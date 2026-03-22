import polars as pl
from dataclasses import dataclass

from survy.errors import DataStructureError, DataTypeError
from survy.separator import MULTISELECT
from survy.survey._utils import extract_mapping


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
    def is_multi(self):
        if self.values.dtype == pl.List:
            return True
        return False

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

    def numberize(self) -> pl.DataFrame:
        if self.is_multi:
            df = self.values.to_frame()
            df = df.with_columns(
                [
                    pl.col(self.id)
                    .list.contains(val)
                    .cast(pl.Int8)
                    .alias(f"{self.id}{MULTISELECT}{index}")
                    for val, index in self.mapping.items()
                ]
            )
            return df.drop(self.id)
        elif self.dtype.is_numeric():
            return self.values.to_frame()
        else:
            return self.values.replace_strict(self.mapping, default=None).to_frame()
