from typing import Literal
from dataclasses import dataclass

import polars

from survy.errors import DataStructureError, QuestionTypeError
from survy.separator import MULTISELECT
from survy.survey._utils import QuestionType
from survy.utils.functions import extract_mapping


@dataclass
class Question:
    label: str
    mapping: dict[str, int]
    values: polars.Series

    @property
    def id(self):
        return self.values.name

    @property
    def dtype(self):
        return self.values.dtype

    @property
    def qtype(self):
        if self.values.dtype == polars.List:
            return QuestionType.MULTISELECT
        elif self.values.dtype.is_numeric():
            return QuestionType.NUMBER
        elif self.values.dtype == polars.String:
            return QuestionType.SELECT
        raise QuestionTypeError(f"Can not identify question type: {self.values.dtype}")

    @property
    def base(self):
        return len([i for i in self.values.to_list() if i])

    def to_dict(self):
        return {
            "id": self.id,
            "label": self.label,
            "mapping": self.mapping,
            "values": self.values.to_list(),
        }

    def update(self, label: str = "", mapping: dict[str, int] = {}):
        if label != "" and isinstance(label, str):
            self.label = label
        if mapping:
            for v in extract_mapping(self.values.to_list()).keys():
                if v not in mapping.keys():
                    raise DataStructureError(f"Value is not have mapping index: {v}")
            self.mapping = mapping

    def get_df(
        self, dtype: Literal["number", "text"], compact: bool = True
    ) -> polars.DataFrame:
        def _get_multiselect_df():
            df = self.values.to_frame()
            if compact:
                return df
            else:
                if dtype == "number":
                    number_df = df.with_columns(
                        [
                            polars.col(self.id)
                            .list.contains(val)
                            .cast(polars.Int8)
                            .alias(f"{self.id}{MULTISELECT}{index}")
                            for val, index in self.mapping.items()
                        ]
                    )
                    return number_df.drop(self.id)
                else:
                    text_df = df.with_columns(
                        [
                            polars.col(self.id)
                            .list.contains(val)
                            .cast(polars.Int8)
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
