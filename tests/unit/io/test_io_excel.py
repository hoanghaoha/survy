import polars as pl
import pytest
from pathlib import Path

from survy.io.excel import read_excel, to_excel
from survy.errors import FileTypeError
from survy.variable.variable import Variable
from survy.survey.survey import Survey


def make_sample_excel(path: Path):
    df = pl.DataFrame(
        {
            "Q1": ["A", "B", "A"],
            "Q2": [1, 2, 3],
            "Q3": ["X;Y", "X", "Y"],
        }
    )

    file_path = path / "survey.xlsx"
    df.write_excel(file_path)

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


def test_read_excel_success(tmp_path: Path):
    file_path, df = make_sample_excel(tmp_path)

    survey = read_excel(file_path, compact_ids=["Q3"])

    assert isinstance(survey, Survey)
    assert len(survey.variables) == len(df.columns)

    for col in df.columns:
        q = survey[col]
        assert q.id == col


def test_read_excel_path_as_str(tmp_path: Path):
    file_path, _ = make_sample_excel(tmp_path)

    survey = read_excel(str(file_path))

    assert isinstance(survey, Survey)


def test_read_excel_wrong_extension(tmp_path: Path):
    file_path = tmp_path / "bad.txt"
    file_path.write_text("not excel")

    with pytest.raises(FileTypeError):
        read_excel(file_path)


def test_read_excel_missing_file():
    with pytest.raises(FileNotFoundError):
        read_excel("non_existent.xlsx")


def test_to_excel_success_compact(tmp_path: Path):
    survey = make_sample_survey()

    to_excel(survey, tmp_path, name="out", compact=True)

    assert (tmp_path / "out_data.xlsx").exists()
    assert (tmp_path / "out_variables_info.xlsx").exists()
    assert (tmp_path / "out_options_info.xlsx").exists()


def test_to_excel_success_non_compact(tmp_path: Path):
    survey = make_sample_survey()

    to_excel(survey, tmp_path, name="out", compact=False)

    assert (tmp_path / "out_data.xlsx").exists()


def test_to_excel_path_as_str(tmp_path: Path):
    survey = make_sample_survey()

    to_excel(survey, str(tmp_path), name="out")

    assert (tmp_path / "out_data.xlsx").exists()


def test_to_excel_output_content(tmp_path: Path):
    survey = make_sample_survey()

    to_excel(survey, tmp_path, name="out")

    df = pl.read_excel(tmp_path / "out_data.xlsx")

    assert "Q1" in df.columns
    assert "Q2" in df.columns
    assert "Q3" in df.columns


def test_to_excel_write_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    survey = make_sample_survey()

    def mock_write_excel(*args, **kwargs):
        raise OSError("Cannot write")

    monkeypatch.setattr("polars.DataFrame.write_excel", mock_write_excel)

    with pytest.raises(OSError):
        to_excel(survey, tmp_path, name="fail")
