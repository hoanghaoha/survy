import polars
from polars.testing import assert_frame_equal
import pytest
from unittest.mock import patch

from survy.errors import DataStructureError
from survy.survey.survey import Survey
from survy.survey.variable import Variable


@pytest.fixture
def select_variable():
    return Variable(series=polars.Series("Q1", ["a", "b", "c", "a"]))


@pytest.fixture
def multiselect_variable():
    return Variable(
        series=polars.Series("Q2", [["x", "y"], ["x", "z"], ["y", "z"], ["y"]])
    )


@pytest.fixture
def number_variable():
    return Variable(series=polars.Series("Q3", [24, 22, 4, 209]))


def test_survey_get_variable(select_variable, multiselect_variable, number_variable):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])
    assert survey["Q1"] == select_variable
    assert survey["Q2"] == multiselect_variable
    assert survey["Q3"] == number_variable


def test_survey_get_variable_error(
    select_variable, multiselect_variable, number_variable
):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])
    with pytest.raises(KeyError):
        assert survey["Q4"]


def test_survey_get_df_text_compact(
    select_variable, multiselect_variable, number_variable
):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])

    assert_frame_equal(
        survey.get_df(select_dtype="text", multiselect_dtype="compact"),
        polars.DataFrame(
            {
                "Q1": ["a", "b", "c", "a"],
                "Q2": [["x", "y"], ["x", "z"], ["y", "z"], ["y"]],
                "Q3": [24, 22, 4, 209],
            }
        ),
    )


def test_survey_get_df_number_compact(
    select_variable, multiselect_variable, number_variable
):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])

    assert_frame_equal(
        survey.get_df(select_dtype="number", multiselect_dtype="compact"),
        polars.DataFrame(
            {
                "Q1": [1, 2, 3, 1],
                "Q2": [["x", "y"], ["x", "z"], ["y", "z"], ["y"]],
                "Q3": [24, 22, 4, 209],
            }
        ),
    )


def test_survey_get_df_text_text(
    select_variable, multiselect_variable, number_variable
):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])

    assert_frame_equal(
        survey.get_df(select_dtype="text", multiselect_dtype="text"),
        polars.DataFrame(
            {
                "Q1": ["a", "b", "c", "a"],
                "Q2_1": ["x", "x", None, None],
                "Q2_2": ["y", None, "y", "y"],
                "Q2_3": [None, "z", "z", None],
                "Q3": [24, 22, 4, 209],
            }
        ),
    )


def test_survey_get_df_text_number(
    select_variable, multiselect_variable, number_variable
):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])

    assert_frame_equal(
        survey.get_df(select_dtype="text", multiselect_dtype="number"),
        polars.DataFrame(
            {
                "Q1": ["a", "b", "c", "a"],
                "Q2_1": [1, 1, 0, 0],
                "Q2_2": [1, 0, 1, 1],
                "Q2_3": [0, 1, 1, 0],
                "Q3": [24, 22, 4, 209],
            },
            schema={
                "Q1": polars.String,
                "Q2_1": polars.Int8,
                "Q2_2": polars.Int8,
                "Q2_3": polars.Int8,
                "Q3": polars.Int64,
            },
        ),
    )


def test_survey_get_sps(select_variable, multiselect_variable, number_variable):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])

    assert isinstance(survey.sps, str)


def test_survey_update(select_variable, multiselect_variable, number_variable):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])

    survey.update(
        [
            {
                "id": "Q1",
                "label": "Test Select",
                "value_indices": {"a": 2, "b": 1, "c": 3},
            },
            {
                "id": "Q2",
                "label": "Test MultiSelect",
                "value_indices": {"x": 2, "y": 1, "z": 3},
            },
            {
                "id": "Q3",
                "label": "Test Number",
            },
        ]
    )

    assert survey["Q1"].label == "Test Select"
    assert survey["Q1"].value_indices == {"a": 2, "b": 1, "c": 3}

    assert survey["Q2"].label == "Test MultiSelect"
    assert survey["Q2"].value_indices == {"y": 1, "x": 2, "z": 3}

    assert survey["Q3"].label == "Test Number"


def test_survey_update_warnings(select_variable, multiselect_variable, number_variable):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])

    with pytest.warns(UserWarning):
        survey.update(
            [
                {
                    "id": "Q4",
                    "label": "Test Warnings",
                    "value_indices": {"a": 2, "b": 1, "c": 3},
                },
            ]
        )


def test_survey_update_error(select_variable, multiselect_variable, number_variable):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])

    with pytest.raises(DataStructureError):
        survey.update([{"id": "Q1", "value_indices": {"a": 1}}])


@patch("survy.io.json.to_json")
def test_to_json(mock_to_json):
    survey = Survey([])
    survey.to_json("path", name="test")

    mock_to_json.assert_called_once()


@patch("survy.io.spss.to_spss")
def test_to_spss(mock_to_spss):
    survey = Survey([])
    survey.to_spss("path", name="test")

    mock_to_spss.assert_called_once()


@patch("survy.io.csv.to_csv")
def test_to_csv(mock_to_csv):
    survey = Survey([])
    survey.to_csv("path", name="test", compact=True)

    mock_to_csv.assert_called_once()
