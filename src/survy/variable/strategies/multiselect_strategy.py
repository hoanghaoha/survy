from typing import Literal
import warnings
import polars
from survy.separators import MULTISELECT
from survy.variable._utils import VarType
from survy.variable.strategies.base_strategy import BaseStrategy
from survy.utils.spss import mrset, value_labels, variable_labels, variable_level


class MultiSelectStrategy(BaseStrategy):
    """
    Strategy for handling multi-select survey variables.

    Multi-select variables contain multiple responses per entry,
    typically stored as a list of selected options.
    """

    def __init__(self, series: polars.Series, value_indices: dict[str, int]) -> None:
        """
        Initialize MultiSelectStrategy.

        Args:
            series (polars.Series): Series containing list-like responses.
            value_indices (dict[str, int]): Mapping of option labels to indices.
        """
        self.series = series
        self.value_indices = value_indices

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
                    - "compact": original list column

        Returns:
            polars.DataFrame: Transformed DataFrame.

        Notes:
            - Expanded columns are named as: {id}{MULTISELECT}{index}
            - Uses `list.contains` to detect option presence
        """
        dtype: Literal["number", "text", "compact"] = kwargs.get("dtype", "text")
        id = self.series.name
        df = self.series.to_frame()

        match dtype:
            case "compact":
                return df
            case "number":
                return df.with_columns(
                    [
                        polars.col(id)
                        .list.contains(val)
                        .cast(polars.Int8)
                        .alias(f"{id}{MULTISELECT}{index}")
                        for val, index in self.value_indices.items()
                    ]
                ).drop(id)
            case "text":
                return df.with_columns(
                    [
                        polars.col(id)
                        .list.contains(val)
                        .cast(polars.Int8)
                        .replace_strict({1: val}, default=None)
                        .alias(f"{id}{MULTISELECT}{index}")
                        for val, index in self.value_indices.items()
                    ]
                ).drop(id)
            case _:
                raise KeyError(f"Unsupported dtype: {dtype}")

    @property
    def frequencies(self) -> dict[str, int]:
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
        df = self.get_df(dtype="compact").explode(id)

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
        Generate SPSS syntax for a multi-select variable.

        This includes:
        - Variable labels
        - Value labels
        - Variable level (nominal)
        - MRSETS definition (if applicable)

        Args:
            label (str): Variable label.

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
            VarType.MULTISELECT, id, label, self.value_indices
        )
        value_label_str = value_labels(VarType.MULTISELECT, id, self.value_indices)
        var_level_str = variable_level(
            VarType.MULTISELECT, id, "NOMINAL", self.value_indices
        )

        if len(self.value_indices) == 1:
            mrset_str = ""
            warnings.warn(f"{id} have only 1 key for option. Mrset will be None")
        else:
            mrset_str = mrset(id, label, self.value_indices)

        return "\n".join([var_label_str, value_label_str, var_level_str, mrset_str])
