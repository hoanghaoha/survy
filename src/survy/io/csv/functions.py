from pathlib import Path
from typing import Any

import polars

from survy.errors import FileTypeError
from survy.io._utils import process_raw_data
from survy.survey.question import Question
from survy.survey.survey import Survey
from survy.utils.functions import extract_mapping


def _extract_raw_data_from_path(path: Path) -> dict[str, list[Any]]:
    if path.suffix != ".csv":
        raise FileTypeError("Required .csv file")

    return polars.read_csv(path).to_dict(as_series=False)


def _process_series(series: polars.Series) -> Question:
    mapping = (
        {}
        if series.dtype.is_numeric() or series.dtype == polars.Datetime
        else extract_mapping(series.to_list())
    )
    values = series.replace({"": None}) if series.dtype == polars.String else series
    question = Question(
        label=series.name,
        values=values,
        mapping=mapping,
    )
    return question


def get_question_from_df(df) -> list[Question]:
    return [_process_series(df[col]) for col in df.columns]


def read_csv(path: str | Path) -> Survey:
    if not isinstance(path, Path):
        path = Path(path)

    raw_data = _extract_raw_data_from_path(path)

    return Survey(questions=get_question_from_df(process_raw_data(raw_data)))
