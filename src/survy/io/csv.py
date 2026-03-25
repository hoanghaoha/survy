from pathlib import Path
import polars

from survy.errors import FileTypeError
from survy.io._utils import process_polars_df
from survy.survey.survey import Survey


def read_csv(path: str | Path, name_pattern: str = "id(.matrix)?(_multi)?") -> Survey:
    if not isinstance(path, Path):
        path = Path(path)

    if path.suffix != ".csv":
        raise FileTypeError("Required .csv file")

    df = polars.read_csv(path)

    return Survey(questions=process_polars_df(df, name_pattern))
