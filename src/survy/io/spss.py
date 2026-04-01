from pathlib import Path

import pyreadstat

from survy.survey.survey import Survey


def to_spss(
    survey: Survey, path: str | Path, name: str = "survey", encoding: str = "utf-8"
):
    """Export a Survey to SPSS data and syntax files.

    This function writes two files:
    - A `.sav` file containing the survey data (numeric representation).
    - A `.sps` syntax file containing SPSS syntax generated from the survey.

    Args:
        survey (Survey): The Survey instance to export.
        path (str | pathlib.Path): Directory where output files will be saved.
        name (str, optional): Base name for the output files. Defaults to "survey".
        encoding (str): Encoding type for write sps file.

    Returns:
        None

    Raises:
        OSError: If files cannot be written to the specified location.

    Notes:
        - Only numeric data is exported to the `.sav` file.
        - Output files will be named `{name}_data.sav` and `{name}_syntax.sps`.
    """
    if not isinstance(path, Path):
        path = Path(path)

    number_df = survey.get_df(select_dtype="number", multiselect_dtype="number")
    pyreadstat.write_sav(number_df, path / f"{name}_data.sav")

    with open(path / f"{name}_syntax.sps", "w", encoding=encoding) as f:
        f.write(survey.sps)
