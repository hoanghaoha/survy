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
    Read a CSV file and convert it into a Survey object.

    This is a convenience wrapper around `read_polars`, allowing users to
    directly load survey data from a CSV file.

    Args:
        path (str | Path):
            Path to the `.csv` file.

        compact_ids (list[str] | None):
            Variable IDs that should be interpreted as compact multi-select
            (e.g. "A;B;C").

        compact_separator (str, default=";"):
            Delimiter used for compact multi-select values.

        auto_detect (bool, default=False):
            If True, automatically detect compact multi-select columns based
            on the presence of the separator in values.

        name_pattern (str, default="id(_multi)?"):
            Pattern used to parse column names into:
            - base variable id
            - optional multi suffix

    Returns:
        Survey:
            Parsed survey object.

    Raises:
        FileTypeError:
            If the input file is not a `.csv`.


    Examples:
        Input CSV (`survey.csv`):
        ┌────────┬──────┬─────────────┬──────────┬──────────┐
        │ gender ┆ yob  ┆ hobby       ┆ animal_1 ┆ animal_2 │
        ╞════════╪══════╪═════════════╪══════════╪══════════╡
        │ Male   ┆ 2000 ┆ Sport;Book  ┆ Cat      ┆ Dog      │
        │ Female ┆ 1999 ┆ Sport;Movie ┆          ┆ Dog      │
        │ Male   ┆ 1998 ┆ Movie       ┆ Cat      ┆          │
        └────────┴──────┴─────────────┴──────────┴──────────┘

        >>> survey = read_csv(
                "survey.csv",
                compact_ids=["hobby"]
            )

        >>> print(survey)
        Survey (4 variables)
            Variable(id=gender, label=gender, value_indices={'Female': 1, 'Male': 2}, base=3)
            Variable(id=yob, label=yob, value_indices={}, base=3)
            Variable(id=hobby, label=hobby, value_indices={'Movie': 1, 'Sport;Book': 2, 'Sport;Movie': 3}, base=3)
            Variable(id=animal, label=animal, value_indices={'Cat': 1, 'Dog': 2}, base=3)

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
        - Empty strings in CSV are treated as null values
        - Multi-select columns can be:
            • spread across multiple columns (Q1_1, Q1_2)
            • stored as compact strings ("A;B")
        - Column parsing behavior follows `read_polars`
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
        │ Male   ┆ 2000 ┆ Book,Sport         ┆ Cat,Dog        │
        │ Female ┆ 1999 ┆ Movie,Sport        ┆ Dog            │
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
