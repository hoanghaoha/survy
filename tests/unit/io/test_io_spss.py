from pathlib import Path
import polars as pl
import pytest

from survy.io.spss import to_spss
from survy.survey.question import Question
from survy.survey.survey import Survey


def make_sample_survey():
    q1 = Question(series=pl.Series("Q1", ["A", "A", "B"]))
    q1.label = "Question 1"
    q1.option_indices = {"A": 1, "B": 2}

    q2 = Question(series=pl.Series("Q2", [3, 4, 5]))
    q2.label = "Question 2"

    survey = Survey(questions=[q1, q2])

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
