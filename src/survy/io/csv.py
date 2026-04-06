from pathlib import Path
import polars

from survy.errors import FileTypeError
from survy.io.polars import read_polars
from survy.variable._utils import VarType
from survy.survey.survey import Survey


def read_csv(
    path: str | Path,
    compact_ids: list[str] | None = None,
    compact_separator: str = ";",
    auto_detect: bool = False,
    name_pattern: str = "id(_multi)?",
) -> Survey:
    """
    Read a CSV file and return a Survey object.

    This is the main entry point for reading survey data.

    Args:
        path (str | Path):
            Path to the CSV file.
        compact_ids (list[str] | None):
            IDs of variables using compact multi-select encoding.
        compact_separator (str):
            Separator for compact multi-select values.
        auto_detect (bool):
            Auto parse multi-select if data have compact_separator.
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
        auto_detect=auto_detect,
        name_pattern=name_pattern,
    )


def to_csv(
    survey: Survey,
    path: str | Path = "",
    name: str = "survey",
    compact: bool = True,
    compact_separator: str = ";",
):
    """
    Export a Survey to CSV files.

    This function writes three CSV files:
    - `{name}_data.csv`: Survey response data.
    - `{name}_variables_info.csv`: Metadata about variables.
    - `{name}_options_info.csv`: Mapping of option text to indices.

    Args:
        survey (Survey): The Survey instance to export.
        path (str | pathlib.Path): Directory where output files will be saved.
        name (str, optional): Base name for output files. Defaults to "survey".
        compact (bool, optional): Whether to compact multiselect responses into
            a single column by joining list values. Defaults to True.
        compact_separator (str, optional): Separator used when joining
            multiselect values in compact mode. Defaults to ";".

    Returns:
        None

    Raises:
        OSError: If files cannot be written to the specified location.

    Notes:
        - In compact mode, multiselect responses (list columns) are joined into
          strings using the specified separator.
        - In non-compact mode, multiselect responses are exported as boolean columns
        - The `{name}_variables_info.csv` file contains variable IDs, types,
          and labels.
        - The `{name}_options_info.csv` file contains option text and their
          corresponding indices for each variable.
    """
    if not isinstance(path, Path):
        path = Path(path)

    if compact:
        multiselect_ids = [
            variable.id
            for variable in survey.variables
            if variable.vtype == VarType.MULTISELECT
        ]

        survey.get_df(select_dtype="text", multiselect_dtype="compact").with_columns(
            [
                polars.col(i).list.join(compact_separator).alias(i)
                for i in multiselect_ids
            ]
        ).select([variable.id for variable in survey.variables]).write_csv(
            path / f"{name}_data.csv"
        )
    else:
        survey.get_df(select_dtype="text", multiselect_dtype="text").write_csv(
            path / f"{name}_data.csv"
        )

    polars.DataFrame(
        [
            {"id": variable.id, "vtype": variable.vtype, "label": variable.label}
            for variable in survey.variables
        ]
    ).write_csv(path / f"{name}_variables_info.csv")

    polars.DataFrame(
        [
            {"id": variable.id, "text": op, "index": index}
            for variable in survey.variables
            for op, index in variable.value_indices.items()
        ]
    ).write_csv(path / f"{name}_options_info.csv")
