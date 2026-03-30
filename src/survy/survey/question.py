from typing import Literal
import warnings

import polars

from survy.errors import DataStructureError, QuestionTypeError
from survy.separator import MULTISELECT
from survy.survey._utils import QuestionType
from survy.utils.functions import extract_mapping


class Question:
    def __init__(self, series: polars.Series):
        self.series = series
        self._option_indices: dict[str, int] = {}
        self._label: str = ""
        self.loop_id: str = ""

    @property
    def id(self) -> str:
        return self.series.name

    @property
    def label(self) -> str:
        label = self._label if self._label else self.series.name
        if self.loop_id:
            return f"[{self.loop_id}] " + label
        else:
            return label

    @label.setter
    def label(self, new_label: str):
        if len(new_label) > 250:
            warnings.warn(f"{self.id} Len of label > 250 will be truncated")
        self._label = new_label[:250]

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
        if self.series.dtype == polars.List:
            return QuestionType.MULTISELECT
        elif self.series.dtype.is_numeric():
            return QuestionType.NUMBER
        elif self.series.dtype == polars.String:
            return QuestionType.SELECT
        raise QuestionTypeError(f"Can not identify question type: {self.series.dtype}")

    @property
    def base(self) -> int:
        return len([i for i in self.series.to_list() if i])

    @property
    def len(self) -> int:
        return self.series.shape[0]

    @property
    def sub_bases(self) -> dict[str, int]:
        if self.qtype == QuestionType.MULTISELECT:
            df = self.get_df(dtype="text", compact=True).explode(self.id)
        else:
            df = self.get_df(dtype="text")

        result = (
            df.filter(polars.col(self.id).is_not_null())
            .group_by(self.id)
            .agg(polars.col(self.id).count().alias("base"))
            .rename({self.id: "option"})
            .sort("option")
            .to_dicts()
        )

        return {item["option"]: item["base"] for item in result}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "option_indices": self.option_indices,
            "values": self.series.to_list(),
        }

    def get_df(
        self, dtype: Literal["number", "text"] = "text", compact: bool = True
    ) -> polars.DataFrame:
        def _get_multiselect_df():
            df = self.series.to_frame()
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
                            for val, index in self.option_indices.items()
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
                            for val, index in self.option_indices.items()
                        ]
                    )
                    return text_df.drop(self.id)

        def _get_number_df():
            return self.series.to_frame()

        def _get_select_df():
            if dtype == "number":
                return self.series.replace_strict(
                    self.option_indices, default=None
                ).to_frame()
            else:
                return self.series.to_frame()

        return {
            QuestionType.MULTISELECT: _get_multiselect_df,
            QuestionType.SELECT: _get_select_df,
            QuestionType.NUMBER: _get_number_df,
        }[self.qtype]()
