import json
from pathlib import Path

import polars

from survy.survey.question import Question
from survy.survey.survey import Survey


def read_json(path: str | Path) -> Survey:
    """Load a survey from a JSON file.

    The JSON file must contain a top-level "questions" key. Each item is
    used to construct a ``Question`` object and populate a ``Survey``.

    Args:
        path (str | pathlib.Path): Path to the JSON file.

    Returns:
        Survey: A Survey instance containing the loaded questions.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        KeyError: If required keys (e.g., "questions") are missing.
    """
    with open(path, "r") as f:
        data = json.load(f)

    questions = []

    for d in data["questions"]:
        question = Question(series=polars.Series(d["id"], d["data"]))
        question.label = d["label"]
        question.option_indices = d["option_indices"]
        question.loop_id = d["loop_id"]
        questions.append(question)

    return Survey(questions=questions)


def to_json(
    survey: Survey, path: str | Path, name: str = "survey", encoding: str = "utf-8"
) -> None:
    """Serialize a Survey object to a JSON file.

    Each question in the survey is converted to a dictionary using its
    ``to_dict()`` method before being written to disk.

    Args:
        survey (Survey): The Survey instance to serialize.
        path (str | pathlib.Path): Directory where the file will be saved.
        name (str, optional): Output file name. Defaults to "survey".
        encoding (str, optional): File encoding. Defaults to "utf-8".

    Returns:
        None

    Raises:
        OSError: If the file cannot be written.
    """
    if not isinstance(path, Path):
        path = Path(path)

    data = {
        "questions": [question.to_dict() for question in survey.questions],
    }

    with open(path / name, "w", encoding=encoding) as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
