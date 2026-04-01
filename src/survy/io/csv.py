from pathlib import Path
import polars

from survy.errors import FileTypeError
from survy.io.polars import read_polars
from survy.survey.survey import Survey


def read_csv(
    path: str | Path,
    compact_ids: list[str] | None = None,
    compact_separator: str = ";",
    name_pattern: str = "id(.loop)?(_multi)?",
) -> Survey:
    """
    Read a CSV file and return a Survey object.

    This is the main entry point for reading survey data.

    Args:
        path (str | Path):
            Path to the CSV file.
        compact_ids (list[str] | None):
            IDs of questions using compact multi-select encoding.
        compact_separator (str):
            Separator for compact multi-select values.
        name_pattern (str):
            Pattern for parsing column names into id/loop/multi components.

    Returns:
        Survey: Parsed survey object.

    Raises:
        FileTypeError: If input file is not .csv
    """
    if not isinstance(path, Path):
        path = Path(path)

    if path.suffix != ".csv":
        raise FileTypeError("Required .csv file")

    compact_ids = compact_ids or []

    return read_polars(
        raw_df=polars.read_csv(path),
        compact_ids=compact_ids,
        compact_separator=compact_separator,
        name_pattern=name_pattern,
    )
