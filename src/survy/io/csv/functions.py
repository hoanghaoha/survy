from pathlib import Path
from typing import Any

import polars as pl

from survy.errors import FileTypeError
from survy.io._utils import process_raw_data
from survy.survey.survey import Survey


def _extract_raw_data_from_path(path: Path) -> dict[str, list[Any]]:
    if path.suffix != ".csv":
        raise FileTypeError("Required .csv file")

    return pl.read_csv(path).to_dict(as_series=False)


def read_csv(path: str | Path) -> Survey:
    if not isinstance(path, Path):
        path = Path(path)

    raw_data = _extract_raw_data_from_path(path)

    return Survey(df=process_raw_data(raw_data))
