from typing import TypeAlias, Literal, Union
from functools import reduce
import numpy
import polars
import polars.selectors as cs
from polars._typing import PivotAgg
from statsmodels.stats.proportion import proportions_ztest
from statsmodels.stats.weightstats import ttest_ind

from survy.errors import VarTypeError
from survy.variable._utils import VarType
from survy.variable.variable import Variable

CatAggFunc: TypeAlias = Literal["count", "percent"]
"""Supported categorical crosstab modes."""

NumAggFunc: TypeAlias = PivotAgg
"""Supported numeric aggregation functions (e.g. "mean", "median", "sum")."""

AggFunc: TypeAlias = Union[CatAggFunc, NumAggFunc]
"""General aggregation type accepted by crosstab operations."""


def _get_row(row: Variable, column: Variable) -> Variable:
    if row.id == column.id:
        return Variable(series=polars.Series(f"{row.id}#1", row.series.to_list()))
    else:
        return row


def _get_filter(filter: Variable | None, len_: int) -> Variable:
    if filter:
        if filter.vtype == VarType.NUMBER:
            raise VarTypeError(f"NUMBER {filter.id} can not be set as filter")
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


def _col_label(n: int) -> str:
    """Convert a zero-based index to an Excel-style column label (A, B, ..., Z, AA, ...).

    Args:
        n: Zero-based column index.

    Returns:
        Excel-style label string (e.g. 0 → "A", 25 → "Z", 26 → "AA").

    Examples:
        >>> _col_label(0)
        'A'
        >>> _col_label(25)
        'Z'
        >>> _col_label(26)
        'AA'
    """
    label = ""
    while n >= 0:
        label = chr(n % 26 + 65) + label
        n = n // 26 - 1
    return label


def _merge_df_by_element(
    df1: polars.DataFrame, df2: polars.DataFrame
) -> polars.DataFrame:
    """Merge two DataFrames element-wise by concatenating cell values with a space.

    Args:
        df1: Base DataFrame (e.g. counts or percents).
        df2: Overlay DataFrame (e.g. significance labels). Must have identical
            schema to df1.

    Returns:
        A DataFrame where each cell is "{df1_value} {df2_value}" as a string.

    Examples:
        Input df1:
        ┌─────┬─────┐
        │ A   ┆ B   │
        │ --- ┆ --- │
        │ i64 ┆ i64 │
        ╞═════╪═════╡
        │ 42  ┆ 18  │
        │ 10  ┆ 30  │
        └─────┴─────┘

        Input df2:
        ┌─────┬─────┐
        │ A   ┆ B   │
        │ --- ┆ --- │
        │ str ┆ str │
        ╞═════╪═════╡
        │ "B" ┆ ""  │
        │ ""  ┆ "A" │
        └─────┴─────┘

        Output:
        ┌────────┬────────┐
        │ A      ┆ B      │
        │ ---    ┆ ---    │
        │ str    ┆ str    │
        ╞════════╪════════╡
        │ "42 B" ┆ "18 "  │
        │ "10 "  ┆ "30 A" │
        └────────┴────────┘
    """
    return df1.select(
        polars.col(col).cast(polars.String)
        + polars.lit(" ")
        + df2[col].cast(polars.String)
        for col in df1.columns
    )


def _label_columns(df: polars.DataFrame) -> polars.DataFrame:
    """Suffix each column with its Excel-style letter label in parentheses.

    Args:
        df: DataFrame whose columns will be relabelled.

    Returns:
        A DataFrame with renamed columns in the format "{col} ({letter})"
        (e.g. "Gender (A)", "Age Group (B)").

    Examples:
        Input columns:  ["Male", "Female", "Other"]
        Output columns: ["Male (A)", "Female (B)", "Other (C)"]
    """
    df.columns = [f"{col} ({_col_label(i)})" for i, col in enumerate(df.columns)]
    return df


