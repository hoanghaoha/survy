import polars
from survy.variable._utils import VarType
from survy.variable.strategies.base_strategy import BaseStrategy
from survy.utils.spss import variable_labels, variable_level


class NumberStrategy(BaseStrategy):
    """
    Strategy for handling numeric (continuous or discrete) survey variables.
    """

    def __init__(self, series: polars.Series, value_indices: dict[str, int]) -> None:
        """
        Initialize NumberStrategy.

        Args:
            series (polars.Series): Series containing numeric responses.
            value_indices (dict[str, int]): Not used for numeric variables,
                but kept for interface consistency.
        """
        self.series = series
        self.value_indices = value_indices

    def get_df(self, **kwargs) -> polars.DataFrame:
        """
        Convert the series into a DataFrame representation.

        For numeric variables, no transformation is applied.

        Args:
            **kwargs: Ignored (kept for interface compatibility).

        Returns:
            polars.DataFrame: DataFrame containing the original numeric data.
        """
        df = self.series.to_frame()
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
        id = self.series.name
        base = len(self.series)
        df = (
            self.get_df(dtype="number")
            .filter(polars.col(id).is_not_null())[id]
            .value_counts(name="count")
            .sort(id)
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
        id = self.series.name

        var_label_str = variable_labels(VarType.NUMBER, id, label, self.value_indices)

        var_level_str = variable_level(VarType.NUMBER, id, "SCALE")

        return "\n".join([var_label_str, var_level_str])
