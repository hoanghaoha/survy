import polars
from survy.survey._utils import QuestionType
from survy.survey.strategies.base_strategy import BaseStrategy
from survy.utils.spss import variable_labels, variable_level


class NumberStrategy(BaseStrategy):
    """
    Strategy for handling numeric (continuous or discrete) survey questions.
    """

    def __init__(self, series: polars.Series, option_indices: dict[str, int]) -> None:
        """
        Initialize NumberStrategy.

        Args:
            series (polars.Series): Series containing numeric responses.
            option_indices (dict[str, int]): Not used for numeric questions,
                but kept for interface consistency.
        """
        self.series = series
        self.option_indices = option_indices

    def get_df(self, **kwargs) -> polars.DataFrame:
        """
        Convert the series into a DataFrame representation.

        For numeric questions, no transformation is applied.

        Args:
            **kwargs: Ignored (kept for interface compatibility).

        Returns:
            polars.DataFrame: DataFrame containing the original numeric data.
        """
        df = self.series.to_frame()
        return df

    @property
    def sub_bases(self) -> dict[str, int]:
        """
        Compute frequency counts for each numeric value.

        Null values are excluded from the base.

        Returns:
            dict[str, int]: Mapping of value → count.
        """
        id = self.series.name
        df = self.get_df()

        result = (
            df.filter(polars.col(id).is_not_null())
            .group_by(id)
            .agg(polars.col(id).count().alias("base"))
            .rename({id: "option"})
            .sort("option")
            .to_dicts()
        )

        return {item["option"]: item["base"] for item in result}

    def get_sps(self, label: str) -> str:
        """
        Generate SPSS syntax for a numeric question.

        This includes:
        - Variable label
        - Measurement level (SCALE)

        Args:
            label (str): Question label.

        Returns:
            str: Combined SPSS syntax string.

        Notes:
            - Label is sanitized to remove quotes.
            - Label must be shorter than 250 characters.
        """
        id = self.series.name

        assert len(label) < 250
        label = label.replace("'", "").replace('"', "")

        var_label_str = variable_labels(
            QuestionType.NUMBER, id, label, self.option_indices
        )

        var_level_str = variable_level(QuestionType.NUMBER, id, "SCALE")

        return "\n".join([var_label_str, var_level_str])
