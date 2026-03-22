from enum import StrEnum
from typing import Literal
import polars as pl
from dataclasses import dataclass

from survy.errors import DataStructureError, DataTypeError
from survy.separator import MULTISELECT
from survy.survey._utils import extract_mapping


class QuestionType(StrEnum):
    SELECT = "select"
    MULTISELECT = "multiselect"
    NUMBER = "number"


@dataclass
class Question:
    id: str
    label: str
    mapping: dict[str, int]
    values: pl.Series

    @property
    def dtype(self):
        return self.values.dtype

    @property
    def qtype(self):
        if self.values.dtype == pl.List:
            return QuestionType.MULTISELECT
        elif self.values.dtype.is_numeric():
            return QuestionType.NUMBER
        else:
            return QuestionType.SELECT

    def to_dict(self):
        return {
            "id": self.id,
            "label": self.label,
            "mapping": self.mapping,
            "values": self.values.to_list(),
        }

    def update(self, label: str = "", mapping: dict[str, int] = {}):
        if not isinstance(label, str):
            raise DataTypeError("Label required to be str")

        if not isinstance(mapping, dict):
            raise DataTypeError("Mapping required to be str")

        if label:
            self.label = label
        if mapping:
            for v in extract_mapping(self.values.to_list()).keys():
                if v not in mapping.keys():
                    raise DataStructureError(f"Value is not have mapping index: {v}")
            self.mapping = mapping

    def get_df(
        self, dtype: Literal["number", "text"], compact: bool = True
    ) -> pl.DataFrame:
        def _get_multiselect_df():
            df = self.values.to_frame()
            if compact:
                return df
            else:
                if dtype == "number":
                    number_df = df.with_columns(
                        [
                            pl.col(self.id)
                            .list.contains(val)
                            .cast(pl.Int8)
                            .alias(f"{self.id}{MULTISELECT}{index}")
                            for val, index in self.mapping.items()
                        ]
                    )
                    return number_df.drop(self.id)
                else:
                    text_df = df.with_columns(
                        [
                            pl.col(self.id)
                            .list.contains(val)
                            .cast(pl.Int8)
                            .replace_strict({1: val}, default=None)
                            .alias(f"{self.id}{MULTISELECT}{index}")
                            for val, index in self.mapping.items()
                        ]
                    )
                    return text_df.drop(self.id)

        def _get_number_df():
            return self.values.to_frame()

        def _get_select_df():
            if dtype == "number":
                return self.values.replace_strict(self.mapping, default=None).to_frame()
            else:
                return self.values.to_frame()

        return {
            QuestionType.MULTISELECT: _get_multiselect_df,
            QuestionType.SELECT: _get_select_df,
            QuestionType.NUMBER: _get_number_df,
        }[self.qtype]()
