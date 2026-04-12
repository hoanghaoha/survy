import polars
from survy.analyze.crosstab._utils import AggFunc, CrosstabExecutor
from survy.variable.variable import Variable


def crosstab(
    column: Variable,
    row: Variable,
    filter: Variable | None = None,
    aggfunc: AggFunc = "count",
    alpha: float = 0.05,
    ndigits: int | None = 2,
) -> dict[str, polars.DataFrame]:
    """Compute a cross-tabulation table between two survey variables.

    This function generates crosstab tables by aggregating a *row* variable
    across categories of a *column* variable, optionally segmented by a
    *filter* variable. It supports categorical counts, percentage
    distributions, and numeric aggregations, with optional statistical
    significance testing.

    Args:
        column: Variable used as the column dimension (grouping variable).
        row: Variable used as the row dimension (analyzed variable).
        filter: Optional variable used to segment the data into multiple
            crosstabs. If None, a single "Total" table is returned.
        aggfunc: Aggregation mode:
            - "count": Count of respondents per cell.
            - "percent": Column-wise proportions.
            - Numeric aggregation (e.g. "mean", "median", "sum"): applied to
              the row variable.
        alpha: Significance level for statistical tests (default 0.05).
        ndigits: Number of decimal places to round output values to.
            Applied to proportions ("percent") and aggregated numeric values.
            Ignored for "count". If None (default), no rounding is applied.

    Returns:
        A dictionary mapping each filter value to a Polars DataFrame
        representing the crosstab.

        - For "count" and "percent":
            Rows = row variable categories
            Columns = column variable categories
            Cells = "{value} {sig_labels}"

        - For numeric aggregation:
            Single-row table with aggregated values per column category.

    Notes:
        - All variables must have the same length (number of respondents).
        - MULTISELECT variables are automatically expanded into long format.
        - Statistical tests:
            - "count"/"percent": two-proportion z-test
            - numeric aggregation: Welch's t-test
        - Significant differences are indicated using column letter labels
          (e.g. "A", "B", "AB").

    Examples:
        Basic count crosstab:

        >>> df = polars.DataFrame(
            {
                "gender": ["Male", "Female", "Male"],
                "yob": [2000, 1999, 1998],
                "hobby": ["Sport;Book", "Sport;Movie", "Movie"],
                "animal_1": ["Cat", "", "Cat"],
                "animal_2": ["Dog", "Dog", ""],
            }
        )

        >>> survey = read_polars(df, auto_detect=True)
        >>> crosstab(survey["gender"], survey["hobby"], aggfunc="count")
        {'Total': shape: (3, 3)
        ┌───────┬──────────┬────────────┐
        │ hobby ┆ Male (A) ┆ Female (B) │
        │ ---   ┆ ---      ┆ ---        │
        │ str   ┆ str      ┆ str        │
        ╞═══════╪══════════╪════════════╡
        │ Book  ┆ 1        ┆ 0          │
        │ Movie ┆ 1        ┆ 1          │
        │ Sport ┆ 1        ┆ 1          │
        └───────┴──────────┴────────────┘}

        Percentage crosstab:

        >>> crosstab(survey["gender"], survey["hobby"], aggfunc="percent")
        {'Total': shape: (3, 3)
        ┌───────┬──────────┬────────────┐
        │ hobby ┆ Male (A) ┆ Female (B) │
        │ ---   ┆ ---      ┆ ---        │
        │ str   ┆ str      ┆ str        │
        ╞═══════╪══════════╪════════════╡
        │ Book  ┆ 0.5      ┆ 0.0        │
        │ Movie ┆ 0.5      ┆ 1.0        │
        │ Sport ┆ 0.5      ┆ 1.0        │
        └───────┴──────────┴────────────┘}

        Numeric aggregation (mean):

        >>> crosstab(survey["gender"], survey["hobby"], aggfunc="mean")
        {'Total': shape: (1, 3)
        ┌───────┬────────┬──────┐
        │ hobby ┆ Female ┆ Male │
        │ ---   ┆ ---    ┆ ---  │
        │ str   ┆ str    ┆ str  │
        ╞═══════╪════════╪══════╡
        │ hobby ┆ 2.5    ┆ 2.0  │
        └───────┴────────┴──────┘}

        With filter (multiple segments):

        >>> crosstab(survey["gender"], survey["yob"], survey["hobby"], aggfunc="mean")
        {'Book': shape: (1, 2)
        ┌─────┬─────────┐
        │ yob ┆ Male    │
        │ --- ┆ ---     │
        │ str ┆ str     │
        ╞═════╪═════════╡
        │ yob ┆ 2000.0  │
        └─────┴─────────┘, 'Movie': shape: (1, 3)
        ┌─────┬─────────┬─────────┐
        │ yob ┆ Female  ┆ Male    │
        │ --- ┆ ---     ┆ ---     │
        │ str ┆ str     ┆ str     │
        ╞═════╪═════════╪═════════╡
        │ yob ┆ 1999.0  ┆ 1998.0  │
        └─────┴─────────┴─────────┘, 'Sport': shape: (1, 3)
        ┌─────┬─────────┬─────────┐
        │ yob ┆ Female  ┆ Male    │
        │ --- ┆ ---     ┆ ---     │
        │ str ┆ str     ┆ str     │
        ╞═════╪═════════╪═════════╡
        │ yob ┆ 1999.0  ┆ 2000.0  │
        └─────┴─────────┴─────────┘}
    """
    crosstab_executor = CrosstabExecutor(column, row, filter)
    return crosstab_executor.run(aggfunc, alpha, ndigits)
