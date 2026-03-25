from pathlib import Path
import polars

from survy.errors import FileTypeError
from survy.io.polars import read_polars
from survy.survey.survey import Survey


def read_csv(
    path: str | Path,
    multiselects_as_single_column: list[str] = [],
    multiselect_separator: str = ";",
    name_pattern: str = "id(.matrix)?(_multi)?",
) -> Survey:
    if not isinstance(path, Path):
        path = Path(path)

    if path.suffix != ".csv":
        raise FileTypeError("Required .csv file")

    df = polars.read_csv(path)

    return read_polars(
        df,
        multiselects_as_single_column=multiselects_as_single_column,
        multiselect_separator=multiselect_separator,
        name_pattern=name_pattern,
    )
