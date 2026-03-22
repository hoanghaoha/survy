from pathlib import Path
from typing import Any, Literal
import polars
import pyreadstat

from survy.survey._utils import extract_mapping
from survy.survey.config import MULTISELECT_COMPACT, MULTISELECT_DTYPE, SELECT_DTYPE
from survy.survey.question import Question, QuestionType
from survy.utils.spss import create_sps


def _process_series(series: polars.Series, metadata: dict) -> Question:
    mapping = {} if series.dtype.is_numeric() else extract_mapping(series.to_list())
    values = series.replace({"": None}) if series.dtype == polars.String else series
    question = Question(
        id=series.name,
        label=series.name,
        values=values,
        mapping=mapping,
    )
    metadata = metadata.get(series.name, {})
    question.update(
        label=metadata.get("label", ""), mapping=metadata.get("mapping", {})
    )
    return question


class Survey:
    def __init__(self, df: polars.DataFrame):
        self.df = df
        self._metadata = {}

    @property
    def questions(self) -> list[Question]:
        return [
            _process_series(self.df[col], self._metadata) for col in self.df.columns
        ]

    @property
    def sps(self) -> str:
        return create_sps(self.questions)

    def update_metadata(self, metadata: dict[str, dict[str, Any]]):
        for id, info in metadata.items():
            self._metadata[id] = info

    def to_dict(self):
        return [question.to_dict() for question in self.questions]

    def get_df(
        self,
        select_dtype: Literal["number", "text"] = SELECT_DTYPE,
        multiselect_compact: bool = MULTISELECT_COMPACT,
        multiselect_dtype: Literal["number", "text"] = MULTISELECT_DTYPE,
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
