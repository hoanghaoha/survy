import polars
from polars.testing import assert_frame_equal
import pytest
from unittest.mock import patch

from survy.errors import DataStructureError
from survy.survey.survey import Survey
from survy.variable.variable import Variable


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


def test_survey_str(select_variable, multiselect_variable, number_variable):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])
    assert str(survey)
    print("\n", survey)


def test_survey_len(select_variable, multiselect_variable, number_variable):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])
    assert len(survey) == 3


def test_survey_iter(select_variable, multiselect_variable, number_variable):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])
    assert survey.variables == [var for var in survey]


def test_survey_get_variable(select_variable, multiselect_variable, number_variable):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])
    assert survey["Q1"] == select_variable
    assert survey[0] == select_variable
    assert survey["Q2"] == multiselect_variable
    assert survey[1] == multiselect_variable
    assert survey["Q3"] == number_variable
    assert survey[2] == number_variable


def test_survey_get_variable_error(
    select_variable, multiselect_variable, number_variable
):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])
    with pytest.raises(KeyError):
        assert survey["Q4"]


def test_survey_add_new_variable(
    select_variable, multiselect_variable, number_variable
):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])
    series = polars.Series("Q4", ["d", "e", "f", "g"])
    survey.add(Variable(series))
    assert survey["Q4"]


def test_survey_add_new_variable_by_series(
    select_variable, multiselect_variable, number_variable
):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])
    survey.add(polars.Series("Q4", ["d", "e", "f", "g"]))
    assert survey["Q4"]


def test_survey_add_exist_varible_id(
    select_variable, multiselect_variable, number_variable
):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])
    series = polars.Series("Q1", [["x", "z"], ["x", "y", "z"], ["y", "z"], ["z"]])
    survey.add(Variable(series))
    assert survey["Q1#1"]


def test_survey_drop_variable(select_variable, multiselect_variable, number_variable):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])
    survey.drop("Q1")
    assert len(survey.variables) == 2
    assert "Q1" not in [var.id for var in survey.variables]


def test_survey_sort_variable(select_variable, multiselect_variable, number_variable):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])
    survey.add(polars.Series("Q0", ["x", "y", "x", "z"]))
    survey.sort()
    assert [var.id for var in survey.variables] == sorted(["Q0", "Q1", "Q2", "Q3"])


def test_survey_sort_reverse(select_variable, multiselect_variable, number_variable):
    survey = Survey(variables=[select_variable, multiselect_variable, number_variable])
    survey.add(polars.Series("Q0", ["x", "y", "x", "z"]))
    survey.sort(reverse=True)
    assert [var.id for var in survey.variables] == sorted(
        ["Q0", "Q1", "Q2", "Q3"], reverse=True
    )


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


@pytest.fixture
def survey_with_id(select_variable, multiselect_variable, number_variable):
    id_var = Variable(series=polars.Series("id", [1, 2, 3, 4]))
    return Survey(variables=[id_var, select_variable, multiselect_variable, number_variable])


def _capture_write_database(survey, **kwargs):
    captured = []

    def _write(self, table_name, connection, **kw):
        captured.append((table_name, self.clone(), connection, kw))

    with patch.object(polars.DataFrame, "write_database", _write):
        survey.to_database(**kwargs)

    return {name: df for name, df, *_ in captured}, captured


def test_to_database_writes_four_tables(survey_with_id):
    _, calls = _capture_write_database(
        survey_with_id,
        id_variable="id",
        dim_respondent_variables=["Q1"],
        connection="sqlite:///test.db",
    )
    assert [name for name, *_ in calls] == [
        "fact_responses",
        "dim_respondent",
        "dim_variable",
        "dim_option",
    ]


def test_to_database_passes_connection_and_if_table_exists(survey_with_id):
    _, calls = _capture_write_database(
        survey_with_id,
        id_variable="id",
        dim_respondent_variables=["Q1"],
        connection="sqlite:///test.db",
        if_table_exists="replace",
    )
    for _, _df, conn, kw in calls:
        assert conn == "sqlite:///test.db"
        assert kw["if_table_exists"] == "replace"


def test_to_database_fact_responses_shape(survey_with_id):
    tables, _ = _capture_write_database(
        survey_with_id,
        id_variable="id",
        dim_respondent_variables=["id"],
        connection="sqlite:///test.db",
    )
    df = tables["fact_responses"]
    assert df.columns == ["id", "variable_id", "response_value"]
    # 4 respondents × (Q1 + Q2_1 + Q2_2 + Q2_3 + Q3) = 4 × 5 = 20 rows
    assert df.height == 20


def test_to_database_dim_respondent_includes_id_variable(survey_with_id):
    tables, _ = _capture_write_database(
        survey_with_id,
        id_variable="id",
        dim_respondent_variables=["Q1"],  # id not explicitly included
        connection="sqlite:///test.db",
    )
    df = tables["dim_respondent"]
    assert "id" in df.columns
    assert "Q1" in df.columns
    assert df.height == 4


def test_to_database_dim_variable_rows(survey_with_id):
    tables, _ = _capture_write_database(
        survey_with_id,
        id_variable="id",
        dim_respondent_variables=["id"],
        connection="sqlite:///test.db",
    )
    df = tables["dim_variable"]
    assert df.columns == ["id", "label", "base"]
    assert df["id"].to_list() == ["id", "Q1", "Q2", "Q3"]
    assert df["base"].to_list() == [4, 4, 4, 4]


def test_to_database_dim_option_rows(survey_with_id):
    tables, _ = _capture_write_database(
        survey_with_id,
        id_variable="id",
        dim_respondent_variables=["id"],
        connection="sqlite:///test.db",
    )
    df = tables["dim_option"]
    assert df.columns == ["id", "variable_id", "label", "index"]
    # Q1: a,b,c (3) + Q2: x,y,z (3) + id and Q3 have no value_indices
    assert df.height == 6
    assert set(df["variable_id"].to_list()) == {"Q1", "Q2"}


def test_to_database_dim_option_empty_when_no_value_indices():
    number_only = Survey(variables=[Variable(series=polars.Series("n", [1, 2, 3]))])
    tables, _ = _capture_write_database(
        number_only,
        id_variable="n",
        dim_respondent_variables=["n"],
        connection="sqlite:///test.db",
    )
    assert tables["dim_option"].is_empty()
