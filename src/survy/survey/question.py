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
            "label": self.label,
            "option_indices": self.option_indices,
            "values": self.series.to_list(),
        }

    @property
    def sub_bases(self) -> dict[str, int]:
        return self.strategy.sub_bases

    def get_df(
        self, dtype: Literal["number", "text"] = "text", compact: bool = True
    ) -> polars.DataFrame:
        return self.strategy.get_df(dtype=dtype, compact=compact)
