from pathlib import Path
from typing import Any, Literal
import warnings
import polars

from survy.variable.variable import Variable, VarType
from survy.utils.spss import ctables


class Survey:
    """Container for a collection of survey variables.

    This class provides utilities to access variables, transform survey data
    into tabular format, export to various file formats, and manage metadata.

    Args:
        variables (list[Variable]): List of Variable objects in the survey.

    Examples:
        >>> survey = Survey(variables=[q1, q2])
        >>> df = survey.get_df()
        >>> print(df.shape)
    """

    def __init__(self, variables: list[Variable]):
        self.variables = variables

    def __getitem__(self, variable_id: str):
        """Retrieve a Variable by its ID.

        Args:
            variable_id (str): The ID of the variable to retrieve.

        Returns:
            Variable: The matching Variable object.

        Raises:
            KeyError: If the variable ID does not exist.

        Examples:
            >>> variable = survey["Q1"]
            >>> print(variable.label)
        """
        return {variable.id: variable for variable in self.variables}[variable_id]

    def get_df(
        self,
        select_dtype: Literal["number", "text"] = "text",
        multiselect_dtype: Literal["number", "text", "compact"] = "compact",
    ) -> polars.DataFrame:
        """Convert the survey into a Polars DataFrame.

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
            >>> df = survey.get_df()
            >>> df = survey.get_df(select_dtype="number")
            >>> df = survey.get_df(multiselect_dtype="compact")
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
        """Generate SPSS syntax for the survey.

        Returns:
            str: A string containing SPSS syntax commands for all variables.

        Notes:
            - Each variable contributes its own SPSS syntax.
            - variable IDs are included as comments for readability.

        Examples:
            >>> syntax = survey.sps
            >>> print(syntax[:100])
        """
        commands = []

        for variable in self.variables:
            commands.append(f"**{variable.id}\n")
            commands.append(variable.sps)

        commands.append(
            ctables({variable.id: variable.vtype for variable in self.variables})
        )

        return "\n".join(commands)

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
            >>> metadata = [
            ...     {"id": "Q1", "label": "Updated label"},
            ...     {"id": "Q2", "value_indices": {"Yes": 1, "No": 0}},
            ... ]
            >>> survey.update(metadata)
        """
        for info in metadata:
            id = info["id"]

            if id not in [q.id for q in self.variables]:
                warnings.warn(f"Id is not in survey: {id}")
                continue

            variable = self[info["id"]]
            variable.label = info.get("label", "")
            if not variable.series.dtype.is_numeric():
                variable.value_indices = info.get("value_indices", {})

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
            >>> survey.to_json("output/")
            >>> survey.to_json("output/", name="my_survey")
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
            >>> survey.to_csv("output/")
            >>> survey.to_csv("output/", compact=True)
            >>> survey.to_csv("output/", name="study1", compact_separator="|")
        """
        from survy.io.csv import to_csv

        to_csv(self, path, name, compact, compact_separator)
