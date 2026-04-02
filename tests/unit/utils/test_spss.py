import pytest

from survy.utils.spss import (
    variable_labels,
    variable_level,
    value_labels,
    mrset,
    ctables,
)
from survy.survey.question import QuestionType
from survy.separator import MULTISELECT


def test_variable_labels_select():
    result = variable_labels(QuestionType.SELECT, "Q1", "Age")
    assert result == "VARIABLE LABELS Q1 'Age'."


def test_variable_labels_number():
    result = variable_labels(QuestionType.NUMBER, "Q1", "Age")
    assert result == "VARIABLE LABELS Q1 'Age'."


def test_variable_labels_multiselect():
    result = variable_labels(
        QuestionType.MULTISELECT,
        "Q1",
        "Hobbies",
        {"Sports": 1, "Music": 2},
    )
    expected = "\n".join(
        [
            f"VARIABLE LABELS Q1{MULTISELECT}1 '[Sports] Hobbies'.",
            f"VARIABLE LABELS Q1{MULTISELECT}2 '[Music] Hobbies'.",
        ]
    )
    assert result == expected


def test_variable_labels_multiselect_empty():
    result = variable_labels(QuestionType.MULTISELECT, "Q1", "Hobbies", {})
    assert result == ""


def test_variable_labels_invalid_type():
    with pytest.raises(KeyError):
        variable_labels("UNKNOWN", "Q1", "Label")


def test_variable_level_select():
    result = variable_level(QuestionType.SELECT, "Q1", "NOMINAL")
    assert result == "VARIABLE LEVEL Q1 (NOMINAL)."


def test_variable_level_multiselect():
    result = variable_level(
        QuestionType.MULTISELECT,
        "Q1",
        "NOMINAL",
        {"A": 1, "B": 2},
    )
    expected = "\n".join(
        [
            f"VARIABLE LEVEL Q1{MULTISELECT}1 (NOMINAL).",
            f"VARIABLE LEVEL Q1{MULTISELECT}2 (NOMINAL).",
        ]
    )
    assert result == expected


def test_variable_level_multiselect_empty():
    result = variable_level(QuestionType.MULTISELECT, "Q1", "NOMINAL", {})
    assert result == ""


def test_value_labels_select():
    result = value_labels(
        QuestionType.SELECT,
        "Q1",
        {"Yes": 1, "No": 0},
    )
    expected = "VALUE LABELS Q1 1 'Yes'\n0 'No'."
    assert result == expected


def test_value_labels_multiselect():
    result = value_labels(
        QuestionType.MULTISELECT,
        "Q1",
        {"A": 1, "B": 2},
    )
    expected = "\n".join(
        [
            f"VALUE LABELS Q1{MULTISELECT}1 1 'A'.",
            f"VALUE LABELS Q1{MULTISELECT}2 1 'B'.",
        ]
    )
    assert result == expected


def test_value_labels_empty():
    result = value_labels(QuestionType.SELECT, "Q1", {})
    assert result == ""


def test_mrset_basic():
    result = mrset("Q1", "Hobbies", {"A": 1, "B": 2})

    assert "MRSETS /MDGROUP NAME=$Q1" in result
    assert "LABEL='Hobbies'" in result
    assert f"Q1{MULTISELECT}1" in result
    assert f"Q1{MULTISELECT}2" in result


def test_mrset_empty():
    result = mrset("Q1", "Hobbies", {})
    assert result == ""


def test_ctables_select():
    result = ctables({"Q1": QuestionType.SELECT})
    assert "Q1 [C][COUNT F40.0, TOTALS[COUNT F40.0]] +" in result


def test_ctables_multiselect():
    result = ctables({"Q1": QuestionType.MULTISELECT})
    assert "$Q1 [C][COUNT F40.0, TOTALS[COUNT F40.0]] +" in result


def test_ctables_number():
    result = ctables({"Q1": QuestionType.NUMBER})
    assert "Q1 [MEAN COMMA40.2] +" in result


def test_ctables_mixed():
    result = ctables(
        {
            "Q1": QuestionType.SELECT,
            "Q2": QuestionType.MULTISELECT,
            "Q3": QuestionType.NUMBER,
        }
    )

    assert "Q1 [C][COUNT F40.0" in result
    assert "$Q2 [C][COUNT F40.0" in result
    assert "Q3 [MEAN COMMA40.2]" in result


def test_ctables_structure():
    result = ctables({"Q1": QuestionType.SELECT})

    assert result.startswith("CTABLES")
    assert "/TABLE" in result
    assert "BY [Input Tabspec here]" in result
