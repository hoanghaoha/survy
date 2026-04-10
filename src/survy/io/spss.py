from pathlib import Path

import pyreadstat

from survy.errors import FileTypeError
from survy.io.polars import read_polars
from survy.survey.survey import Survey


def read_spss(
    path: str | Path,
    name_pattern: str = "id(_multi)?",
) -> Survey:
    """Read an SPSS ``.sav`` file and convert it into a Survey object.

    SPSS ``.sav`` files are always in wide format — each column is a separate
    variable. Multiselect variables are detected automatically from column names
    via ``name_pattern`` (e.g. ``hobby_1``, ``hobby_2`` are merged into a single
    ``MULTISELECT`` variable ``hobby``).

    Args:
        path (str | Path):
            Path to the ``.sav`` file.

        name_pattern (str):
            Format template for parsing column names into wide multiselect
            groups. This is **not** a raw regex — it uses two named tokens:

            - ``id`` — matches the base variable name
            - ``multi`` — matches the numeric suffix

            The recognized separators between tokens are ``_``, ``.``,
            and ``:``. The template is converted internally into a regex
            by ``parse_id()``.

            Examples of how columns are parsed with the default pattern
            ``"id(_multi)?"``:

            - ``"hobby_1"`` → ``id="hobby"``, ``multi="1"`` (grouped)
            - ``"hobby_2"`` → ``id="hobby"``, ``multi="2"`` (grouped)
            - ``"gender"``  → ``id="gender"``, no ``multi`` (normal column)

            To match a different separator convention, change the template::

                # Columns named Q1.1, Q1.2, Q2.1, ...
                name_pattern="id.multi"

                # Columns named Q1:a, Q1:b, ...
                name_pattern="id:multi"

    Returns:
        Survey:
            Parsed survey object with variables inferred from the ``.sav`` data.

    Raises:
        FileTypeError:
            If the input file does not have a ``.sav`` extension.

    Examples:
        **Wide format** — multiselect columns detected automatically:

        Input ``.sav`` (``data.sav``):

        >>> # gender, yob, hobby_1, hobby_2, hobby_3, animal_1, animal_2
        >>> # Male,   2000, Book,   ,        Sport,   Cat,      Dog
        >>> # Female, 1999, ,       Movie,   ,        ,         Dog
        >>> # Male,   1998, ,       Movie,   ,        Cat,

        >>> survey = read_spss("data.sav")
        >>> print(survey.get_df())
        shape: (3, 4)
        ┌────────┬──────┬────────────────────┬────────────────┐
        │ gender ┆ yob  ┆ hobby              ┆ animal         │
        │ ---    ┆ ---  ┆ ---                ┆ ---            │
        │ str    ┆ i64  ┆ list[str]          ┆ list[str]      │
        ╞════════╪══════╪════════════════════╪════════════════╡
        │ Male   ┆ 2000 ┆ ["Book", "Sport"]  ┆ ["Cat", "Dog"] │
        │ Female ┆ 1999 ┆ ["Movie", "Sport"] ┆ ["Dog"]        │
        │ Male   ┆ 1998 ┆ ["Movie"]          ┆ ["Cat"]        │
        └────────┴──────┴────────────────────┴────────────────┘

    Notes:
        - SPSS ``.sav`` files are always wide — compact multiselect detection
          is not applicable and not supported.
        - Empty strings are converted to ``None``.
        - Multiselect values are always sorted alphabetically within each row.
        - Columns with no valid responses are excluded by default.
        - ``name_pattern`` separators (``_``, ``.``, ``:``) are defined in
          ``survy.separator.SEPARATORS``.
        - All column parsing behavior is delegated to ``read_polars``.
    """
    if not isinstance(path, Path):
        path = Path(path)

    if path.suffix != ".sav":
        raise FileTypeError("Required .sav file")

    raw_df, _ = pyreadstat.read_sav(
        path,
        apply_value_formats=True,
        formats_as_category=False,
        output_format="polars",
    )

    return read_polars(
        raw_df=raw_df,
        name_pattern=name_pattern,
    )


def to_spss(
    survey: Survey, path: str | Path = "", name: str = "survey", encoding: str = "utf-8"
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
