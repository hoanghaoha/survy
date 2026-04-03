import json
from pathlib import Path

import polars as pl
import pytest

from survy.io.json import read_json, to_json
from survy.variable.variable import Variable
from survy.survey.survey import Survey


def make_sample_json(path: Path):
    data = {
        "variables": [
            {
                "id": "Q1",
                "data": ["A", "B", "C", "A"],
                "label": "Variable 1",
                "value_indices": {"A": 1, "B": 2, "C": 3},
            },
            {
                "id": "Q2",
                "data": [4, 5, 6],
                "label": "Variable 2",
                "value_indices": {},
            },
            {
                "id": "Q3",
                "data": [["X", "Y", "Z"], ["X", "Z"], ["X"], ["Y", "Z"]],
                "label": "Variable 1",
                "value_indices": {"X": 1, "Y": 2, "Z": 3},
            },
        ]
    }
    file_path = path / "survey.json"
    with open(file_path, "w") as f:
        json.dump(data, f)
    return file_path, data


def test_read_json_success(tmp_path: Path):
    file_path, data = make_sample_json(tmp_path)

    survey = read_json(file_path)

    assert isinstance(survey, Survey)
    assert len(survey.variables) == 3

    for index, id in enumerate(["Q1", "Q2", "Q3"]):
        q = survey[id]
        assert isinstance(q, Variable)
        assert isinstance(q.label, str)
        assert q.value_indices == data["variables"][index]["value_indices"]
        assert q.series.to_list() == data["variables"][index]["data"]


def test_read_json_missing_file():
    with pytest.raises(FileNotFoundError):
        read_json("non_existent_file.json")


def test_read_json_invalid_json(tmp_path: Path):
    file_path = tmp_path / "bad.json"
    file_path.write_text("invalid json")

    with pytest.raises(json.JSONDecodeError):
        read_json(file_path)


def test_read_json_missing_variables_key(tmp_path: Path):
    file_path = tmp_path / "bad.json"
    file_path.write_text(json.dumps({"wrong_key": []}))

    with pytest.raises(KeyError):
        read_json(file_path)


def make_sample_survey():
    q1 = Variable(series=pl.Series("Q1", ["A", "B", "A"]))
    q1.label = "Variable 1"
    q1.value_indices = {"A": 1, "B": 2}

    q2 = Variable(series=pl.Series("Q2", [4, 5, 6]))
    q2.label = "Variable 2"

    q3 = Variable(series=pl.Series("Q3", [["X"], ["X", "Y"], ["Y"]]))
    q3.label = "Variable 3"
    q3.value_indices = {"X": 1, "Y": 2}

    return Survey(variables=[q1, q2, q3])


def test_to_json_success(tmp_path: Path):
    survey = make_sample_survey()

    to_json(survey, tmp_path, name="out.json")

    output_file = tmp_path / "out.json"
    assert output_file.exists()

    with open(output_file) as f:
        data = json.load(f)

    assert "variables" in data
    assert len(data["variables"]) == 3


def test_to_json_path_as_str(tmp_path: Path):
    survey = make_sample_survey()

    to_json(survey, str(tmp_path), name="out.json")

    assert (tmp_path / "out.json").exists()


def test_to_json_write_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    survey = make_sample_survey()

    def mock_open(*args, **kwargs):
        raise OSError("Cannot write file")

    monkeypatch.setattr("builtins.open", mock_open)

    with pytest.raises(OSError):
        to_json(survey, tmp_path, name="fail.json")
