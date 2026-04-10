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
    """Read a CSV file and convert it into a Survey object.

    This is a convenience wrapper around ``read_polars``, allowing users to
    directly load survey data from a CSV file. It detects and merges
    multiselect variables from two possible raw formats:

    **Wide format** — each answer option occupies its own column with a
    shared prefix and a separator-delimited suffix
    (e.g. ``hobby_1``, ``hobby_2``). These are detected automatically
    via ``name_pattern``.

    **Compact format** — all selected answers are stored in a single cell
    joined by a delimiter (e.g. ``"Sport;Book"``). These must be declared
    explicitly via ``compact_ids`` or discovered via ``auto_detect``.

    After reading, both formats produce the same internal representation:
    a ``MULTISELECT`` variable whose data is a sorted list of chosen values
    per respondent.

    Args:
        path (str | Path):
            Path to the ``.csv`` file.

        compact_ids (list[str] | None):
            Column IDs to treat as compact multiselect. Each listed column's
            cell values are split on ``compact_separator`` to recover
            individual choices. Do not combine with ``auto_detect=True``.

        compact_separator (str):
            Delimiter used inside compact multiselect cells.
            Also used by ``auto_detect`` to scan for compact columns.

        auto_detect (bool):
            If ``True``, every column is scanned for the presence of
            ``compact_separator`` in its values. Any column containing the
            separator in at least one cell is treated as compact multiselect.
            Do not combine with ``compact_ids``.

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
            Parsed survey object with variables inferred from the CSV data.

    Raises:
        FileTypeError:
            If the input file does not have a ``.csv`` extension.

    Examples:
        **Wide format** — detected automatically, no special parameters:

        Input CSV (``data_wide.csv``):

        >>> # gender, yob, hobby_1, hobby_2, hobby_3, animal_1, animal_2
        >>> # Male,   2000, Book,   ,        Sport,   Cat,      Dog
        >>> # Female, 1999, ,       Movie,   ,        ,         Dog
        >>> # Male,   1998, ,       Movie,   ,        Cat,

        >>> survey = read_csv("data_wide.csv")

        **Compact format** — specify compact columns explicitly:

        Input CSV (``data_compact.csv``):

        >>> # gender, yob,  hobby,       animal_1, animal_2
        >>> # Male,   2000, Sport;Book,  Cat,      Dog
        >>> # Female, 1999, Sport;Movie, ,         Dog
        >>> # Male,   1998, Movie,       Cat,

        >>> survey = read_csv(
        ...     "data_compact.csv",
        ...     compact_ids=["hobby"],
        ...     compact_separator=";",
        ... )

        **Auto-detect** compact columns by scanning for the separator:

        >>> survey = read_csv(
        ...     "data_compact.csv",
        ...     auto_detect=True,
        ...     compact_separator=";",
        ... )

        All approaches produce the same result:

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
        - Empty strings (``""``) in the CSV are converted to ``None``.
        - Multiselect values are always sorted alphabetically within each row.
        - Columns with no valid responses are excluded by default.
        - Do not combine ``auto_detect=True`` with ``compact_ids`` in the
          same call — use one approach or the other.
        - ``name_pattern`` separators (``_``, ``.``, ``:``) are defined in
          ``survy.separator.SEPARATORS``.
        - All column parsing behavior is delegated to ``read_polars``.
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
    Export a Survey object to CSV files.

    This function writes three CSV files:

    - `{name}_data.csv`:
        Survey responses (main dataset)

    - `{name}_variables_info.csv`:
        Variable metadata (id, type, label)

    - `{name}_values_info.csv`:
        Mapping of values text to numeric indices

    Args:
        survey (Survey):
            The Survey instance to export.

        path (str | Path, default=""):
            Output directory.

        name (str, default="survey"):
            Base filename for exported files.

        compact (bool, default=True):
            Controls how multi-select variables are exported:

            - True → compact format (e.g. "A;B")
            - False → expanded format (one column per option)

        compact_separator (str, default=";"):
            Separator used when joining multi-select values.

    Returns:
        None

    Raises:
        OSError:
            If files cannot be written.

    Examples:
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

        Export in compact mode:
        >>> to_csv(survey, path=".", name="survey", compact=True)

        Output: `survey_data.csv`
        ┌────────┬──────┬────────────────────┬────────────────┐
        │ gender ┆ yob  ┆ hobby              ┆ animal         │
        ╞════════╪══════╪════════════════════╪════════════════╡
        │ Male   ┆ 2000 ┆ Book;Sport         ┆ Cat;Dog        │
        │ Female ┆ 1999 ┆ Movie;Sport        ┆ Dog            │
        │ Male   ┆ 1998 ┆ Movie              ┆ Cat            │
        └────────┴──────┴────────────────────┴────────────────┘

        Export in non-compact mode:
        >>> to_csv(survey, compact=False)

        Output: `survey_data.csv`
        ┌────────┬──────┬─────────┬─────────┬─────────┬──────────┬──────────┐
        │ gender ┆ yob  ┆ hobby_1 ┆ hobby_2 ┆ hobby_3 ┆ animal_1 ┆ animal_2 │
        ╞════════╪══════╪═════════╪═════════╪═════════╪══════════╪══════════╡
        │ Male   ┆ 2000 ┆ Book    ┆ null    ┆ Sport   ┆ Cat      ┆ Dog      │
        │ Female ┆ 1999 ┆ null    ┆ Movie   ┆ Sport   ┆ null     ┆ Dog      │
        │ Male   ┆ 1998 ┆ null    ┆ Movie   ┆ null    ┆ Cat      ┆ null     │
        └────────┴──────┴─────────┴─────────┴─────────┴──────────┴──────────┘

        Variables metadata (`survey_variables_info.csv`):
            gender,SINGLE,gender
            yob,NUMBER,yob
            hobby,MULTISELECT,hobby
            animal,MULTISELECT,animal


        Values mapping (`survey_values_info.csv`):
            gender,Male,1
            gender,Female,2
            hobby,Book,1
            hobby,Movie,2
            hobby,Sport,3
            animal,Cat,1
            animal,Dog,2

    Notes:
        - Compact mode is recommended for storage and interoperability
        - Non-compact mode is useful for modeling (e.g. ML features)
        - Output column order follows the Survey variable order
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
    ).write_csv(path / f"{name}_values_info.csv")
