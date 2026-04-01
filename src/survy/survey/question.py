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
    Representation of a single survey question backed by a Polars Series.

    This class encapsulates a column of survey data and provides utilities
    to infer question type, manage labels and options, and transform data
    using strategy objects.

    Parameters
    ----------
    series : polars.Series
        A Polars Series representing the responses for a single question.
        The series name is used as the question identifier.

    Attributes
    ----------
    series : polars.Series
        Underlying data for the question.
    loop_id : str
        Optional loop identifier used to prefix the label.
    _label : str
        Internal label storage. Falls back to series name if not set.
    _option_indices : dict[str, int]
        Mapping of option values to indices for categorical questions.

    Properties
    ----------
    id : str
        Unique identifier of the question (derived from series name).
    label : str
        Human-readable label. Defaults to series name and may be prefixed
        by loop_id. Truncated to 249 characters if too long.
    dtype : polars.DataType
        Data type of the underlying series.
    qtype : QuestionType
        Inferred question type (SELECT, MULTISELECT, NUMBER).
    option_indices : dict[str, int]
        Mapping of categorical values to indices. Automatically inferred
        if not explicitly set.
    base : int
        Number of non-null / truthy responses.
    len : int
        Total number of responses.
    strategy : BaseStrategy
        Strategy instance used for processing the question based on qtype.
    sub_bases : dict[str, int]
        Subgroup counts computed by the strategy.
    sps : str
        SPSS syntax auto generated of the question (strategy-specific)

    Methods
    -------
    to_dict() -> dict
        Convert the question into a dictionary representation.
    get_df(dtype="text", compact=True) -> polars.DataFrame
        Return a DataFrame representation of the question using the
        associated strategy.

    Raises
    ------
    QuestionTypeError
        If the series dtype cannot be interpreted as a valid question type.
    DataStructureError
        If provided option_indices do not match the data values.

    Warns
    -----
    UserWarning
        If label length exceeds 250 characters (will be truncated).
    UserWarning
        If a non-string dtype is coerced into SELECT type.

    Notes
    -----
    - Question type is inferred automatically from the series dtype:
      - List → MULTISELECT
      - Numeric → NUMBER
      - String → SELECT
    - Strategy pattern is used to delegate behavior based on question type.
    """

    def __init__(self, series: polars.Series):
        self.series = series
        self._option_indices: dict[str, int] = {}
        self._label: str = ""
        self.loop_id: str = ""

        assert self.qtype

    @property
    def id(self) -> str:
        return self.series.name

    @property
    def label(self) -> str:
        """
        Label of the question. Len < 250
        If the question have loop_id, label will be [loop_id] + label
        """
        label = self._label if self._label else self.series.name
        if self.loop_id:
            label = f"[{self.loop_id}] " + label

        if len(label) >= 250:
            warnings.warn(f"{self.id} Len of label > 250 will be truncated")

        return label[:249]

    @label.setter
    def label(self, new_label: str):
        self._label = new_label

    @property
    def option_indices(self) -> dict[str, int]:
        if self.series.dtype.is_numeric():
            return {}

        return (
            self._option_indices
            if self._option_indices
            else extract_mapping(self.series.to_list())
        )

    @option_indices.setter
    def option_indices(self, new_option_indices):
        for v in extract_mapping(self.series.to_list()).keys():
            if v not in new_option_indices.keys():
                raise DataStructureError(f"Value is not have option index: {v}")
        self._option_indices = new_option_indices

    @property
    def dtype(self) -> polars.DataType:
        return self.series.dtype

    @property
    def qtype(self) -> QuestionType:
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
        return len([i for i in self.series.to_list() if i])

    @property
    def len(self) -> int:
        return self.series.shape[0]

    @property
    def strategy(self) -> BaseStrategy:
        return {
            QuestionType.SELECT: SelectStrategy,
            QuestionType.MULTISELECT: MultiSelectStrategy,
            QuestionType.NUMBER: NumberStrategy,
        }[self.qtype](self.series, self.option_indices)

    def to_dict(self) -> dict:
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
        return self.strategy.sub_bases

    @property
    def sps(self) -> str:
        return self.strategy.get_sps(self.label)

    def get_df(
        self, dtype: Literal["number", "text"] = "text", compact: bool = True
    ) -> polars.DataFrame:
        return self.strategy.get_df(dtype=dtype, compact=compact)
