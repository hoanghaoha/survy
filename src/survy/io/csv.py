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

    Parameters
    ----------
    path : str or Path
        Path to the CSV file.
    compact_ids : list[str], optional
        List of column names that represent multi-select responses stored
        as a single delimited string. These will be split into lists.
    compact_separator : str, default=";"
        Delimiter used to split multi-select values in compact columns.
    name_pattern : str, default="id(.loop)?(_multi)?"
        Regular expression used to parse column names into components
        such as question id, loop indicator, and multi-select flag.

    Returns
    -------
    Survey
        A Survey object containing parsed questions and responses.

    Raises
    ------
    FileTypeError
        If the provided file is not a `.csv` file.
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
