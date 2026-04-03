from typing import Literal
import warnings

import polars

from survy.errors import DataStructureError, VarTypeError
from survy.variable._utils import VarType
from survy.variable.strategies.base_strategy import BaseStrategy
from survy.variable.strategies.multiselect_strategy import MultiSelectStrategy
from survy.variable.strategies.number_strategy import NumberStrategy
from survy.variable.strategies.select_strategy import SelectStrategy
from survy.utils.functions import extract_mapping


class Variable:
    """
    Represents a single survey variable backed by a Polars Series.

    Attributes:
        series (polars.Series): Raw data for the variable.
    """

    def __init__(self, series: polars.Series):
        """
        Initialize a Variable instance.

        Args:
            series (polars.Series): The data column representing the variable.

        Raises:
            AssertionError: If variable type cannot be determined.
        """
        self.series = series
        self._value_indices: dict[str, int] = {}
        self._label: str = ""

        assert self.vtype

    @property
    def id(self) -> str:
        """
        Returns the variable identifier (column name).

        Returns:
            str: Variable ID.
        """
        return self.series.name

    @property
    def label(self) -> str:
        """
        Returns the display label of the variable.

        - Uses custom label if set, otherwise defaults to column name.
        - Prepends loop_id if present.
        - Truncates label to 249 characters.

        Returns:
            str: Formatted label.
        """
        label = self._label if self._label else self.series.name

        return label

    @label.setter
    def label(self, new_label: str):
        """
        Set a custom label for the variable.

        Args:
            new_label (str): New label.
        """
        self._label = new_label

    @property
    def value_indices(self) -> dict[str, int]:
        """
        Returns mapping of response values to numeric indices.

        - For numeric variable, returns empty dict.
        - If not manually set, inferred from data.

        Returns:
            dict[str, int]: Value-to-index mapping.
        """
        if self.series.dtype.is_numeric():
            return {}

        return (
            self._value_indices
            if self._value_indices
            else extract_mapping(self.series.to_list())
        )

    @value_indices.setter
    def value_indices(self, new_value_indices):
        """
        Set custom value index mapping.

        Ensures all existing values are covered.

        Args:
            new_value_indices (dict[str, int]): Mapping of values to indices.

        Raises:
            DataStructureError: If any value is missing from mapping.
        """
        if self.series.dtype.is_numeric():
            warnings.warn(f"NUMBER {self.id} can not be updated value_indices")
        else:
            for v in extract_mapping(self.series.to_list()).keys():
                if v not in new_value_indices.keys():
                    raise DataStructureError(
                        f"{self.id}: Value is not have option index: {v}"
                    )
            self._value_indices = new_value_indices

    @property
    def dtype(self) -> polars.DataType:
        """
        Returns the data type of the series.

        Returns:
            polars.DataType: Series data type.
        """
        return self.series.dtype

    @property
    def vtype(self) -> VarType:
        """
        Infers the variable type based on data type.

        Rules:
            - List → MULTISELECT
            - Numeric → NUMBER
            - String → SELECT
            - Otherwise, attempts cast to string → SELECT

        Returns:
            VarType: Inferred variable type.

        Raises:
            VarTypeError: If type cannot be determined.
        """
        dtype = self.dtype

        if dtype == polars.List:
            if all([d == [] for d in self.series.to_list()]):
                self.series = polars.Series(
                    self.series.name, ["" for _ in range(self.len)], dtype=polars.String
                )
                warnings.warn(f"{self.id} with empty list converted to SELECT")
                return VarType.SELECT
            return VarType.MULTISELECT

        if dtype.is_numeric():
            return VarType.NUMBER

        if dtype == polars.String:
            return VarType.SELECT

        try:
            self.series.cast(polars.String)
        except Exception as e:
            raise VarTypeError from e

        warnings.warn(f"{self.id} with dtype {self.series.dtype} converted to SELECT")
        return VarType.SELECT

    @property
    def base(self) -> int:
        """
        Returns the count of non-empty responses.

        Returns:
            int: Base count.
        """
        return len([i for i in self.series.to_list() if i])

    @property
    def len(self) -> int:
        """
        Returns total number of responses.

        Returns:
            int: Length of series.
        """
        return self.series.shape[0]

    @property
    def strategy(self) -> BaseStrategy:
        """
        Returns the appropriate strategy instance for the variable.

        Strategy is selected based on var type.

        Returns:
            BaseStrategy: Strategy instance.
        """
        return {
            VarType.SELECT: SelectStrategy,
            VarType.MULTISELECT: MultiSelectStrategy,
            VarType.NUMBER: NumberStrategy,
        }[self.vtype](self.series, self.value_indices)

    def to_dict(self) -> dict:
        """
        Serializes the variable into a dictionary.

        Returns:
            dict: Variable representation.
        """
        return {
            "id": self.id,
            "data": self.series.to_list(),
            "label": self._label,
            "value_indices": self.value_indices,
            "vtype": self.vtype,
        }

    @property
    def frequencies(self) -> dict[str, int]:
        """
        Returns value counts from the strategy.

        Returns:
            dict[str, int]: Value counts.
        """
        return self.strategy.frequencies

    @property
    def sps(self) -> str:
        """
        Returns SPSS syntax representation of the variable.

        Returns:
            str: SPSS syntax string.
        """
        return self.strategy.get_sps(self.label)

    def get_df(
        self, dtype: Literal["number", "text", "compact"] = "text"
    ) -> polars.DataFrame:
        """
        Returns a processed DataFrame representation of the variable.

        Args:
            dtype (Literal["number", "text", "compact"], optional):
                Output format. Defaults to "text". "compact" only use for MULTISELECT.

        Returns:
            polars.DataFrame: Processed DataFrame.
        """
        return self.strategy.get_df(dtype=dtype)
