from typing import Literal
import warnings
import polars
from survy.separator import MULTISELECT
from survy.survey._utils import QuestionType
from survy.survey.strategies.base_strategy import BaseStrategy
from survy.utils.spss import mrset, value_labels, variable_labels, variable_level


class MultiSelectStrategy(BaseStrategy):
    """
    Strategy for handling multi-select survey questions.

    Multi-select questions contain multiple responses per entry,
    typically stored as a list of selected options.
    """

    def __init__(self, series: polars.Series, option_indices: dict[str, int]) -> None:
        """
        Initialize MultiSelectStrategy.

        Args:
            series (polars.Series): Series containing list-like responses.
            option_indices (dict[str, int]): Mapping of option labels to indices.
        """
        self.series = series
        self.option_indices = option_indices

    def get_df(self, **kwargs) -> polars.DataFrame:
        """
        Convert the series into a DataFrame representation.

        Supports two modes:
        - Compact (default): returns original list column
        - Expanded: creates one column per option

        Args:
            **kwargs:
                dtype (Literal["number", "text"]):
                    - "number": binary indicators (0/1)
                    - "text": option labels or None
                compact (bool):
                    - True: return original list column
                    - False: expand into multiple columns

        Returns:
            polars.DataFrame: Transformed DataFrame.

        Notes:
            - Expanded columns are named as: {id}{MULTISELECT}{index}
            - Uses `list.contains` to detect option presence
        """
        dtype: Literal["number", "text"] = kwargs.get("dtype", "text")
        compact: bool = kwargs.get("compact", True)
        id = self.series.name
        df = self.series.to_frame()

        if compact:
            return df

        if dtype == "number":
            number_df = df.with_columns(
                [
                    polars.col(id)
                    .list.contains(val)
                    .cast(polars.Int8)
                    .alias(f"{id}{MULTISELECT}{index}")
                    for val, index in self.option_indices.items()
                ]
            )
            return number_df.drop(id)
        else:
            text_df = df.with_columns(
                [
                    polars.col(id)
                    .list.contains(val)
                    .cast(polars.Int8)
                    .replace_strict({1: val}, default=None)
                    .alias(f"{id}{MULTISELECT}{index}")
                    for val, index in self.option_indices.items()
                ]
            )
            return text_df.drop(id)

    @property
    def sub_bases(self) -> dict[str, int]:
        """
        Compute frequency counts for each selected option.

        This is done by:
        - Exploding list responses into long format
        - Counting occurrences per option
        - Ignoring null values

        Returns:
            dict[str, int]: Mapping of option → count.
        """
        id = self.series.name
        df = self.get_df(dtype="text", compact=True).explode(id)

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
        Generate SPSS syntax for a multi-select question.

        This includes:
        - Variable labels
        - Value labels
        - Variable level (nominal)
        - MRSETS definition (if applicable)

        Args:
            label (str): Question label.

        Returns:
            str: Combined SPSS syntax string.

        Notes:
            - Label is sanitized to remove quotes.
            - Label must be shorter than 250 characters.
            - MRSETS is skipped if only one option exists.
        """
        id = self.series.name

        assert len(label) < 250
        label = label.replace("'", "").replace('"', "")

        var_label_str = variable_labels(
            QuestionType.MULTISELECT, id, label, self.option_indices
        )
        value_label_str = value_labels(
            QuestionType.MULTISELECT, id, self.option_indices
        )
        var_level_str = variable_level(
            QuestionType.MULTISELECT, id, "NOMINAL", self.option_indices
        )

        if len(self.option_indices) == 1:
            mrset_str = ""
            warnings.warn(f"{id} have only 1 key for option. Mrset will be None")
        else:
            mrset_str = mrset(id, label, self.option_indices)

        return "\n".join([var_label_str, value_label_str, var_level_str, mrset_str])
