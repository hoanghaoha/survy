import polars
from survy.variable._utils import VarType
from survy.variable.strategies.base_strategy import _BaseStrategy
from survy.utils.spss import variable_labels, variable_level


class _NumberStrategy(_BaseStrategy):
    """
    Strategy for handling numeric (continuous or discrete) survey variables.
    """

    def __init__(self, series: polars.Series, value_indices: dict[str, int]) -> None:
        """
        Initialize _NumberStrategy.

        Args:
            series (polars.Series): Series containing numeric responses.
            value_indices (dict[str, int]): Not used for numeric variables,
                but kept for interface consistency.
        """
        self._series = series
        self._value_indices = value_indices

    def get_df(self, **kwargs) -> polars.DataFrame:
        """
        Convert the series into a DataFrame representation.

        For numeric variables, no transformation is applied.

        Args:
            **kwargs: Ignored (kept for interface compatibility).

        Returns:
            polars.DataFrame: DataFrame containing the original numeric data.
        """
        df = self._series.to_frame()
        return df

    @property
    def frequencies(self) -> polars.DataFrame:
        """Frequency counts and proportions for each numeric value.

        Returns:
            A DataFrame with columns:
                - value name: the numeric value
                - "count": number of respondents with that value
                - "proportion": count divided by total number of respondents

        Notes:
            Null values are excluded from counts but included in the base,
            so proportions may not sum to 1.
        """
        col_name = self._series.name
        base = len(self._series)
        df = (
            self.get_df(dtype="number")
            .filter(polars.col(col_name).is_not_null())[col_name]
            .value_counts(name="count")
            .cast({col_name: polars.String})
            .sort(col_name)
            .with_columns((polars.col("count") / base).alias("proportion"))
        )

        return df

    def get_sps(self, label: str) -> str:
        """
        Generate SPSS syntax for a numeric variable.

        This includes:
        - Variable label
        - Measurement level (SCALE)

        Args:
            label (str): Variable label.

        Returns:
            str: Combined SPSS syntax string.

        """
        col_name = self._series.name

        var_label_str = variable_labels(VarType.NUMBER, col_name, label, self._value_indices)

        var_level_str = variable_level(VarType.NUMBER, col_name, "SCALE")

        return "\n".join([var_label_str, var_level_str])
