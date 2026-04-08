import polars as pl
import pytest
from pathlib import Path

from survy.io.csv import read_csv, to_csv
from survy.errors import FileTypeError
from survy.variable.variable import Variable
from survy.survey.survey import Survey


def make_sample_csv(path: Path):
    df = pl.DataFrame(
        {
            "Q1": ["A", "B", "A"],
            "Q2": [1, 2, 3],
            "Q3": ["X;Y", "X", "Y"],
        }
    )

    file_path = path / "survey.csv"
    df.write_csv(file_path)

    return file_path, df


def make_sample_survey():
    q1 = Variable(series=pl.Series("Q1", ["A", "B", "A"]))
    q1.label = "Variable 1"
    q1.value_indices = {"A": 1, "B": 2}

    q2 = Variable(series=pl.Series("Q2", [1, 2, 3]))
    q2.label = "Variable 2"

    q3 = Variable(series=pl.Series("Q3", [["X", "Y"], ["X"], ["Y"]]))
    q3.label = "Variable 3"
    q3.value_indices = {"X": 1, "Y": 2}

    return Survey(variables=[q1, q2, q3])


def test_read_csv_success(tmp_path: Path):
    file_path, df = make_sample_csv(tmp_path)

    survey = read_csv(file_path, compact_ids=["Q3"])

    assert isinstance(survey, Survey)
    assert len(survey.variables) == len(df.columns)

    for col in df.columns:
        q = survey[col]
        assert q.id == col


def test_read_csv_path_as_str(tmp_path: Path):
    file_path, _ = make_sample_csv(tmp_path)

    survey = read_csv(str(file_path))

    assert isinstance(survey, Survey)


def test_read_csv_wrong_extension(tmp_path: Path):
    file_path = tmp_path / "bad.txt"
    file_path.write_text("not csv")

    with pytest.raises(FileTypeError):
        read_csv(file_path)


def test_read_csv_missing_file():
    with pytest.raises(FileNotFoundError):
        read_csv("non_existent.csv")


def test_to_csv_success_compact(tmp_path: Path):
    survey = make_sample_survey()

    to_csv(survey, tmp_path, name="out", compact=True)

    assert (tmp_path / "out_data.csv").exists()
    assert (tmp_path / "out_variables_info.csv").exists()
    assert (tmp_path / "out_values_info.csv").exists()


def test_to_csv_success_non_compact(tmp_path: Path):
    survey = make_sample_survey()

    to_csv(survey, tmp_path, name="out", compact=False)

    assert (tmp_path / "out_data.csv").exists()


def test_to_csv_path_as_str(tmp_path: Path):
    survey = make_sample_survey()

    to_csv(survey, str(tmp_path), name="out")

    assert (tmp_path / "out_data.csv").exists()


def test_to_csv_output_content(tmp_path: Path):
    survey = make_sample_survey()

    to_csv(survey, tmp_path, name="out")

    df = pl.read_csv(tmp_path / "out_data.csv")

    assert "Q1" in df.columns
    assert "Q2" in df.columns
    assert "Q3" in df.columns


def test_to_csv_write_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    survey = make_sample_survey()

    def mock_write_csv(*args, **kwargs):
        raise OSError("Cannot write")

    monkeypatch.setattr("polars.DataFrame.write_csv", mock_write_csv)

    with pytest.raises(OSError):
        to_csv(survey, tmp_path, name="fail")
