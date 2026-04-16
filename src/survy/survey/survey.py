from pathlib import Path
from typing import Any, Literal
import warnings
import polars

from survy.variable.variable import Variable, VarType
from survy.utils.spss import ctables


class Survey:
    """
    Container for a collection of survey variables.

    This class provides utilities to access variables, transform survey data
    into tabular format, export to various file formats, and manage metadata.

    Args:
        variables (list[Variable]): List of Variable objects in the survey.
    """

    def __init__(self, variables: list[Variable]):
        self.variables = variables

    def __str__(self) -> str:
        """
        Return a human-readable summary of the survey.

        Returns:
            str: A string listing the number of variables and each variable's
                string representation.

        Examples:
            >>> df = polars.DataFrame(
                {
                    "gender": ["Male", "Female", "Male"],
                    "yob": [2000, 1999, 1998],
                    "hobby": ["Sport;Book", "Sport;Movie", "Movie"],
                    "animal_1": ["Cat", "", "Cat"],
                    "animal_2": ["Dog", "Dog", ""],
                }
            )

            >>> survey = read_polars(df, auto_detect=True)
            >>> survey
            Survey (4 variables)
                Variable(id=gender, base=3, label=gender, value_indices={'Female': 1, 'Male': 2})
                Variable(id=yob, base=3, label=yob, value_indices={})
                Variable(id=hobby, base=3, label=hobby, value_indices={'Book': 1, 'Movie': 2, 'Sport': 3})
                Variable(id=animal, base=3, label=animal, value_indices={'Cat': 1, 'Dog': 2})
        """
        lines = [f"Survey ({len(self.variables)} variables)"]
        for variable in self.variables:
            lines.append(f"    {variable}")
        return "\n".join(lines)

    def __iter__(self):
        """
        Iterate over variables in the survey.

        Yields:
            Variable: Each variable in the survey, in order.

        Notes:
            This allows direct iteration over the survey instance:

            >>> for var in survey:
            ...     print(var.id)

            Equivalent to iterating over ``survey.variables``.
        """
        for var in self.variables:
            yield var

    def __len__(self):
        """
        Return the number of variables in the survey.

        Returns:
            int: Total number of variables.

        Examples:
            >>> len(survey)
            4
        """
        return len(self.variables)

    def __getitem__(self, key: str | int):
        """
        Retrieve a variable by index or ID.

        Args:
            key (str | int):
                - If ``int``: positional index of the variable.
                - If ``str``: ID of the variable.

        Returns:
            Variable: The matching Variable object.

        Raises:
            KeyError: If a string ID is provided and no variable matches.
            IndexError: If an integer index is out of range.

        Examples:
            >>> survey[0]
            Variable(...)

            >>> survey["gender"]
            Variable(id=gender, label=gender, value_indices={'Female': 1, 'Male': 2}, base=3)
        """
        if isinstance(key, int):
            return self.variables[key]

        for var in self.variables:
            if var.id == key:
                return var
        raise KeyError(f"Variable not found: {key}")

    def add(self, variable: Variable | polars.Series):
        """
        Add a Variable to the survey.

        Args:
            variable (Variable | polars.Series): The variable to add. If a
                ``polars.Series`` is given, it is wrapped in a ``Variable``
                automatically.

        Notes:
            If the variable's ID already exists in the survey, a numeric suffix
            is appended (e.g. ``"Q1#1"``, ``"Q1#2"``) until the ID is unique.
        """
        if isinstance(variable, polars.Series):
            variable = Variable(series=variable)

        existing_ids = {var.id for var in self.variables}
        if variable.id in existing_ids:
            base_id = variable.id
            counter = 1
            while f"{base_id}#{counter}" in existing_ids:
                counter += 1
            variable.id = f"{base_id}#{counter}"

        self.variables.append(variable)

    def drop(self, id: str):
        """
        Remove a variable from the survey.

        Args:
            id (str): ID of the variable to remove.

        Returns:
            None

        Raises:
            Nothing: Variables not found are silently ignored.
        """
        self.variables = [var for var in self.variables if var.id != id]

    def sort(self, key=lambda var: var.id, reverse: bool = False):
        """
        Sort variables in-place.

        Args:
            key (callable, optional): A function applied to each variable for
                sorting. Defaults to sorting by variable ID.
            reverse (bool, optional): If ``True``, sort in descending order.
                Defaults to ``False``.

        Returns:
            None
        """
        self.variables = sorted(self.variables, key=key, reverse=reverse)

    def update(self, metadata: list[dict[str, Any]]):
        """Update variable metadata from a list of dictionaries.

        Args:
            metadata (list[dict[str, Any]]): List of metadata dictionaries.
                Each dictionary should include:
                - "id": variable ID
                - "label" (optional): New label for the variable
                - "value_indices" (optional): Mapping of options to indices

        Returns:
            None

        Raises:
            Warning: If a metadata ID does not exist in the survey.

        Notes:
            - Missing optional fields default to empty values.
            - Unknown variable IDs trigger a warning and are skipped.
            - NUMBER variable will not be updated for value_indices

        Examples:

            >>> df = polars.DataFrame(
                {
                    "gender": ["Male", "Female", "Male"],
                    "yob": [2000, 1999, 1998],
                    "hobby": ["Sport;Book", "Sport;Movie", "Movie"],
                    "animal_1": ["Cat", "", "Cat"],
                    "animal_2": ["Dog", "Dog", ""],
                }
            )

            >>> survey = read_polars(df, auto_detect=True)

            >>> survey
            Survey (4 variables)
                Variable(id=gender, label=gender, value_indices={'Female': 1, 'Male': 2}, base=3)
                Variable(id=yob, label=yob, value_indices={}, base=3)
                Variable(id=hobby, label=hobby, value_indices={'Book': 1, 'Movie': 2, 'Sport': 3}, base=3)
                Variable(id=animal, label=animal, value_indices={'Cat': 1, 'Dog': 2}, base=3)

            >>> survey.update(
                [
                    {"id": "gender", "label": "Gender of respondent"},
                    {"id": "hobby", "value_indices": {"Sport": 1, "Book": 2, "Movie": 3}},
                ]
            )
            >>> survey
            Survey (4 variables)
                Variable(id=gender, label=Gender of respondent, value_indices={'Female': 1, 'Male': 2}, base=3)
                Variable(id=yob, label=yob, value_indices={}, base=3)
                Variable(id=hobby, label=hobby, value_indices={'Sport': 1, 'Book': 2, 'Movie': 3}, base=3)
                Variable(id=animal, label=animal, value_indices={'Cat': 1, 'Dog': 2}, base=3)
        """
        for info in metadata:
            var_id = info.get("id")

            if not var_id:
                warnings.warn("Metadata entry missing 'id', skipping.")
                continue

            if var_id not in [q.id for q in self.variables]:
                warnings.warn(f"Id is not in survey: {var_id}")
                continue

            variable = self[var_id]
            label = info.get("label", "")

            if label:
                variable.label = label
            if not variable.series.dtype.is_numeric():
                value_indices = info.get("value_indices", {})
                if value_indices:
                    variable.value_indices = value_indices

    def filter(self, variable_id: str, values: Any | list[Any]) -> "Survey":
        """
        Filter the survey by matching values in a variable's series.

        Args:
            variable_id (str): ID of the variable to filter by.
            values (Any | list[Any]): Value or list of values to keep.

        Returns:
            Survey: A new Survey with only the matching rows.

        Raises:
            KeyError: If the variable ID does not exist.

        Examples:

            >>> df = polars.DataFrame(
                {
                    "gender": ["Male", "Female", "Male"],
                    "yob": [2000, 1999, 1998],
                    "hobby": ["Sport;Book", "Sport;Movie", "Movie"],
                    "animal_1": ["Cat", "", "Cat"],
                    "animal_2": ["Dog", "Dog", ""],
                }
            )

            >>> survey = read_polars(df, auto_detect=True)

            >>> survey.get_df()
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

            >>> survey = survey.filter("hobby", ["Sport", "Book"])

            >>> survey.get_df()
            shape: (2, 4)
            ┌────────┬──────┬────────────────────┬────────────────┐
            │ gender ┆ yob  ┆ hobby              ┆ animal         │
            │ ---    ┆ ---  ┆ ---                ┆ ---            │
            │ str    ┆ i64  ┆ list[str]          ┆ list[str]      │
            ╞════════╪══════╪════════════════════╪════════════════╡
            │ Male   ┆ 2000 ┆ ["Book", "Sport"]  ┆ ["Cat", "Dog"] │
            │ Female ┆ 1999 ┆ ["Movie", "Sport"] ┆ ["Dog"]        │
            └────────┴──────┴────────────────────┴────────────────┘
        """
        if not isinstance(values, list):
            values = [values]

        variable = self[variable_id]
        series = variable.series

        if series.dtype == polars.List:
            mask = series.list.eval(polars.element().is_in(values)).list.any()
        else:
            mask = series.is_in(values)

        indices = mask.arg_true().to_list()

        filtered_variables = [
            Variable(series=var.series[indices]) for var in self.variables
        ]

        return Survey(variables=filtered_variables)

    def get_df(
        self,
        select_dtype: Literal["number", "text"] = "text",
        multiselect_dtype: Literal["number", "text", "compact"] = "compact",
    ) -> polars.DataFrame:
        """
        Convert the survey into a Polars DataFrame.

        Each variable is converted into a column (or columns) and concatenated
        horizontally into a single DataFrame.

        Args:
            select_dtype (Literal["number", "text"], optional):
                Data type for single-select variables. Defaults to "text".
            multiselect_dtype (Literal["number", "text", "compact"], optional):
                Data type for multi-select variables. Defaults to "compact".

        Returns:
            polars.DataFrame: A DataFrame representing the survey responses.

        Notes:
            - Multi-select variables may return multiple columns depending on
              the selected dtype.
            - The final DataFrame is constructed using horizontal concatenation.

        Examples:
            >>> df = polars.DataFrame(
                {
                    "gender": ["Male", "Female", "Male"],
                    "yob": [2000, 1999, 1998],
                    "hobby": ["Sport;Book", "Sport;Movie", "Movie"],
                    "animal_1": ["Cat", "", "Cat"],
                    "animal_2": ["Dog", "Dog", ""],
                }
            )

            >>> survey = read_polars(df, auto_detect=True)

            >>> survey.get_df(select_dtype="text", multiselect_dtype="compact")
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

            >>> survey.get_df(select_dtype="number", multiselect_dtype="compact")
            shape: (3, 4)
            ┌────────┬──────┬────────────────────┬────────────────┐
            │ gender ┆ yob  ┆ hobby              ┆ animal         │
            │ ---    ┆ ---  ┆ ---                ┆ ---            │
            │ i64    ┆ i64  ┆ list[str]          ┆ list[str]      │
            ╞════════╪══════╪════════════════════╪════════════════╡
            │ 2      ┆ 2000 ┆ ["Book", "Sport"]  ┆ ["Cat", "Dog"] │
            │ 1      ┆ 1999 ┆ ["Movie", "Sport"] ┆ ["Dog"]        │
            │ 2      ┆ 1998 ┆ ["Movie"]          ┆ ["Cat"]        │
            └────────┴──────┴────────────────────┴────────────────┘

            >>> survey.get_df(select_dtype="text", multiselect_dtype="text")
            shape: (3, 7)
            ┌────────┬──────┬─────────┬─────────┬─────────┬──────────┬──────────┐
            │ gender ┆ yob  ┆ hobby_1 ┆ hobby_2 ┆ hobby_3 ┆ animal_1 ┆ animal_2 │
            │ ---    ┆ ---  ┆ ---     ┆ ---     ┆ ---     ┆ ---      ┆ ---      │
            │ str    ┆ i64  ┆ str     ┆ str     ┆ str     ┆ str      ┆ str      │
            ╞════════╪══════╪═════════╪═════════╪═════════╪══════════╪══════════╡
            │ Male   ┆ 2000 ┆ Book    ┆ null    ┆ Sport   ┆ Cat      ┆ Dog      │
            │ Female ┆ 1999 ┆ null    ┆ Movie   ┆ Sport   ┆ null     ┆ Dog      │
            │ Male   ┆ 1998 ┆ null    ┆ Movie   ┆ null    ┆ Cat      ┆ null     │
            └────────┴──────┴─────────┴─────────┴─────────┴──────────┴──────────┘

            >>> survey.get_df(select_dtype="text", multiselect_dtype="number")
            shape: (3, 7)
            ┌────────┬──────┬─────────┬─────────┬─────────┬──────────┬──────────┐
            │ gender ┆ yob  ┆ hobby_1 ┆ hobby_2 ┆ hobby_3 ┆ animal_1 ┆ animal_2 │
            │ ---    ┆ ---  ┆ ---     ┆ ---     ┆ ---     ┆ ---      ┆ ---      │
            │ str    ┆ i64  ┆ i8      ┆ i8      ┆ i8      ┆ i8       ┆ i8       │
            ╞════════╪══════╪═════════╪═════════╪═════════╪══════════╪══════════╡
            │ Male   ┆ 2000 ┆ 1       ┆ 0       ┆ 1       ┆ 1        ┆ 1        │
            │ Female ┆ 1999 ┆ 0       ┆ 1       ┆ 1       ┆ 0        ┆ 1        │
            │ Male   ┆ 1998 ┆ 0       ┆ 1       ┆ 0       ┆ 1        ┆ 0        │
            └────────┴──────┴─────────┴─────────┴─────────┴──────────┴──────────┘

            >>> survey.get_df(select_dtype="number", multiselect_dtype="text")
            shape: (3, 7)
            ┌────────┬──────┬─────────┬─────────┬─────────┬──────────┬──────────┐
            │ gender ┆ yob  ┆ hobby_1 ┆ hobby_2 ┆ hobby_3 ┆ animal_1 ┆ animal_2 │
            │ ---    ┆ ---  ┆ ---     ┆ ---     ┆ ---     ┆ ---      ┆ ---      │
            │ i64    ┆ i64  ┆ str     ┆ str     ┆ str     ┆ str      ┆ str      │
            ╞════════╪══════╪═════════╪═════════╪═════════╪══════════╪══════════╡
            │ 2      ┆ 2000 ┆ Book    ┆ null    ┆ Sport   ┆ Cat      ┆ Dog      │
            │ 1      ┆ 1999 ┆ null    ┆ Movie   ┆ Sport   ┆ null     ┆ Dog      │
            │ 2      ┆ 1998 ┆ null    ┆ Movie   ┆ null    ┆ Cat      ┆ null     │
            └────────┴──────┴─────────┴─────────┴─────────┴──────────┴──────────┘

            >>> survey.get_df(select_dtype="number", multiselect_dtype="number")
            shape: (3, 7)
            ┌────────┬──────┬─────────┬─────────┬─────────┬──────────┬──────────┐
            │ gender ┆ yob  ┆ hobby_1 ┆ hobby_2 ┆ hobby_3 ┆ animal_1 ┆ animal_2 │
            │ ---    ┆ ---  ┆ ---     ┆ ---     ┆ ---     ┆ ---      ┆ ---      │
            │ i64    ┆ i64  ┆ i8      ┆ i8      ┆ i8      ┆ i8       ┆ i8       │
            ╞════════╪══════╪═════════╪═════════╪═════════╪══════════╪══════════╡
            │ 2      ┆ 2000 ┆ 1       ┆ 0       ┆ 1       ┆ 1        ┆ 1        │
            │ 1      ┆ 1999 ┆ 0       ┆ 1       ┆ 1       ┆ 0        ┆ 1        │
            │ 2      ┆ 1998 ┆ 0       ┆ 1       ┆ 0       ┆ 1        ┆ 0        │
            └────────┴──────┴─────────┴─────────┴─────────┴──────────┴──────────┘
        """
        dfs = []
        for variable in self.variables:
            if variable.vtype == VarType.MULTISELECT:
                dfs.append(variable.get_df(multiselect_dtype))
            elif variable.vtype == VarType.SELECT:
                dfs.append(variable.get_df(select_dtype))
            else:
                dfs.append(variable.get_df())
        return polars.concat(dfs, how="horizontal")

    @property
    def sps(self) -> str:
        """
        Generate SPSS syntax for the survey.

        Returns:
            str: A string containing SPSS syntax commands for all variables.

        Notes:
            - Each variable contributes its own SPSS syntax.
            - variable IDs are included as comments for readability.

        Examples:
            >>> df = polars.DataFrame(
                {
                    "gender": ["Male", "Female", "Male"],
                    "yob": [2000, 1999, 1998],
                    "hobby": ["Sport;Book", "Sport;Movie", "Movie"],
                    "animal_1": ["Cat", "", "Cat"],
                    "animal_2": ["Dog", "Dog", ""],
                }
            )

            >>> survey = read_polars(df, auto_detect=True)

            >>> survey.sps
            **gender

            VARIABLE LABELS gender 'gender'.
            VALUE LABELS gender 1 'Female'
            2 'Male'.
            VARIABLE LEVEL gender (NOMINAL).
            **yob

            VARIABLE LABELS yob 'yob'.
            VARIABLE LEVEL yob (SCALE).
            **hobby

            VARIABLE LABELS hobby_1 '[Book] hobby'.
            VARIABLE LABELS hobby_2 '[Movie] hobby'.
            VARIABLE LABELS hobby_3 '[Sport] hobby'.
            VALUE LABELS hobby_1 1 'Book'.
            VALUE LABELS hobby_2 1 'Movie'.
            VALUE LABELS hobby_3 1 'Sport'.
            VARIABLE LEVEL hobby_1 (NOMINAL).
            VARIABLE LEVEL hobby_2 (NOMINAL).
            VARIABLE LEVEL hobby_3 (NOMINAL).
            MRSETS /MDGROUP NAME=$hobby
            LABEL='hobby'
            CATEGORYLABELS=COUNTEDVALUES VALUE=1
            VARIABLES=hobby_1 hobby_2 hobby_3
            /DISPLAY NAME=[$hobby].
            **animal

            VARIABLE LABELS animal_1 '[Cat] animal'.
            VARIABLE LABELS animal_2 '[Dog] animal'.
            VALUE LABELS animal_1 1 'Cat'.
            VALUE LABELS animal_2 1 'Dog'.
            VARIABLE LEVEL animal_1 (NOMINAL).
            VARIABLE LEVEL animal_2 (NOMINAL).
            MRSETS /MDGROUP NAME=$animal
            LABEL='animal'
            CATEGORYLABELS=COUNTEDVALUES VALUE=1
            VARIABLES=animal_1 animal_2
            /DISPLAY NAME=[$animal].
            CTABLES
            /TABLE
            gender [C][COUNT F40.0, TOTALS[COUNT F40.0]] +
            yob [MEAN COMMA40.2] +
            $hobby [C][COUNT F40.0, TOTALS[COUNT F40.0]] +
            $animal [C][COUNT F40.0, TOTALS[COUNT F40.0]] +
            BY [Input Tabspec here]
            /SLABELS POSITION=ROW VISIBLE=NO
            /CATEGORIES VARIABLES=ALL
                EMPTY=INCLUDE TOTAL=YES POSITION=BEFORE
            /COMPARETEST TYPE=MEAN ALPHA=0.05 ADJUST=NONE ORIGIN=COLUMN INCLUDEMRSETS=YES
                CATEGORIES=ALLVISIBLE MEANSVARIANCE=TESTEDCATS MERGE=YES STYLE=SIMPLE SHOWSIG=NO
            /COMPARETEST TYPE=PROP ALPHA=0.05 ADJUST=NONE ORIGIN=COLUMN INCLUDEMRSETS=YES
                CATEGORIES=ALLVISIBLE MEANSVARIANCE=TESTEDCATS MERGE=YES STYLE=SIMPLE SHOWSIG=NO.
        """
        commands = []

        for variable in self.variables:
            commands.append(f"**{variable.id}\n")
            commands.append(variable.sps)

        commands.append(
            ctables({variable.id: variable.vtype for variable in self.variables})
        )

        return "\n".join(commands)

    def to_json(
        self, path: str | Path, name: str = "survey", encoding: str = "utf-8"
    ) -> None:
        """Export the survey to a JSON file.

        This is a thin wrapper around ``survy.io.json.to_json``.

        Args:
            path (str | pathlib.Path): Output directory.
            name (str, optional): Output file name. Defaults to "survey".
            encoding (str, optional): File encoding. Defaults to "utf-8".

        Returns:
            None

        Examples:

            >>> df = polars.DataFrame(
                {
                    "gender": ["Male", "Female", "Male"],
                    "yob": [2000, 1999, 1998],
                    "hobby": ["Sport;Book", "Sport;Movie", "Movie"],
                    "animal_1": ["Cat", "", "Cat"],
                    "animal_2": ["Dog", "Dog", ""],
                }
            )

            >>> survey = read_polars(df, auto_detect=True)

            >>> survey.get_df()
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

            >>> survey.to_json("/data", name="survey")

            >>> with open("data/survey.json", "r") as f:
                data = json.load(f)

            >>> data
            {
                "variables": [
                    {
                        "id": "gender",
                        "data": ["Male", "Female", "Male"],
                        "label": "",
                        "value_indices": {"Female": 1, "Male": 2},
                    },
                    {"id": "yob", "data": [2000, 1999, 1998], "label": "", "value_indices": {}},
                    {
                        "id": "hobby",
                        "data": [["Book", "Sport"], ["Movie", "Sport"], ["Movie"]],
                        "label": "",
                        "value_indices": {"Book": 1, "Movie": 2, "Sport": 3},
                    },
                    {
                        "id": "animal",
                        "data": [["Cat", "Dog"], ["Dog"], ["Cat"]],
                        "label": "",
                        "value_indices": {"Cat": 1, "Dog": 2},
                    },
                ]
            }
        """
        from survy.io.json import to_json

        to_json(self, path, name, encoding)

    def to_spss(self, path: str | Path, name: str = "survey", encoding: str = "utf-8"):
        """Export the survey to SPSS files.

        This is a wrapper around ``survy.io.csv.to_csv`` and writes:
        - A `.sav` data file
        - A `.sps` syntax file.

        Args:
            path (str | pathlib.Path): Output directory.
            name (str, optional): Base name for output files. Defaults to "survey".
            encoding (str, optional): Encoding for syntax file. Defaults to "utf-8".

        Returns:
            None

        Examples:
            >>> survey.to_spss("output/")
            >>> survey.to_spss("output/", name="my_survey")
        """
        from survy.io.spss import to_spss

        to_spss(self, path, name, encoding)

    def to_csv(
        self,
        path: str | Path,
        name: str = "survey",
        compact: bool = False,
        compact_separator: str = ";",
    ):
        """Export the survey to CSV files.

        This is a wrapper around ``survy.io.csv.to_csv`` and writes:
        - Survey data
        - Variable metadata
        - Option mappings

        Args:
            path (str | pathlib.Path): Output directory.
            name (str, optional): Base name for output files. Defaults to "survey".
            compact (bool, optional): Whether to compact multi-select responses.
                Defaults to False.
            compact_separator (str, optional): Separator for compacted values.
                Defaults to ";".

        Returns:
            None

        Examples:

            >>> df = polars.DataFrame(
                {
                    "gender": ["Male", "Female", "Male"],
                    "yob": [2000, 1999, 1998],
                    "hobby": ["Sport;Book", "Sport;Movie", "Movie"],
                    "animal_1": ["Cat", "", "Cat"],
                    "animal_2": ["Dog", "Dog", ""],
                }
            )

            >>> survey = read_polars(df, auto_detect=True)

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
            >>> survey.to_csv(path=".", name="survey", compact=True)

            Output: `survey_data.csv`
            ┌────────┬──────┬────────────────────┬────────────────┐
            │ gender ┆ yob  ┆ hobby              ┆ animal         │
            ╞════════╪══════╪════════════════════╪════════════════╡
            │ Male   ┆ 2000 ┆ Book;Sport         ┆ Cat;Dog        │
            │ Female ┆ 1999 ┆ Movie;Sport        ┆ Dog            │
            │ Male   ┆ 1998 ┆ Movie              ┆ Cat            │
            └────────┴──────┴────────────────────┴────────────────┘

            Export in non-compact mode:
            >>> survey.to_csv(path=".", name="survey", compact=False)

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
        """
        from survy.io.csv import to_csv

        to_csv(self, path, name, compact, compact_separator)

    def to_excel(
        self,
        path: str | Path,
        name: str = "survey",
        compact: bool = False,
        compact_separator: str = ";",
    ):
        """Export the survey to Excel files.

        This is a wrapper around ``survy.io.excel.to_excel`` and writes:
        - Survey data
        - Variable metadata
        - Option mappings

        Args:
            path (str | pathlib.Path): Output directory.
            name (str, optional): Base name for output files. Defaults to "survey".
            compact (bool, optional): Whether to compact multi-select responses.
                Defaults to False.
            compact_separator (str, optional): Separator for compacted values.
                Defaults to ";".

        Returns:
            None

        Examples:

            >>> df = polars.DataFrame(
                {
                    "gender": ["Male", "Female", "Male"],
                    "yob": [2000, 1999, 1998],
                    "hobby": ["Sport;Book", "Sport;Movie", "Movie"],
                    "animal_1": ["Cat", "", "Cat"],
                    "animal_2": ["Dog", "Dog", ""],
                }
            )

            >>> survey = read_polars(df, auto_detect=True)

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
            >>> survey.to_excel(path=".", name="survey", compact=True)

            Output: `survey_data.xlsx`
            ┌────────┬──────┬────────────────────┬────────────────┐
            │ gender ┆ yob  ┆ hobby              ┆ animal         │
            ╞════════╪══════╪════════════════════╪════════════════╡
            │ Male   ┆ 2000 ┆ Book;Sport         ┆ Cat;Dog        │
            │ Female ┆ 1999 ┆ Movie;Sport        ┆ Dog            │
            │ Male   ┆ 1998 ┆ Movie              ┆ Cat            │
            └────────┴──────┴────────────────────┴────────────────┘

            Export in non-compact mode:
            >>> survey.to_excel(path=".", name="survey", compact=False)

            Output: `survey_data.xlsx`
            ┌────────┬──────┬─────────┬─────────┬─────────┬──────────┬──────────┐
            │ gender ┆ yob  ┆ hobby_1 ┆ hobby_2 ┆ hobby_3 ┆ animal_1 ┆ animal_2 │
            ╞════════╪══════╪═════════╪═════════╪═════════╪══════════╪══════════╡
            │ Male   ┆ 2000 ┆ Book    ┆ null    ┆ Sport   ┆ Cat      ┆ Dog      │
            │ Female ┆ 1999 ┆ null    ┆ Movie   ┆ Sport   ┆ null     ┆ Dog      │
            │ Male   ┆ 1998 ┆ null    ┆ Movie   ┆ null    ┆ Cat      ┆ null     │
            └────────┴──────┴─────────┴─────────┴─────────┴──────────┴──────────┘

            Variables metadata (`survey_variables_info.xlsx`):
                gender,SINGLE,gender
                yob,NUMBER,yob
                hobby,MULTISELECT,hobby
                animal,MULTISELECT,animal


            Values mapping (`survey_values_info.xlsx`):
                gender,Male,1
                gender,Female,2
                hobby,Book,1
                hobby,Movie,2
                hobby,Sport,3
                animal,Cat,1
                animal,Dog,2
        """
        from survy.io.excel import to_excel

        to_excel(self, path, name, compact, compact_separator)
