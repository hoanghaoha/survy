import json
from pathlib import Path

import polars

from survy.variable.variable import Variable
from survy.survey.survey import Survey


def read_json(path: str | Path) -> Survey:
    """Load a :class:`Survey` from a JSON file.

    The JSON file must contain a top-level ``"variables"`` key mapping to a
    list of variable definitions. Each variable entry is used to construct
    a :class:`Variable` instance and populate a :class:`Survey`.

    Expected JSON structure::

        {
            "variables": [
                {
                    "id": "age",
                    "data": [25, 30, 22],
                    "label": "Age of respondent",
                    "value_indices": null
                },
                {
                    "id": "gender",
                    "data": [1, 2, 1],
                    "label": "Gender",
                    "value_indices": {"1": "Male", "2": "Female"}
                }
            ]
        }

    Args:
        path (str | pathlib.Path):
            Path to the JSON file to read.

    Returns:
        Survey:
            A Survey instance populated with Variable objects created from
            the JSON content.

    Raises:
        FileNotFoundError:
            If the file does not exist.
        json.JSONDecodeError:
            If the file contains invalid JSON.
        KeyError:
            If required keys such as ``"variables"``, ``"id"``, ``"data"``,
            or ``"label"`` are missing.
        TypeError:
            If any variable entry has an unexpected type.

    Notes:
        - Each variable's ``data`` is converted into a ``polars.Series`` using
          its ``id`` as the series name.
        - ``value_indices`` is only assigned if it is truthy (e.g., not None or empty).

    Example:
        >>> survey = read_json("survey.json")
        >>> len(survey.variables)
        2
        >>> survey.variables[0].label
        'Age of respondent'
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
    survey: Survey, path: str | Path = "", name: str = "survey", encoding: str = "utf-8"
) -> None:
    """Serialize a :class:`Survey` object to a JSON file.

    Each variable in the survey is converted to a dictionary via its
    ``to_dict()`` method and written under a top-level ``"variables"`` key.

    The output file will be created at ``path / f"{name}.json"``.

    Args:
        survey (Survey):
            The Survey instance to serialize.
        path (str | pathlib.Path, optional):
            Directory where the JSON file will be saved. Defaults to the
            current working directory.
        name (str, optional):
            Output file name without extension. Defaults to ``"survey"``.
        encoding (str, optional):
            File encoding used when writing the file. Defaults to ``"utf-8"``.

    Returns:
        None

    Raises:
        OSError:
            If the file cannot be written (e.g., invalid path or permissions).
        AttributeError:
            If any variable does not implement ``to_dict()``.

    Notes:
        - The output JSON is pretty-printed with indentation (4 spaces).
        - Non-ASCII characters are preserved (``ensure_ascii=False``).

    Example:
        >>> from pathlib import Path
        >>> survey = Survey(variables=[
        ...     Variable(series=polars.Series("age", [25, 30]))
        ... ])
        >>> survey.variables[0].label = "Age"
        >>> to_json(survey, path=Path("./data"), name="my_survey")

        This creates a file ``./data/my_survey.json`` with content like::

            {
                "variables": [
                    {
                        "id": "age",
                        "data": [25, 30],
                        "label": "Age",
                        "value_indices": null
                    }
                ]
            }
    """
    if not isinstance(path, Path):
        path = Path(path)

    data = {
        "variables": [variable.to_dict() for variable in survey.variables],
    }

    with open(path / f"{name}.json", "w", encoding=encoding) as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
