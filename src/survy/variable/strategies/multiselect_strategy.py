from typing import Literal
import warnings
import polars
from survy.separators import MULTISELECT
from survy.variable._utils import VarType
from survy.variable.strategies.base_strategy import _BaseStrategy
from survy.utils.spss import mrset, value_labels, variable_labels, variable_level


class _MultiSelectStrategy(_BaseStrategy):
    """
    Strategy for handling multi-select survey variables.

    Multi-select variables contain multiple responses per entry,
    typically stored as a list of selected options.
    """

    def __init__(self, series: polars.Series, value_indices: dict[str, int]) -> None:
        """
        Initialize _MultiSelectStrategy.

        Args:
            series (polars.Series): Series containing list-like responses.
            value_indices (dict[str, int]): Mapping of option labels to indices.
        """
        self._series = series
        self._value_indices = value_indices

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
        col_name = self._series.name
        df = self._series.to_frame()

        match dtype:
            case "compact":
                return df
            case "number":
                return df.with_columns(
                    [
                        polars.col(col_name)
                        .list.contains(val)
                        .cast(polars.Int8)
                        .alias(f"{col_name}{MULTISELECT}{index}")
                        for val, index in self._value_indices.items()
                    ]
                ).drop(col_name)
            case "text":
                return df.with_columns(
                    [
                        polars.col(col_name)
                        .list.contains(val)
                        .cast(polars.Int8)
                        .replace_strict({1: val}, default=None)
                        .alias(f"{col_name}{MULTISELECT}{index}")
                        for val, index in self._value_indices.items()
                    ]
                ).drop(col_name)
            case _:
                raise KeyError(f"Unsupported dtype: {dtype}")

    @property
    def frequencies(self) -> polars.DataFrame:
        """Frequency counts and proportions for each selected option.

        Returns:
            A DataFrame with columns:
                - option name: the selected option label
                - "count": number of respondents who selected the option
                - "proportion": count divided by total number of respondents

        Notes:
            Null values are ignored. MULTISELECT responses are exploded
            before counting, so a single respondent may contribute to
            multiple rows.
        """
        col_name = self._series.name
        base = len(self._series)
        df = (
            self.get_df(dtype="compact")
            .explode(col_name)[col_name]
            .value_counts(name="count")
            .sort(col_name)
            .with_columns((polars.col("count") / base).alias("proportion"))
        )

        return df

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
            - MRSETS is skipped if only one option exists.
        """
        col_name = self._series.name

        var_label_str = variable_labels(
            VarType.MULTISELECT, col_name, label, self._value_indices
        )
        value_label_str = value_labels(VarType.MULTISELECT, col_name, self._value_indices)
        var_level_str = variable_level(
            VarType.MULTISELECT, col_name, "NOMINAL", self._value_indices
        )

        if len(self._value_indices) == 1:
            mrset_str = ""
            warnings.warn(f"{col_name} have only 1 key for option. Mrset will be None")
        else:
            mrset_str = mrset(col_name, label, self._value_indices)

        return "\n".join([var_label_str, value_label_str, var_level_str, mrset_str])
