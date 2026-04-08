from pathlib import Path
import polars

from survy.errors import FileTypeError
from survy.io.polars import read_polars
from survy.variable._utils import VarType
from survy.survey.survey import Survey


def read_excel(
    path: str | Path,
    compact_ids: list[str] | None = None,
    compact_separator: str = ";",
    auto_detect: bool = False,
    name_pattern: str = "id(_multi)?",
) -> Survey:
    """
    Read a Excel file and convert it into a Survey object.

    This is a convenience wrapper around `read_polars`, allowing users to
    directly load survey data from a Excel file.

    Args:
        path (str | Path):
            Path to the `.xlsx` file.

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
            If the input file is not a `.xlsx`.

    Examples:

        Input Excel (`survey.xlsx`):
            ┌────────┬──────┬──────┬─────┐
            │ gender ┆ Q1_1 ┆ Q1_2 ┆ Q2  │
            ╞════════╪══════╪══════╪═════╡
            │ M      ┆ A    ┆ B    ┆ X;Y │
            │ F      ┆      ┆ B    ┆ X   │
            │ F      ┆ A    ┆      ┆ Y;Z │
            └────────┴──────┴──────┴─────┘

        Usage:

            survey = read_excel(
                "survey.xlsx",
                compact_ids=["hobby"]
            )


        Parsed result:

            gender →
                ["M", "F", "F"]

            Q1 →
                [
                    ["A", "B"],
                    ["B"],
                    ["A"]
                ]

            Q2 →
                [
                    ["X", "Y"],
                    ["X"],
                    ["Y", "Z"]
                ]

    Notes:
        - Empty strings in Excel are treated as null values
        - Multi-select columns can be:
            • spread across multiple columns (Q1_1, Q1_2)
            • stored as compact strings ("A;B")
        - Column parsing behavior follows `read_polars`
    """
    if not isinstance(path, Path):
        path = Path(path)

    if path.suffix != ".xlsx":
        raise FileTypeError("Required .xlsx file")

    compact_ids = compact_ids or []

    return read_polars(
        raw_df=polars.read_excel(path),
        compact_ids=compact_ids,
        compact_separator=compact_separator,
        auto_detect=auto_detect,
        name_pattern=name_pattern,
    )


def to_excel(
    survey: Survey,
    path: str | Path = "",
    name: str = "survey",
    compact: bool = True,
    compact_separator: str = ";",
):
    """
    Export a Survey object to Excel files.

    This function writes three Excel files:

    - `{name}_data.xlsx`:
        Survey responses (main dataset)

    - `{name}_variables_info.xlsx`:
        Variable metadata (id, type, label)

    - `{name}_values_info.xlsx`:
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

        Given Survey data:

            gender →
                ["M", "F", "F"]

            hobby →
                [
                    ["A", "B"],
                    ["B"],
                    []
                ]


        Export in compact mode:

            to_excel(survey, path=".", name="survey", compact=True)


        Output: `survey_data.xlsx`
            ┌────────┬───────┐
            │ gender ┆ hobby │
            ╞════════╪═══════╡
            │ M      ┆ A;B   │
            │ F      ┆ B     │
            │ F      ┆       │
            └────────┴───────┘

        Export in non-compact mode:

            to_excel(survey, compact=False)


        Output: `survey_data.excel`

            ┌────────┬─────────┬─────────┐
            │ gender ┆ hobby_1 ┆ hobby_2 │
            ╞════════╪═════════╪═════════╡
            │ M      ┆ A       ┆ B       │
            │ F      ┆         ┆ B       │
            │ F      ┆         ┆         │
            └────────┴─────────┴─────────┘

        Variables metadata (`survey_variables_info.xlsx`):

            gender,SINGLE,gender
            hobby,MULTISELECT,hobby


        Values mapping (`survey_values_info.xlsx`):

            hobby,A,1
            hobby,B,2


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
        ).select([variable.id for variable in survey.variables]).write_excel(
            path / f"{name}_data.xlsx"
        )
    else:
        survey.get_df(select_dtype="text", multiselect_dtype="text").write_excel(
            path / f"{name}_data.xlsx"
        )

    polars.DataFrame(
        [
            {"id": variable.id, "vtype": variable.vtype, "label": variable.label}
            for variable in survey.variables
        ]
    ).write_excel(path / f"{name}_variables_info.xlsx")

    polars.DataFrame(
        [
            {"id": variable.id, "text": op, "index": index}
            for variable in survey.variables
            for op, index in variable.value_indices.items()
        ]
    ).write_excel(path / f"{name}_options_info.xlsx")
