from pathlib import Path
import polars

from survy.errors import FileTypeError
from survy.io.polars import read_polars
from survy.survey.survey import Survey


def read_csv(
    path: str | Path,
    compact_ids: list[str] = [],
    compact_separator: str = ";",
    name_pattern: str = "id(.loop)?(_multi)?",
) -> Survey:
    if not isinstance(path, Path):
        path = Path(path)

    if path.suffix != ".csv":
        raise FileTypeError("Required .csv file")

    return read_polars(
        raw_df=polars.read_csv(path),
        compact_ids=compact_ids,
        compact_separator=compact_separator,
        name_pattern=name_pattern,
    )
