from pathlib import Path
from typing import Any, Literal
import warnings

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

    def get_df(
        self,
        select_dtype: Literal["number", "text"] = "text",
        multiselect_compact: bool = True,
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

    def get_info(self, as_yml: bool = False) -> list | str:
        info = {}
        for question in self.questions:
            info[question.id] = {"id": question.id, "label": question.label}
            if question.option_indices:
                info[question.id].update({"option_indices": question.option_indices})

        result = [i for _, i in info.items()]
        if as_yml:
            import yaml

            return yaml.dump(result, default_flow_style=False, allow_unicode=True)

        return result

    def update(self, metadata: list[dict[str, Any]]):
        for info in metadata:
            id = info["id"]
            if id in [q.id for q in self.questions]:
                question = self[info["id"]]
                question.update(
                    label=info.get("label", ""),
                    option_indices=info.get("option_indices", {}),
                )
            else:
                warnings.warn(f"Id is not in survey: {id}")

    def update_by_yml(self, yml: str | Path):
        import yaml

        path = Path(yml)
        if path.is_file():
            with open(yml, "r") as f:
                metadata = yaml.safe_load(f)
        else:
            metadata = yaml.safe_load(str(yml))
        self.update(metadata)

    def to_dict(self):
        return [question.to_dict() for question in self.questions]

    def to_csv(self, dir_path: str | Path, name: str = "survey"):
        if not isinstance(dir_path, Path):
            dir_path = Path(dir_path)

        self.get_df(
            select_dtype="text", multiselect_compact=False, multiselect_dtype="text"
        ).write_csv(dir_path / f"{name}_text.csv")

        self.get_df(
            select_dtype="number", multiselect_compact=False, multiselect_dtype="number"
        ).write_csv(dir_path / f"{name}_number.csv")

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

    def to_spss(self, dir_path: str | Path, name: str = "survey"):
        if not isinstance(dir_path, Path):
            dir_path = Path(dir_path)

        number_df = self.get_df(
            select_dtype="number", multiselect_compact=False, multiselect_dtype="number"
        )
        pyreadstat.write_sav(number_df, dir_path / f"{name}_data.sav")

        with open(dir_path / f"{name}_syntax.sps", "w", encoding="utf-8") as f:
            f.write(self.sps)
