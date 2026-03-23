from pathlib import Path
from typing import Any, Literal
import polars
import pyreadstat

from survy.survey.question import Question, QuestionType
from survy.utils.spss import create_sps


class Survey:
    def __init__(self, questions: list[Question]):
        self.questions = questions

    @property
    def sps(self) -> str:
        return create_sps(self.questions)

    def __getitem__(self, question_id: str):
        return {question.id: question for question in self.questions}[question_id]

    def update(self, metadata: dict[str, dict[str, Any]]):
        for id, info in metadata.items():
            question = self[id]
            question.update(
                label=info.get("label", ""), mapping=info.get("mapping", {})
            )

    def to_dict(self):
        return [question.to_dict() for question in self.questions]

    def get_df(
        self,
        select_dtype: Literal["number", "text"] = "text",
        multiselect_compact: bool = False,
        multiselect_dtype: Literal["number", "text"] = "number",
    ) -> polars.DataFrame:
        dfs = []
        for question in self.questions:
            if question.qtype == QuestionType.MULTISELECT:
                dfs.append(question.get_df(multiselect_dtype, multiselect_compact))
            elif question.qtype == QuestionType.SELECT:
                dfs.append(question.get_df(select_dtype))
            else:
                dfs.append(question.get_df("number"))
        return polars.concat(dfs, how="horizontal")

    def to_csv(self, dir_path: str | Path):
        if not isinstance(dir_path, Path):
            dir_path = Path(dir_path)

        self.get_df(
            select_dtype="text", multiselect_compact=False, multiselect_dtype="text"
        ).write_csv(dir_path / "text_wide.csv")

        self.get_df(
            select_dtype="number", multiselect_compact=False, multiselect_dtype="number"
        ).write_csv(dir_path / "number_wide.csv")

        polars.DataFrame(
            [
                {"id": question.id, "qtype": question.qtype, "label": question.label}
                for question in self.questions
            ]
        ).write_csv(dir_path / "questions_info.csv")

        polars.DataFrame(
            [
                {"id": question.id, "text": op, "index": index}
                for question in self.questions
                for op, index in question.mapping.items()
            ]
        ).write_csv(dir_path / "options_info.csv")

    def to_spss(self, dir_path: str | Path):
        if not isinstance(dir_path, Path):
            dir_path = Path(dir_path)

        number_df = self.get_df(
            select_dtype="number", multiselect_compact=False, multiselect_dtype="number"
        )
        pyreadstat.write_sav(number_df, dir_path / "data.sav")

        with open(dir_path / "syntax.sps", "w", encoding="utf-8") as f:
            f.write(self.sps)
