from typing import Iterable
import polars
from survy.analyze.crosstab._utils import AggFunc, CrosstabExecutor
from survy.variable.variable import Variable
from statsmodels.stats.proportion import proportions_ztest


def crosstab(
    column: Variable,
    row: Variable,
    filter: Variable | None = None,
    aggfunc: AggFunc = "count",
) -> dict[str, polars.DataFrame]:
    """Generate cross-tabulation tables between two survey variables.

    Computes contingency tables (crosstabs) between a column variable and a
    row variable, optionally segmented by a filter variable. Supports count,
    percentage, and numeric aggregations.

    Args:
        column: The variable used for the column dimension of the crosstab.
        row: The variable used for the row dimension of the crosstab.
        filter: Optional variable used to segment the data. If provided, a
            separate crosstab is computed for each value of the filter.
            If None, a single "Total" segment is used.
        aggfunc: Aggregation function to apply. Defaults to "count".
            - "count"   : number of unique respondents (based on ID)
            - "percent" : column-wise percentage distribution
            - "mean"    : mean of numeric row variable values
            - other str : any valid pandas aggregation function (e.g. "min", "max", "median")

    Returns:
        A dictionary mapping each filter value to its corresponding crosstab
        result as a Polars DataFrame. Keys are filter categories (or "Total"
        if no filter is provided). Values are crosstab tables with rows
        representing `row` variable categories, columns representing `column`
        variable categories, and an additional "Total" margin row/column.

    Notes:
        - Internally uses pandas `crosstab` and `pivot_table` for aggregation,
          then converts results back to Polars DataFrames.
        - MULTISELECT variables are automatically exploded before aggregation.
        - Percentages are normalized by column.
        - Numeric aggregations require the `row` variable to be numeric or
          convertible to numeric form.

    Examples:
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


def sig_test_proportion(
    crosstab: polars.DataFrame, sig_level: float
) -> polars.DataFrame:
    """
    Perform column-wise proportion significance tests on a count crosstab.

    For each cell in the crosstab, tests whether its proportion differs
    significantly from every other column's proportion in the same row.
    Significant differences are indicated by appending the letter label
    of the compared column (e.g. ``"A"``, ``"AB"``).

    Args:
        crosstab (polars.DataFrame): A count-based contingency table as
            returned by ``crosstab_count``. Expected structure:
            - First column: category labels.
            - Middle columns: count values per group.
            - Last row and last column: ``"Total"`` margins.
        sig_level (float): Significance level threshold for the z-test
            (e.g. ``0.05``).

    Returns:
        polars.DataFrame: A DataFrame where count values are replaced by
            strings indicating which columns differ significantly
            (e.g. ``"AB"`` means this column differs significantly from
            columns A and B). Column headers are suffixed with their letter
            label (e.g. ``"Gender (A)"``). The first column (category
            labels) and Total margins are excluded from testing.

    Examples:
        >>> result = sig_test_proportion(crosstab_result, sig_level=0.05)
        shape: (3, 4)
        ┌──────────┬────────────┬────────────┬────────────┐
        │ category ┆ Col1 (A)   ┆ Col2 (B)   ┆ Col3 (C)   │
        │ ---      ┆ ---        ┆ ---        ┆ ---        │
        │ str      ┆ str        ┆ str        ┆ str        │
        ╞══════════╪════════════╪════════════╪════════════╡
        │ Cat A    ┆ B          ┆            ┆ A          │
        │ Cat B    ┆            ┆ C          ┆ B          │
        │ Cat C    ┆            ┆            ┆            │
        └──────────┴────────────┴────────────┴────────────┘
    """

    def _is_sig_diff(count: Iterable, nobs: Iterable):
        """Return True if two proportions differ significantly."""
        if any(n == 0 for n in nobs) or any(c == 0 for c in count):
            return False
        _, p = proportions_ztest(count, nobs)
        return p < sig_level

    def _col_label(n: int) -> str:
        """Convert a zero-based index to an Excel-style column label (A, B, ..., Z, AA, ...)."""
        label = ""
        while n >= 0:
            label = chr(n % 26 + 65) + label
            n = n // 26 - 1
        return label

    def _build_sig_labels(df: polars.DataFrame) -> polars.DataFrame:
        """Replace each cell with letters of columns that differ significantly."""
        results = []
        for row in df.iter_rows():
            row_result = []
            for i, val in enumerate(row):
                sig_cols = "".join(
                    _col_label(j)
                    for j, other in enumerate(row)
                    if i != j
                    and _is_sig_diff([val, other], [col_totals[i], col_totals[j]])
                )
                row_result.append(sig_cols)
            results.append(row_result)
        return polars.DataFrame(results, schema=df.columns, orient="row")

    cat_col = crosstab[:, 0][:-1]  # category label column, drop Total row
    counts_df = crosstab[:-1, 1:-1]  # inner counts, drop Total row and margins
    col_totals = crosstab.row(-1)[1:-1]  # Total row values, excluding label and margin

    sig_df = _build_sig_labels(counts_df)
    sig_df.columns = [
        f"{col} ({_col_label(i)})" for i, col in enumerate(sig_df.columns)
    ]
    result = polars.concat([cat_col.to_frame(), sig_df], how="horizontal")

    return result
