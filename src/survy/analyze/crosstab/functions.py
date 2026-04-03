from survy.analyze.crosstab._utils import AggFunc, CrosstabExecutor
from survy.variable.variable import Variable


def crosstab(
    column: Variable,
    row: Variable,
    filter: Variable | None = None,
    aggfunc: AggFunc = "count",
):
    """
    Generate cross-tabulation tables between two survey variables.

    This function computes contingency tables (crosstabs) between a column
    variable and a row variable, optionally segmented by a filter variable.
    It supports count, percentage, and numeric aggregations.

    Parameters
    ----------
    column : Variable
        The variable used for the column dimension of the crosstab.
    row : Variable
        The variable used for the row dimension of the crosstab.
    filter : Variable | None, default None
        Optional variable used to segment the data. If provided, a separate
        crosstab is computed for each value of the filter. If None, a single
        "Total" segment is used.
    aggfunc : {"count", "percent", "mean"} or str, default "count"
        Aggregation function to apply:
        - "count"   : number of unique respondents (based on ID)
        - "percent" : column-wise percentage distribution
        - "mean"    : mean of numeric row variable values
        - other str : any valid pandas aggregation function (e.g. "min", "max", "median")

    Returns
    -------
    dict[str, polars.DataFrame]
        A dictionary mapping each filter value to its corresponding crosstab
        result as a Polars DataFrame.

        - Keys are filter categories (or "Total" if no filter is provided)
        - Values are crosstab tables with:
            * rows representing `row` variable categories
            * columns representing `column` variable categories
            * an additional "Total" margin row/column

    Notes
    -----
    - Internally uses pandas `crosstab` and `pivot_table` for aggregation,
      then converts results back to Polars DataFrames.
    - MULTISELECT variables are automatically exploded before aggregation.
    - Percentages are normalized by column.
    - Numeric aggregations require the `row` variable to be numeric or
      convertible to numeric form.

    Examples
    --------
    >>> crosstab(v1, v2)
    {'Total': <polars.DataFrame ...>}

    >>> crosstab(v1, v2, aggfunc="percent")
    {'Total': <polars.DataFrame ...>}

    >>> crosstab(v1, v3, aggfunc="median")
    {'Total': <polars.DataFrame ...>}

    >>> crosstab(v1, v2, filter=v_filter)
    {'A': <polars.DataFrame ...>, 'B': <polars.DataFrame ...>}
    """
    crosstab_executor = CrosstabExecutor(column, row, filter)
    return crosstab_executor.run(aggfunc)