class CrosstabExecutor:
    """Internal executor for computing cross-tabulations between survey variables.

    Orchestrates the preparation, joining, and aggregation of Variable objects
    into crosstab tables. Supports categorical counts, percentage distributions,
    and numeric aggregations, optionally segmented by a filter variable.

    Args:
        column: Variable used as the column dimension in the crosstab.
        row: Variable used as the row dimension in the crosstab.
        filter: Optional variable used to segment the data. If None, a
            synthetic "Total" filter is applied.

    Notes:
        - All variables must have the same length (number of respondents).
        - MULTISELECT variables are automatically exploded into long format.
        - Significance tests use a two-proportion z-test for count/percent
          and Welch's t-test for numeric aggregations.
    """

    def __init__(
        self, column: Variable, row: Variable, filter: Variable | None
    ) -> None:
        assert column.len == row.len
        self.column = column
        self.row = _get_row(row, column)
        self.filter = _get_filter(filter, column.len)

    def get_df(self, row_as_num: bool) -> polars.DataFrame:
        """Construct a merged DataFrame for crosstab computation.

        Prepares and joins the column, row, and filter variables into a single
        Polars DataFrame using a common respondent ID.

        Args:
            row_as_num: Whether to convert the row variable to numeric
                representation. Required for numeric aggregations.

        Returns:
            A DataFrame containing an "ID" column (row index), the column
            variable, the row variable, and the filter variable.

        Notes:
            - MULTISELECT variables are exploded before joining.
            - Joins are performed as left joins on "ID".
        """
        column_df = _get_var_df(self.column, as_num=False)
        row_df = _get_var_df(self.row, as_num=row_as_num)
        filter_df = _get_var_df(self.filter, as_num=False)

        return (
            reduce(
                lambda left, right: left.join(right, on="ID", how="inner"),
                [column_df, row_df, filter_df],
            )
            .filter(
                polars.col(self.column.id).is_not_null(),
                polars.col(self.row.id).is_not_null(),
            )
            .cast({self.column.id: polars.String})
        )

    def _pivot_counts(self, filter_by: str) -> polars.DataFrame:
        """Pivot raw response data into a count-based crosstab for a given filter.

        Args:
            filter_by: Filter value used to subset the data.

        Returns:
            A DataFrame with row variable categories as rows, column variable
            categories as columns, and unique respondent counts as values,
            sorted by row variable.

        Examples:
            Output (column=gender, row=satisfaction):
            ┌──────────────┬────────┬────────┐
            │ satisfaction ┆ Male   ┆ Female │
            │ ---          ┆ ---    ┆ ---    │
            │ str          ┆ i64    ┆ i64    │
            ╞══════════════╪════════╪════════╡
            │ Satisfied    ┆ 42     ┆ 55     │
            │ Neutral      ┆ 30     ┆ 28     │
            │ Dissatisfied ┆ 18     ┆ 12     │
            └──────────────┴────────┴────────┘
        """
        df = self.get_df(row_as_num=False).filter(
            polars.col(self.filter.id) == filter_by
        )
        pivot = (
            df.pivot(
                on=self.column.id,
                index=self.row.id,
                values="ID",
                aggregate_function=polars.element().n_unique(),
            )
            .filter(polars.col(self.row.id).is_not_null())
            .sort(self.row.id)
            .cast({self.row.id: polars.String})
        )

        return pivot

    def _get_col_total(self, col_name: str) -> int:
        """Look up the total respondent count for a column variable category.

        Args:
            col_name: Category label matching a value in the column variable.

        Returns:
            Total count for that category, or 0 if not found.

        Examples:
            >>> self._get_col_total("Male")
            90
            >>> self._get_col_total("Unknown")
            0
        """
        result = self.column.frequencies.filter(
            polars.col(self.column.id) == str(col_name)
        )["count"]
        return result[0] if len(result) > 0 else 0

    def _sig_test_proportion(
        self, counts: polars.DataFrame, alpha: float
    ) -> polars.DataFrame:
        """Test pairwise proportion differences for each cell in a count crosstab.

        For each cell, compares its column proportion against every other column
        using a two-proportion z-test. Cells are labelled with the letters of
        columns they differ from significantly.

        Args:
            counts: Numeric-only crosstab DataFrame (no label column). Rows
                represent row variable categories; columns represent column
                variable categories.
            alpha: Significance level threshold (e.g. 0.05).

        Returns:
            A DataFrame with the same schema as `counts`, where each cell
            contains a string of column letters indicating significant
            differences, or an empty string if none.

        Examples:
            Input counts (column=gender, row=satisfaction):
            ┌────────┬────────┐
            │ Male   ┆ Female │
            │ ---    ┆ ---    │
            │ i64    ┆ i64    │
            ╞════════╪════════╡
            │ 42     ┆ 55     │
            │ 30     ┆ 28     │
            │ 18     ┆ 12     │
            └────────┴────────┘

            Output (Male proportion of Satisfied differs significantly from Female):
            ┌────────┬────────┐
            │ Male   ┆ Female │
            │ ---    ┆ ---    │
            │ str    ┆ str    │
            ╞════════╪════════╡
            │ "B"    ┆ "A"    │
            │ ""     ┆ ""     │
            │ ""     ┆ ""     │
            └────────┴────────┘
        """

        def _is_sig_diff(count, nobs) -> bool:
            if any(n == 0 for n in nobs):
                return False

            props = [c / n for c, n in zip(count, nobs)]

            if any(p == 0 or p == 1 for p in props):
                return False

            _, p = proportions_ztest(count, nobs)
            return float(p) < alpha

        col_names = counts.columns
        results = []
        for row in counts.iter_rows():
            row_result = [
                "".join(
                    _col_label(j)
                    for j, other in enumerate(row)
                    if i != j
                    and _is_sig_diff(
                        [val, other],
                        [
                            self._get_col_total(col_names[i]),
                            self._get_col_total(col_names[j]),
                        ],
                    )
                )
                for i, val in enumerate(row)
            ]
            results.append(row_result)

        return polars.DataFrame(results, schema=counts.columns, orient="row")

    def _sig_test_mean(self, filter_by: str, alpha: float) -> polars.DataFrame:
        """Test pairwise mean differences across column variable categories.

        For each pair of column categories, applies Welch's t-test on the raw
        row variable values. Each category is labelled with the letters of
        categories it differs from significantly.

        Args:
            filter_by: Filter value used to subset the data.
            alpha: Significance level threshold (e.g. 0.05).

        Returns:
            A two-column DataFrame mapping each column category to its
            significance label string.

            ┌────────┬─────┐
            │ gender ┆ sig │
            │ ---    ┆ --- │
            │ str    ┆ str │
            ╞════════╪═════╡
            │ Male   ┆ "B" │
            │ Female ┆ "A" │
            └────────┴─────┘

        Notes:
            - Categories with fewer than 2 non-null values are skipped.
            - Uses Welch's t-test (unequal variance assumption).
        """

        def _get_group_data(item) -> list:
            return (
                df.filter(polars.col(self.column.id) == item)[self.row.id]
                .drop_nulls()
                .to_list()
            )

        def _is_valid_sample(arr):
            return len(arr) >= 2 and numpy.var(arr) > 0

        def _is_sig_diff(group_a, group_b) -> bool:
            if not (_is_valid_sample(group_a) and _is_valid_sample(group_b)):
                return False

            _, p, _ = ttest_ind(group_a, group_b)
            return float(p) < alpha

        df = self.get_df(row_as_num=True).filter(
            polars.col(self.filter.id) == filter_by
        )
        col_names = df[self.column.id].unique().sort().to_list()
        col_names = [col for col in col_names if col is not None]

        sig_labels = [
            "".join(
                _col_label(j)
                for j, other in enumerate(col_names)
                if i != j and _is_sig_diff(_get_group_data(val), _get_group_data(other))
            )
            for i, val in enumerate(col_names)
        ]

        return polars.DataFrame(
            {self.column.id: col_names, "sig": sig_labels},
        )

    def crosstab_count(self, filter_by: str, alpha: float) -> polars.DataFrame:
        """Compute a count-based crosstab with inline significance labels.

        Counts unique respondents for each row/column category combination,
        then appends significance labels indicating which columns differ
        significantly in proportion (two-proportion z-test).

        Args:
            filter_by: Filter value used to subset the data.
            alpha: Significance level for the proportion z-test (e.g. 0.05).

        Returns:
            A DataFrame where each cell contains "{count} {sig_labels}".
            The first column contains row category labels. Column headers are
            suffixed with their letter label.

        Examples:
            Output (column=gender, row=satisfaction, alpha=0.05):
            ┌──────────────┬────────────┬────────────┐
            │ satisfaction ┆ Male (A)   ┆ Female (B) │
            │ ---          ┆ ---        ┆ ---        │
            │ str          ┆ str        ┆ str        │
            ╞══════════════╪════════════╪════════════╡
            │ Satisfied    ┆ "42 B"     ┆ "55 A"     │
            │ Neutral      ┆ "30 "      ┆ "28 "      │
            │ Dissatisfied ┆ "18 "      ┆ "12 "      │
            └──────────────┴────────────┴────────────┘
        """
        counts = self._pivot_counts(filter_by)
        numeric_counts = counts.select(cs.numeric())

        sig_df = self._sig_test_proportion(numeric_counts, alpha)
        merged = _label_columns(_merge_df_by_element(numeric_counts, sig_df))

        return polars.concat([counts.select(self.row.id), merged], how="horizontal")

    def crosstab_percent(self, filter_by: str, alpha: float) -> polars.DataFrame:
        """Compute a percentage-based crosstab with inline significance labels.

        Calculates column-wise proportions for each row/column combination,
        then appends significance labels based on proportion z-tests.

        Args:
            filter_by: Filter value used to subset the data.
            alpha: Significance level for the proportion z-test (e.g. 0.05).

        Returns:
            A DataFrame where each cell contains "{proportion} {sig_labels}".
            The first column contains row category labels. Column headers are
            suffixed with their letter label.

        Examples:
            Output (column=gender, row=satisfaction, alpha=0.05):
            ┌──────────────┬────────────┬────────────┐
            │ satisfaction ┆ Male (A)   ┆ Female (B) │
            │ ---          ┆ ---        ┆ ---        │
            │ str          ┆ str        ┆ str        │
            ╞══════════════╪════════════╪════════════╡
            │ Satisfied    ┆ "0.467 B"  ┆ "0.579 A"  │
            │ Neutral      ┆ "0.333 "   ┆ "0.295 "   │
            │ Dissatisfied ┆ "0.2 "     ┆ "0.126 "   │
            └──────────────┴────────────┴────────────┘

        Notes:
            Proportions are count / total respondents per column category.
            If a column total is 0, its proportion is set to 0.
        """
        counts = self._pivot_counts(filter_by)
        numeric_counts = counts.select(cs.numeric())

        percents = numeric_counts.select(
            (polars.col(col) / self._get_col_total(col)).fill_nan(0.0)
            for col in numeric_counts.columns
        )

        sig_df = self._sig_test_proportion(numeric_counts, alpha)
        merged = _label_columns(_merge_df_by_element(percents, sig_df))

        return polars.concat([counts.select(self.row.id), merged], how="horizontal")

    def crosstab_number(
        self, filter_by: str, aggfunc: PivotAgg, alpha: float
    ) -> polars.DataFrame:
        """Compute a numeric aggregation crosstab with inline significance labels.

        Aggregates the row variable by column variable categories using the
        specified function, then appends significance labels based on pairwise
        Welch's t-tests on the raw values.

        Args:
            filter_by: Filter value used to subset the data.
            aggfunc: Aggregation function to apply to the row variable
                (e.g. "mean", "median", "sum", "min", "max").
            alpha: Significance level for the t-test (e.g. 0.05).

        Returns:
            A single-row DataFrame where each cell contains
            "{aggregated_value} {sig_labels}". The first column is the row
            variable name; columns are column variable categories.

        Examples:
            Output (column=gender, row=age, aggfunc="mean", alpha=0.05):
            ┌─────┬────────────┬────────────┐
            │ age ┆ Male (A)   ┆ Female (B) │
            │ --- ┆ ---        ┆ ---        │
            │ str ┆ str        ┆ str        │
            ╞═════╪════════════╪════════════╡
            │ age ┆ "34.2 B"   ┆ "29.8 A"   │
            └─────┴────────────┴────────────┘

        Notes:
            - The row variable must be numeric or convertible to numeric.
            - Significance test uses raw (non-aggregated) values per group.
        """
        df = self.get_df(row_as_num=True).filter(
            polars.col(self.filter.id) == filter_by
        )

        agg_df = (
            df.group_by(self.column.id)
            .agg(getattr(polars.col(self.row.id), aggfunc)())
            .sort(self.column.id)
        )

        sig_df = self._sig_test_mean(filter_by, alpha)

        transposed = (
            agg_df.join(sig_df, on=self.column.id)
            .with_columns(
                (
                    polars.col(self.row.id).cast(polars.String)
                    + polars.lit(" ")
                    + polars.col("sig")
                ).alias(self.row.id)
            )
            .drop("sig")
            .transpose(
                include_header=True,
                header_name=self.row.id,
                column_names=self.column.id,
            )
        )

        label_col = transposed.select(self.row.id)
        value_cols = _label_columns(transposed.select(cs.exclude(self.row.id)))
        return polars.concat([label_col, value_cols], how="horizontal")

    def run(self, aggfunc: AggFunc, alpha: float) -> dict[str, polars.DataFrame]:
        """Execute crosstab computation for all filter segments.

        Dispatches to the appropriate crosstab method based on the aggregation
        function and computes results for each filter value.

        Args:
            aggfunc: Aggregation mode. Use "count" for frequency counts,
                "percent" for column-wise percentages, or a numeric string
                (e.g. "mean", "median") for numeric aggregation. Proportion
                z-tests are applied for "count"/"percent"; Welch's t-tests
                for numeric modes.
            alpha: Significance level applied across all tests (e.g. 0.05).

        Returns:
            A dictionary mapping filter values to crosstab DataFrames. If no
            filter is provided, returns a single key "Total".

        Examples:
            >>> executor.run("count", alpha=0.05)
            {'Total': <polars.DataFrame>}

            >>> executor.run("mean", alpha=0.05)
            {'Male': <polars.DataFrame>, 'Female': <polars.DataFrame>}
        """
        results = {}
        for value in self.filter.value_indices.keys():
            if aggfunc == "count":
                results[value] = self.crosstab_count(value, alpha)
            elif aggfunc == "percent":
                results[value] = self.crosstab_percent(value, alpha)
            else:
                results[value] = self.crosstab_number(value, aggfunc, alpha)

        return results
