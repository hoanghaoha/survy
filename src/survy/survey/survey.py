from pathlib import Path
from typing import Any, Literal
import warnings
import polars

from survy.survey.question import Question, QuestionType


class Survey:
    def __init__(self, questions: list[Question]):
        self.questions = questions

    def __getitem__(self, question_id: str):
        return {question.id: question for question in self.questions}[question_id]

    def get_df(
        self,
        select_dtype: Literal["number", "text"] = "text",
        multiselect_dtype: Literal["number", "text", "compact"] = "number",
    ) -> polars.DataFrame:
        dfs = []
        for question in self.questions:
            if question.qtype == QuestionType.MULTISELECT:
                dfs.append(question.get_df(multiselect_dtype))
            elif question.qtype == QuestionType.SELECT:
                dfs.append(question.get_df(select_dtype))
            else:
                dfs.append(question.get_df())
        return polars.concat(dfs, how="horizontal")

    @property
    def sps(self) -> str:
        commands = []

        for question in self.questions:
            commands.append(f"**{question.id}")
            commands.append(question.sps)

        return "\n".join(commands)

    def update(self, metadata: list[dict[str, Any]]):
        for info in metadata:
            id = info["id"]
            if id in [q.id for q in self.questions]:
                question = self[info["id"]]
                question.label = info.get("label", "")
                question.option_indices = info.get("option_indices", {})
            else:
                warnings.warn(f"Id is not in survey: {id}")

    def to_json(
        self, path: str | Path, name: str = "survey", encoding: str = "utf-8"
    ) -> None:
        from survy.io.json import to_json

        to_json(self, path, name, encoding)

    def to_spss(self, path: str | Path, name: str = "survey", encoding: str = "utf-8"):
        from survy.io.spss import to_spss

        to_spss(self, path, name, encoding)

    def to_csv(
        self,
        path: str | Path,
        name: str = "survey",
        compact: bool = False,
        compact_separator: str = ";",
    ):
        from survy.io.csv import to_csv

        to_csv(self, path, name, compact, compact_separator)
