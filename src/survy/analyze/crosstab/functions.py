import polars
from survy.analyze.crosstab._utils import AggFunc, CrosstabExecutor
from survy.variable.variable import Variable


def crosstab(
    column: Variable,
    row: Variable,
    filter: Variable | None = None,
    aggfunc: AggFunc = "count",
    alpha: float = 0.05,
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

        >>> crosstab(gender, satisfaction)
        {
            'Total': shape: (3, 3)
            ┌──────────────┬────────────┬────────────┐
            │ satisfaction ┆ Male (A)   ┆ Female (B) │
            │ ---          ┆ ---        ┆ ---        │
            │ str          ┆ str        ┆ str        │
            ╞══════════════╪════════════╪════════════╡
            │ Satisfied    ┆ "42 B"     ┆ "55 A"     │
            │ Neutral      ┆ "30 "      ┆ "28 "      │
            │ Dissatisfied ┆ "18 "      ┆ "12 "      │
            └──────────────┴────────────┴────────────┘
        }

        Percentage crosstab:

        >>> crosstab(gender, satisfaction, aggfunc="percent")
        {
            'Total': shape: (3, 3)
            ┌──────────────┬────────────┬────────────┐
            │ satisfaction ┆ Male (A)   ┆ Female (B) │
            │ ---          ┆ ---        ┆ ---        │
            │ str          ┆ str        ┆ str        │
            ╞══════════════╪════════════╪════════════╡
            │ Satisfied    ┆ "0.467 B"  ┆ "0.579 A"  │
            │ Neutral      ┆ "0.333 "   ┆ "0.295 "   │
            │ Dissatisfied ┆ "0.200 "   ┆ "0.126 "   │
            └──────────────┴────────────┴────────────┘
        }

        Numeric aggregation (mean):

        >>> crosstab(gender, age, aggfunc="mean")
        {
            'Total': shape: (1, 3)
            ┌─────┬──────────┬──────────┐
            │ age ┆ Male     ┆ Female   │
            │ --- ┆ ---      ┆ ---      │
            │ str ┆ str      ┆ str      │
            ╞═════╪══════════╪══════════╡
            │ age ┆ "34.2 B" ┆ "29.8 A" │
            └─────┴──────────┴──────────┘
        }

        With filter (multiple segments):

        >>> crosstab(gender, satisfaction, filter=region)
        {
            'North': shape: (3, 3)
            ┌──────────────┬────────────┬────────────┐
            │ satisfaction ┆ Male (A)   ┆ Female (B) │
            ╞══════════════╪════════════╪════════════╡
            │ Satisfied    ┆ "20 "      ┆ "25 "      │
            │ Neutral      ┆ "15 "      ┆ "12 "      │
            │ Dissatisfied ┆ "10 "      ┆ "8 "       │
            └──────────────┴────────────┴────────────┘,

            'South': shape: (3, 3)
            ┌──────────────┬────────────┬────────────┐
            │ satisfaction ┆ Male (A)   ┆ Female (B) │
            ╞══════════════╪════════════╪════════════╡
            │ Satisfied    ┆ "22 "      ┆ "30 "      │
            │ Neutral      ┆ "15 "      ┆ "16 "      │
            │ Dissatisfied ┆ "8 "       ┆ "4 "       │
            └──────────────┴────────────┴────────────┘
        }
    """
    crosstab_executor = CrosstabExecutor(column, row, filter)
    return crosstab_executor.run(aggfunc, alpha)
