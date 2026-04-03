from typing import Callable, TypeAlias, Literal, Union
from functools import reduce
import pandas
import polars
import polars.selectors as cs

from survy.survey._utils import VarType
from survy.survey.variable import Variable

CatAggFunc: TypeAlias = Literal["count", "percent"]
"""
Supported categorical crosstab modes.
"""

NumAggFunc: TypeAlias = Literal["mean", "min", "max", "median", "sum", "var", "std"]
"""
Supported numeric aggregation functions.
"""

AggFunc: TypeAlias = Union[CatAggFunc, NumAggFunc, Callable]
"""
General aggregation type accepted by crosstab operations.
"""


def _get_filter(filter: Variable | None, len_: int):
    if filter:
        series = polars.Series("FILTER", filter.series.to_list())
    else:
        series = polars.Series("FILTER", ["Total" for _ in range(len_)])

    return Variable(series)


def _get_var_df(variable: Variable, as_num: bool) -> polars.DataFrame:
    match variable.vtype:
        case VarType.MULTISELECT:
            df = variable.get_df("compact").with_row_index("ID").explode(variable.id)
            if as_num:
                df = df.with_columns(
                    polars.col(variable.id)
                    .replace_strict(variable.value_indices, default=None)
                    .alias(variable.id)
                )
        case VarType.SELECT:
            df = variable.get_df("number" if as_num else "text").with_row_index("ID")
        case _:
            df = variable.get_df("number").with_row_index("ID")

    return df


