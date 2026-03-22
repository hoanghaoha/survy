import polars as pl
from dataclasses import dataclass

from survy.errors import DataStructureError, DataTypeError


@dataclass
class Question:
    id: str
    label: str
    mapping: dict[str, int]
    values: pl.Series

    @property
    def dtype(self):
        return self.values.dtype

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
            for v in set(self.values):
                if v not in mapping.keys():
                    raise DataStructureError(f"Value is not have mapping index: {v}")
            self.mapping = mapping
