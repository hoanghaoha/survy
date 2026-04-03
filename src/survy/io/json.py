import json
from pathlib import Path

import polars

from survy.variable.variable import Variable
from survy.survey.survey import Survey


def read_json(path: str | Path) -> Survey:
    """Load a survey from a JSON file.

    The JSON file must contain a top-level "variables" key. Each item is
    used to construct a ``Variable`` object and populate a ``Survey``.

    Args:
        path (str | pathlib.Path): Path to the JSON file.

    Returns:
        Survey: A Survey instance containing the loaded variables.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        KeyError: If required keys (e.g., "variables") are missing.
    """
    with open(path, "r") as f:
        data = json.load(f)

    variables = []

    for d in data["variables"]:
        variable = Variable(series=polars.Series(d["id"], d["data"]))
        variable.label = d["label"]
        if d["value_indices"]:
            variable.value_indices = d["value_indices"]
        variables.append(variable)

    return Survey(variables=variables)


def to_json(
    survey: Survey, path: str | Path, name: str = "survey", encoding: str = "utf-8"
) -> None:
    """Serialize a Survey object to a JSON file.

    Each variable in the survey is converted to a dictionary using its
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
        "variables": [variable.to_dict() for variable in survey.variables],
    }

    with open(path / name, "w", encoding=encoding) as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
