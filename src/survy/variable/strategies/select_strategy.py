from typing import Literal
import polars
from survy.variable._utils import VarType
from survy.variable.strategies.base_strategy import _BaseStrategy
from survy.utils.spss import value_labels, variable_labels, variable_level


class _SelectStrategy(_BaseStrategy):
    """
    Strategy for handling single-select (categorical) survey variables.
    """

    def __init__(self, series: polars.Series, value_indices: dict[str, int]) -> None:
        """
        Initialize _SelectStrategy.

        Args:
            series (polars.Series): Raw response data.
            value_indices (dict[str, int]): Mapping from category labels
                to numeric codes.
        """
        self._series = series
        self._value_indices = value_indices

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
            return self._series.replace_strict(
                self._value_indices, default=None
            ).to_frame()

        return self._series.to_frame()

    @property
    def frequencies(self) -> polars.DataFrame:
        """Frequency counts and proportions for each category.

        Returns:
            A DataFrame with columns:
                - option name: the selected category label
                - "count": number of respondents who selected the category
                - "proportion": count divided by total number of respondents

        Notes:
            Null values are excluded from counts but included in the base,
            so proportions may not sum to 1.
        """
        col_name = self._series.name
        base = len(self._series)
        df = (
            self.get_df(dtype="text")
            .filter(polars.col(col_name).is_not_null())[col_name]
            .value_counts(name="count")
            .sort(col_name)
            .with_columns((polars.col("count") / base).alias("proportion"))
        )

        return df

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

        """
        col_name = self._series.name

        var_label_str = variable_labels(VarType.SELECT, col_name, label, self._value_indices)
        value_label_str = value_labels(VarType.SELECT, col_name, self._value_indices)
        var_level_str = variable_level(
            VarType.SELECT, col_name, "NOMINAL", self._value_indices
        )

        return "\n".join([var_label_str, value_label_str, var_level_str])
