from typing import Literal
import polars
from survy.survey._utils import VarType
from survy.survey.strategies.base_strategy import BaseStrategy
from survy.utils.spss import value_labels, variable_labels, variable_level


class SelectStrategy(BaseStrategy):
    """
    Strategy for handling single-select (categorical) survey variables.
    """

    def __init__(self, series: polars.Series, value_indices: dict[str, int]) -> None:
        """
        Initialize SelectStrategy.

        Args:
            series (polars.Series): Raw response data.
            value_indices (dict[str, int]): Mapping from category labels
                to numeric codes.
        """
        self.series = series
        self.value_indices = value_indices

    def get_df(self, **kwargs) -> polars.DataFrame:
        """
        Convert the series into a DataFrame representation.

        Args:
            **kwargs:
                dtype (Literal["number", "text"]):
                    - "number": replace categories with numeric codes
                    - "text": keep original labels

        Returns:
            polars.DataFrame: Transformed DataFrame.
        """
        dtype: Literal["number", "text"] = kwargs["dtype"]

        if dtype == "number":
            return self.series.replace_strict(
                self.value_indices, default=None
            ).to_frame()

        return self.series.to_frame()

    @property
    def frequencies(self) -> dict[str, int]:
        """
        Compute frequency counts for each category.

        Null values are excluded from the base.

        Returns:
            dict[str, int]: Mapping of category → count.
        """
        df = self.get_df(dtype="text")
        id = self.series.name

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
        Generate SPSS syntax for a single-select variable.

        This includes:
        - Variable labels
        - Value labels
        - Variable measurement level (nominal)

        Args:
            label (str): Variable label.

        Returns:
            str: Combined SPSS syntax string.

        Notes:
            - Label is sanitized to remove quotes.
            - Label must be shorter than 250 characters.
        """
        id = self.series.name

        assert len(label) < 250
        label = label.replace("'", "").replace('"', "")

        var_label_str = variable_labels(VarType.SELECT, id, label, self.value_indices)
        value_label_str = value_labels(VarType.SELECT, id, self.value_indices)
        var_level_str = variable_level(
            VarType.SELECT, id, "NOMINAL", self.value_indices
        )

        return "\n".join([var_label_str, value_label_str, var_level_str])