class CrosstabExecutor:
    """
    Internal executor for computing cross-tabulations between survey variables.

    This class orchestrates the preparation, joining, and aggregation of
    `Variable` objects into crosstab tables. It supports categorical counts,
    percentage distributions, and numeric aggregations, optionally segmented
    by a filter variable.

    Parameters
    ----------
    column : Variable
        Variable used as the column dimension in the crosstab.
    row : Variable
        Variable used as the row dimension in the crosstab.
    filter : Variable | None
        Optional variable used to segment the data. If None, a synthetic
        "Total" filter is applied.

    Notes
    -----
    - All variables must have the same length (number of respondents).
    - MULTISELECT variables are automatically exploded into long format.
    - Aggregations are performed using pandas and converted back to Polars.
    """

    def __init__(
        self, column: Variable, row: Variable, filter: Variable | None
    ) -> None:
        assert column.len == row.len

        self.column = column
        self.row = row
        self.filter = _get_filter(filter, column.len)

    def get_df(self, row_as_num: bool):
        """
        Construct a merged DataFrame for crosstab computation.

        This method prepares and joins the column, row, and filter variables
        into a single Polars DataFrame using a common respondent ID.

        Parameters
        ----------
        row_as_num : bool
            Whether to convert the row variable to numeric representation.
            Required for numeric aggregations.

        Returns
        -------
        polars.DataFrame
            A DataFrame containing:
            - "ID" column (row index)
            - column variable
            - row variable
            - filter variable

        Notes
        -----
        - MULTISELECT variables are exploded before joining.
        - Joins are performed as left joins on "ID".
        """
        column_df = _get_var_df(self.column, as_num=False)
        row_df = _get_var_df(self.row, as_num=row_as_num)
        filter_df = _get_var_df(self.filter, as_num=False)

        merged_df = reduce(
            lambda left, right: left.join(right, on="ID", how="left"),
            [column_df, row_df, filter_df],
        )

        return merged_df

    def crosstab_count(self, filter_by: str) -> polars.DataFrame:
        """
        Compute a count-based crosstab for a given filter value.

        Counts the number of unique respondents (based on "ID") for each
        combination of row and column categories.

        Parameters
        ----------
        filter_by : str
            Filter value used to subset the data.

        Returns
        -------
        polars.DataFrame
            Crosstab table with:
            - rows representing row variable categories
            - columns representing column variable categories
            - integer counts
            - "Total" margins for rows and columns
        """
        df = self.get_df(row_as_num=False).filter(
            polars.col(self.filter.id) == filter_by
        )
        crosstab = (
            pandas.crosstab(
                index=df[self.row.id],
                columns=df[self.column.id],
                values=df["ID"],
                aggfunc=pandas.Series.nunique,
                margins=True,
                margins_name="Total",
            )
            .reset_index()
            .fillna(0)
            .rename(columns={"row_0": self.row.id + "/" + self.column.id})
        )

        return polars.DataFrame(crosstab.to_dict("records")).cast(
            {cs.numeric(): polars.Int64}
        )

    def crosstab_percent(self, filter_by: str) -> polars.DataFrame:
        """
        Compute a column-normalized percentage crosstab.

        Calculates the proportion of respondents in each row category
        within each column category.

        Parameters
        ----------
        filter_by : str
            Filter value used to subset the data.

        Returns
        -------
        polars.DataFrame
            Crosstab table with:
            - rows representing row variable categories
            - columns representing column variable categories
            - float percentages normalized by column
            - "Total" margins

        Notes
        -----
        - Percentages are normalized column-wise (each column sums to 1).
        """
        df = self.get_df(row_as_num=False).filter(
            polars.col(self.filter.id) == filter_by
        )
        crosstab = (
            pandas.crosstab(
                index=df[self.row.id],
                columns=df[self.column.id],
                values=df["ID"],
                aggfunc=pandas.Series.nunique,
                margins=True,
                margins_name="Total",
                normalize="columns",
            )
            .reset_index()
            .fillna(0)
            .rename(columns={"row_0": self.row.id + "/" + self.column.id})
        )

        return polars.DataFrame(crosstab.to_dict("records")).cast(
            {cs.numeric(): polars.Float16}
        )

    def crosstab_number(self, filter_by: str, aggfunc: AggFunc) -> polars.DataFrame:
        """
        Compute a numeric aggregation crosstab.

        Applies a numeric aggregation function to the row variable grouped
        by the column variable.

        Parameters
        ----------
        filter_by : str
            Filter value used to subset the data.
        aggfunc : AggFunc
            Aggregation function to apply. Can be:
            - A predefined numeric aggregation string (e.g. "mean", "min", "max",
            "median", "sum", "var", "std")
            - A callable compatible with pandas `pivot_table`

        Returns
        -------
        polars.DataFrame
            Aggregated crosstab table with:
            - rows representing aggregation results
            - columns representing column variable categories
            - "Total" margin

        Notes
        -----
        - The row variable is converted to numeric before aggregation.
        - Internally uses pandas `pivot_table`.
        """
        df = self.get_df(row_as_num=True).filter(
            polars.col(self.filter.id) == filter_by
        )
        crosstab = pandas.pivot_table(
            pandas.DataFrame(df.to_dict(as_series=False)),
            values="ID",
            index=self.column.id,
            aggfunc=aggfunc,
            fill_value=0,
            margins=True,
            margins_name="Total",
        ).transpose()

        return polars.DataFrame(crosstab.to_dict("records"))

    def run(self, aggfunc: AggFunc) -> dict[str, polars.DataFrame]:
        """
        Execute crosstab computation for all filter segments.

        Dispatches to the appropriate crosstab method based on the
        aggregation function and computes results for each filter value.

        Parameters
        ----------
        aggfunc : AggFunc
            Aggregation mode or function:
            - "count"   : frequency counts
            - "percent" : column-wise percentages
            - numeric aggregation (e.g. "mean", "median", etc.)
            - callable  : custom aggregation function

        Returns
        -------
        dict[str, polars.DataFrame]
            Mapping of filter values to crosstab DataFrames.

        Notes
        -----
        - Each filter value produces a separate crosstab.
        - If no filter is provided, a single "Total" key is returned.
        """
        results = {}
        for value in self.filter.value_indices.keys():
            if aggfunc == "count":
                results[value] = self.crosstab_count(value)
            elif aggfunc == "percent":
                results[value] = self.crosstab_percent(value)
            else:
                results[value] = self.crosstab_number(value, aggfunc)

        return results
