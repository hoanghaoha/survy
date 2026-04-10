from pathlib import Path
import polars as pl
import pytest

from survy.io.spss import read_spss, to_spss
from survy.errors import FileTypeError
from survy.variable.variable import Variable
from survy.survey.survey import Survey


def make_mock_read_sav(df: pl.DataFrame):
    """Return a mock for pyreadstat.read_sav that returns (df, None)."""

    def mock_read_sav(path, **kwargs):
        return df, None

    return mock_read_sav


def test_read_spss_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    df = pl.DataFrame({"Q1": ["A", "B", "A"], "Q2": [1, 2, 3]})
    monkeypatch.setattr("pyreadstat.read_sav", make_mock_read_sav(df))

    file_path = tmp_path / "survey.sav"
    file_path.touch()

    survey = read_spss(file_path)

    assert isinstance(survey, Survey)
    assert len(survey.variables) == 2
    assert survey["Q1"].id == "Q1"
    assert survey["Q2"].id == "Q2"


def test_read_spss_path_as_str(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    df = pl.DataFrame({"Q1": ["A", "B", "A"]})
    monkeypatch.setattr("pyreadstat.read_sav", make_mock_read_sav(df))

    file_path = tmp_path / "survey.sav"
    file_path.touch()

    survey = read_spss(str(file_path))

    assert isinstance(survey, Survey)


def test_read_spss_wrong_extension(tmp_path: Path):
    file_path = tmp_path / "bad.csv"
    file_path.write_text("not sav")

    with pytest.raises(FileTypeError):
        read_spss(file_path)


def test_read_spss_applies_value_formats(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify read_sav is called with apply_value_formats=True and formats_as_category=False."""
    captured = {}

    def mock_read_sav(path, **kwargs):
        captured.update(kwargs)
        return pl.DataFrame({"Q1": ["A", "B"]}), None

    monkeypatch.setattr("pyreadstat.read_sav", mock_read_sav)

    file_path = tmp_path / "survey.sav"
    file_path.touch()

    read_spss(file_path)

    assert captured.get("apply_value_formats") is True
    assert captured.get("formats_as_category") is False
    assert captured.get("output_format") == "polars"


def test_read_spss_wide_multiselect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Wide multiselect columns (hobby_1, hobby_2) should be merged into one variable."""
    df = pl.DataFrame(
        {
            "gender": ["Male", "Female", "Male"],
            "hobby_1": ["Book", None, None],
            "hobby_2": [None, "Movie", "Movie"],
        }
    )
    monkeypatch.setattr("pyreadstat.read_sav", make_mock_read_sav(df))

    file_path = tmp_path / "survey.sav"
    file_path.touch()

    survey = read_spss(file_path)

    assert len(survey.variables) == 2
    assert survey["gender"].id == "gender"
    assert survey["hobby"].id == "hobby"
    assert survey["hobby"].series.to_list() == [["Book"], ["Movie"], ["Movie"]]


def make_sample_survey():
    q1 = Variable(series=pl.Series("Q1", ["A", "A", "B"]))
    q1.label = "Variable 1"
    q1.value_indices = {"A": 1, "B": 2}

    q2 = Variable(series=pl.Series("Q2", [3, 4, 5]))
    q2.label = "Variable 2"

    survey = Survey(variables=[q1, q2])

    return survey


def test_to_spss_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    survey = make_sample_survey()

    # mock pyreadstat.write_sav to avoid actual file dependency
    calls = {}

    def mock_write_sav(df, path):
        calls["called"] = True
        calls["path"] = path

    monkeypatch.setattr("pyreadstat.write_sav", mock_write_sav)

    to_spss(survey, tmp_path, name="out")

    # check SAV was "written"
    assert calls.get("called", False)
    assert str(calls["path"]).endswith("out_data.sav")

    # check syntax file
    syntax_file = tmp_path / "out_syntax.sps"
    assert syntax_file.exists()
    assert syntax_file.read_text() == survey.sps


def test_to_spss_path_as_str(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    survey = make_sample_survey()

    monkeypatch.setattr("pyreadstat.write_sav", lambda df, path: None)

    to_spss(survey, str(tmp_path), name="out")

    assert (tmp_path / "out_syntax.sps").exists()


def test_to_spss_custom_encoding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    survey = make_sample_survey()

    monkeypatch.setattr("pyreadstat.write_sav", lambda df, path: None)

    to_spss(survey, tmp_path, name="out", encoding="utf-8")

    content = (tmp_path / "out_syntax.sps").read_text(encoding="utf-8")
    assert content == survey.sps


def test_to_spss_write_error_sav(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    survey = make_sample_survey()

    def mock_write_sav(*args, **kwargs):
        raise OSError("Cannot write sav")

    monkeypatch.setattr("pyreadstat.write_sav", mock_write_sav)

    with pytest.raises(OSError):
        to_spss(survey, tmp_path, name="fail")


def test_to_spss_write_error_syntax(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    survey = make_sample_survey()

    monkeypatch.setattr("pyreadstat.write_sav", lambda df, path: None)

    def mock_open(*args, **kwargs):
        raise OSError("Cannot write syntax")

    monkeypatch.setattr("builtins.open", mock_open)

    with pytest.raises(OSError):
        to_spss(survey, tmp_path, name="fail")
