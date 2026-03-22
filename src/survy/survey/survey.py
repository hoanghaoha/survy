from typing import Any
import polars

from survy.survey._utils import extract_mapping
from survy.survey.question import Question


class Survey:
    def __init__(self, df: polars.DataFrame):
        self.df = df
        self._metadata = {}

    @property
    def questions(self) -> list[Question]:
        results = []
        for col in self.df.columns:
            series = self.df[col]
            mapping = (
                {} if series.dtype.is_numeric() else extract_mapping(series.to_list())
            )
            question = Question(
                id=series.name,
                label=series.name,
                mapping=mapping,
                values=series,
            )
            metadata = self._metadata.get(series.name, {})
            question.update(
                label=metadata.get("label", ""), mapping=metadata.get("mapping", {})
            )
            results.append(question)

        return results

    def update_metadata(self, metadata: dict[str, dict[str, Any]]):
        for id, info in metadata.items():
            self._metadata[id] = info

    def to_dict(self):
        return [question.to_dict() for question in self.questions]
