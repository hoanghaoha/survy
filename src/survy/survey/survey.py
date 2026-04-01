from pathlib import Path
from typing import Any, Literal
import warnings
import polars
import pyreadstat

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

    def to_spss(self, dir_path: str | Path, name: str = "survey"):
        if not isinstance(dir_path, Path):
            dir_path = Path(dir_path)

        number_df = self.get_df(select_dtype="number", multiselect_dtype="number")
        pyreadstat.write_sav(number_df, dir_path / f"{name}_data.sav")

        with open(dir_path / f"{name}_syntax.sps", "w", encoding="utf-8") as f:
            f.write(self.sps)

    def to_csv(self, dir_path: str | Path, name: str = "survey"):
        if not isinstance(dir_path, Path):
            dir_path = Path(dir_path)

        self.get_df(select_dtype="text", multiselect_dtype="text").write_csv(
            dir_path / f"{name}_text.csv"
        )

        self.get_df(select_dtype="number", multiselect_dtype="number").write_csv(
            dir_path / f"{name}_number.csv"
        )

        polars.DataFrame(
            [
                {"id": question.id, "qtype": question.qtype, "label": question.label}
                for question in self.questions
            ]
        ).write_csv(dir_path / f"{name}_questions_info.csv")

        polars.DataFrame(
            [
                {"id": question.id, "text": op, "index": index}
                for question in self.questions
                for op, index in question.option_indices.items()
            ]
        ).write_csv(dir_path / f"{name}_options_info.csv")
