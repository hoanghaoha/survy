from typing import Literal
import warnings

import polars

from survy.errors import DataStructureError, QuestionTypeError
from survy.survey._utils import QuestionType
from survy.survey.strategies.base_strategy import BaseStrategy
from survy.survey.strategies.multiselect_strategy import MultiSelectStrategy
from survy.survey.strategies.number_strategy import NumberStrategy
from survy.survey.strategies.select_strategy import SelectStrategy
from survy.utils.functions import extract_mapping


class Question:
    """
    Represents a single survey question backed by a Polars Series.

    Attributes:
        series (polars.Series): Raw data for the question.
        loop_id (str): Optional loop identifier for repeated questions.
    """

    def __init__(self, series: polars.Series):
        """
        Initialize a Question instance.

        Args:
            series (polars.Series): The data column representing the question.

        Raises:
            AssertionError: If question type cannot be determined.
        """
        self.series = series
        self._option_indices: dict[str, int] = {}
        self._label: str = ""
        self.loop_id: str = ""

        assert self.qtype

    @property
    def id(self) -> str:
        """
        Returns the question identifier (column name).

        Returns:
            str: Question ID.
        """
        return self.series.name

    @property
    def label(self) -> str:
        """
        Returns the display label of the question.

        - Uses custom label if set, otherwise defaults to column name.
        - Prepends loop_id if present.
        - Truncates label to 249 characters.

        Returns:
            str: Formatted label.
        """
        label = self._label if self._label else self.series.name
        if self.loop_id:
            label = f"[{self.loop_id}] " + label

        if len(label) >= 250:
            warnings.warn(f"{self.id} Len of label > 250 will be truncated")

        return label[:249]

    @label.setter
    def label(self, new_label: str):
        """
        Set a custom label for the question.

        Args:
            new_label (str): New label.
        """
        self._label = new_label

    @property
    def option_indices(self) -> dict[str, int]:
        """
        Returns mapping of response values to numeric indices.

        - For numeric questions, returns empty dict.
        - If not manually set, inferred from data.

        Returns:
            dict[str, int]: Value-to-index mapping.
        """
        if self.series.dtype.is_numeric():
            return {}

        return (
            self._option_indices
            if self._option_indices
            else extract_mapping(self.series.to_list())
        )

    @option_indices.setter
    def option_indices(self, new_option_indices):
        """
        Set custom option index mapping.

        Ensures all existing values are covered.

        Args:
            new_option_indices (dict[str, int]): Mapping of values to indices.

        Raises:
            DataStructureError: If any value is missing from mapping.
        """
        for v in extract_mapping(self.series.to_list()).keys():
            if v not in new_option_indices.keys():
                raise DataStructureError(f"Value is not have option index: {v}")
        self._option_indices = new_option_indices

    @property
    def dtype(self) -> polars.DataType:
        """
        Returns the data type of the series.

        Returns:
            polars.DataType: Series data type.
        """
        return self.series.dtype

    @property
    def qtype(self) -> QuestionType:
        """
        Infers the question type based on data type.

        Rules:
            - List → MULTISELECT
            - Numeric → NUMBER
            - String → SELECT
            - Otherwise, attempts cast to string → SELECT

        Returns:
            QuestionType: Inferred question type.

        Raises:
            QuestionTypeError: If type cannot be determined.
        """
        dtype = self.dtype

        if dtype == polars.List:
            return QuestionType.MULTISELECT

        if dtype.is_numeric():
            return QuestionType.NUMBER

        if dtype == polars.String:
            return QuestionType.SELECT
        try:
            self.series.cast(polars.String)
        except Exception as e:
            raise QuestionTypeError from e

        warnings.warn(f"{self.id} with dtype {self.series.dtype} converted to SELECT")
        return QuestionType.SELECT

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
        Returns the appropriate strategy instance for the question.

        Strategy is selected based on question type.

        Returns:
            BaseStrategy: Strategy instance.
        """
        return {
            QuestionType.SELECT: SelectStrategy,
            QuestionType.MULTISELECT: MultiSelectStrategy,
            QuestionType.NUMBER: NumberStrategy,
        }[self.qtype](self.series, self.option_indices)

    def to_dict(self) -> dict:
        """
        Serializes the question into a dictionary.

        Returns:
            dict: Question representation.
        """
        return {
            "id": self.id,
            "label": self._label,
            "option_indices": self.option_indices,
            "values": self.series.to_list(),
            "qtype": self.qtype,
            "loop_id": self.loop_id,
        }

    @property
    def sub_bases(self) -> dict[str, int]:
        """
        Returns sub-base counts from the strategy.

        Returns:
            dict[str, int]: Sub-base values.
        """
        return self.strategy.sub_bases

    @property
    def sps(self) -> str:
        """
        Returns SPSS syntax representation of the question.

        Returns:
            str: SPSS syntax string.
        """
        return self.strategy.get_sps(self.label)

    def get_df(
        self, dtype: Literal["number", "text"] = "text", compact: bool = True
    ) -> polars.DataFrame:
        """
        Returns a processed DataFrame representation of the question.

        Args:
            dtype (Literal["number", "text"], optional):
                Output format. Defaults to "text".
            compact (bool, optional):
                Use for MULTISELECT question.
                Whether to return compact format. Defaults to True.

        Returns:
            polars.DataFrame: Processed DataFrame.
        """
        return self.strategy.get_df(dtype=dtype, compact=compact)

