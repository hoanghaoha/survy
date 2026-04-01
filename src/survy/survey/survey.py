from pathlib import Path
from typing import Any, Literal
import warnings
import polars

from survy.survey.question import Question, QuestionType
from survy.utils.spss import ctables


class Survey:
    """Container for a collection of survey questions.

    This class provides utilities to access questions, transform survey data
    into tabular format, export to various file formats, and manage metadata.

    Args:
        questions (list[Question]): List of Question objects in the survey.

    Examples:
        >>> survey = Survey(questions=[q1, q2])
        >>> df = survey.get_df()
        >>> print(df.shape)
    """

    def __init__(self, questions: list[Question]):
        self.questions = questions

    def __getitem__(self, question_id: str):
        """Retrieve a question by its ID.

        Args:
            question_id (str): The ID of the question to retrieve.

        Returns:
            Question: The matching Question object.

        Raises:
            KeyError: If the question ID does not exist.

        Examples:
            >>> question = survey["Q1"]
            >>> print(question.label)
        """
        return {question.id: question for question in self.questions}[question_id]

    def get_df(
        self,
        select_dtype: Literal["number", "text"] = "text",
        multiselect_dtype: Literal["number", "text", "compact"] = "compact",
    ) -> polars.DataFrame:
        """Convert the survey into a Polars DataFrame.

        Each question is converted into a column (or columns) and concatenated
        horizontally into a single DataFrame.

        Args:
            select_dtype (Literal["number", "text"], optional):
                Data type for single-select questions. Defaults to "text".
            multiselect_dtype (Literal["number", "text", "compact"], optional):
                Data type for multi-select questions. Defaults to "compact".

        Returns:
            polars.DataFrame: A DataFrame representing the survey responses.

        Notes:
            - Multi-select questions may return multiple columns depending on
              the selected dtype.
            - The final DataFrame is constructed using horizontal concatenation.

        Examples:
            >>> df = survey.get_df()
            >>> df = survey.get_df(select_dtype="number")
            >>> df = survey.get_df(multiselect_dtype="compact")
        """
        dfs = []
        for question in self.questions:
            if question.qtype == QuestionType.MULTISELECT:
                dfs.append(question.get_df(multiselect_dtype))
            elif question.qtype == QuestionType.SELECT:
                dfs.append(question.get_df(select_dtype))
            else:
                dfs.append(question.get_df())
        return polars.concat(dfs, how="horizontal")

    @property
    def sps(self) -> str:
        """Generate SPSS syntax for the survey.

        Returns:
            str: A string containing SPSS syntax commands for all questions.

        Notes:
            - Each question contributes its own SPSS syntax.
            - Question IDs are included as comments for readability.

        Examples:
            >>> syntax = survey.sps
            >>> print(syntax[:100])
        """
        commands = []

        for question in self.questions:
            commands.append(f"**{question.id}\n")
            commands.append(question.sps)

        commands.append(
            ctables({question.id: question.qtype for question in self.questions})
        )

        return "\n".join(commands)

    def update(self, metadata: list[dict[str, Any]]):
        """Update question metadata from a list of dictionaries.

        Args:
            metadata (list[dict[str, Any]]): List of metadata dictionaries.
                Each dictionary should include:
                - "id": Question ID
                - "label" (optional): New label for the question
                - "option_indices" (optional): Mapping of options to indices

        Returns:
            None

        Raises:
            Warning: If a metadata ID does not exist in the survey.

        Notes:
            - Missing optional fields default to empty values.
            - Unknown question IDs trigger a warning and are skipped.

        Examples:
            >>> metadata = [
            ...     {"id": "Q1", "label": "Updated label"},
            ...     {"id": "Q2", "option_indices": {"Yes": 1, "No": 0}},
            ... ]
            >>> survey.update(metadata)
        """
        for info in metadata:
            id = info["id"]

            if id not in [q.id for q in self.questions]:
                warnings.warn(f"Id is not in survey: {id}")
                continue

            question = self[info["id"]]
            question.label = info.get("label", "")
            question.option_indices = info.get("option_indices", {})

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
        - Question metadata
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
