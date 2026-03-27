import pytest
import polars
from polars.testing import assert_frame_equal

from survy.errors import DataStructureError
from survy.io.polars import read_polars
from survy.separator import MULTISELECT

non_null_df = polars.DataFrame(
    {
        "Q1": ["a", "b", "c", "a", "a"],
        "Q2": [["x", "y", "z"], ["x", "y"], ["x"], ["y", "z"], ["z"]],
        "Q3": [10, 12, 13, 14, 20],
        "Q4": ["abc", "def", "xyz", "ghy", "czxc"],
    }
)


def test_non_null_survey():
    survey = read_polars(non_null_df)

    assert isinstance(survey.get_info(), list)
    assert isinstance(survey.get_info(as_yml=True), str)
    assert isinstance(survey.sps, str)

    assert survey.to_dict() == [
        {
            "id": "Q1",
            "label": "Q1",
            "option_indices": {"a": 1, "b": 2, "c": 3},
            "values": ["a", "b", "c", "a", "a"],
        },
        {
            "id": "Q2",
            "label": "Q2",
            "option_indices": {"x": 1, "y": 2, "z": 3},
            "values": [["x", "y", "z"], ["x", "y"], ["x"], ["y", "z"], ["z"]],
        },
        {
            "id": "Q3",
            "label": "Q3",
            "option_indices": {},
            "values": [10, 12, 13, 14, 20],
        },
        {
            "id": "Q4",
            "label": "Q4",
            "option_indices": {"abc": 1, "czxc": 2, "def": 3, "ghy": 4, "xyz": 5},
            "values": ["abc", "def", "xyz", "ghy", "czxc"],
        },
    ]

    assert_frame_equal(
        survey.get_df(select_dtype="text", multiselect_compact=True),
        polars.DataFrame(
            {
                "Q1": ["a", "b", "c", "a", "a"],
                "Q2": [["x", "y", "z"], ["x", "y"], ["x"], ["y", "z"], ["z"]],
                "Q3": [10, 12, 13, 14, 20],
                "Q4": ["abc", "def", "xyz", "ghy", "czxc"],
            }
        ),
    )

    assert_frame_equal(
        survey.get_df(select_dtype="number", multiselect_compact=True),
        polars.DataFrame(
            {
                "Q1": [1, 2, 3, 1, 1],
                "Q2": [["x", "y", "z"], ["x", "y"], ["x"], ["y", "z"], ["z"]],
                "Q3": [10, 12, 13, 14, 20],
                "Q4": [1, 3, 5, 4, 2],
            }
        ),
    )

    assert_frame_equal(
        survey.get_df(
            select_dtype="number", multiselect_compact=False, multiselect_dtype="number"
        ),
        polars.DataFrame(
            {
                "Q1": [1, 2, 3, 1, 1],
                f"Q2{MULTISELECT}1": [1, 1, 1, 0, 0],
                f"Q2{MULTISELECT}2": [1, 1, 0, 1, 0],
                f"Q2{MULTISELECT}3": [1, 0, 0, 1, 1],
                "Q3": [10, 12, 13, 14, 20],
                "Q4": [1, 3, 5, 4, 2],
            },
            schema={
                "Q1": polars.Int64,
                f"Q2{MULTISELECT}1": polars.Int8,
                f"Q2{MULTISELECT}2": polars.Int8,
                f"Q2{MULTISELECT}3": polars.Int8,
                "Q3": polars.Int64,
                "Q4": polars.Int64,
            },
        ),
    )

    assert_frame_equal(
        survey.get_df(
            select_dtype="text", multiselect_compact=False, multiselect_dtype="text"
        ),
        polars.DataFrame(
            {
                "Q1": ["a", "b", "c", "a", "a"],
                f"Q2{MULTISELECT}1": ["x", "x", "x", None, None],
                f"Q2{MULTISELECT}2": ["y", "y", None, "y", None],
                f"Q2{MULTISELECT}3": ["z", None, None, "z", "z"],
                "Q3": [10, 12, 13, 14, 20],
                "Q4": ["abc", "def", "xyz", "ghy", "czxc"],
            },
            schema={
                "Q1": polars.String,
                f"Q2{MULTISELECT}1": polars.String,
                f"Q2{MULTISELECT}2": polars.String,
                f"Q2{MULTISELECT}3": polars.String,
                "Q3": polars.Int64,
                "Q4": polars.String,
            },
        ),
    )


have_null_df = polars.DataFrame(
    {
        "Q1": ["a", "b", "c", "a", ""],
        "Q2": [["x", "y", "z"], ["x", "y"], ["x"], ["y", "z"], ["z"]],
        "Q3": [10, 12, 13, 14, None],
        "Q4": ["abc", "def", "xyz", "ghy", None],
    }
)


def test_have_null_survey():
    survey = read_polars(have_null_df)

    assert isinstance(survey.get_info(), list)
    assert isinstance(survey.get_info(as_yml=True), str)
    assert isinstance(survey.sps, str)

    assert survey.to_dict() == [
        {
            "id": "Q1",
            "label": "Q1",
            "option_indices": {"a": 1, "b": 2, "c": 3},
            "values": ["a", "b", "c", "a", None],
        },
        {
            "id": "Q2",
            "label": "Q2",
            "option_indices": {"x": 1, "y": 2, "z": 3},
            "values": [["x", "y", "z"], ["x", "y"], ["x"], ["y", "z"], ["z"]],
        },
        {
            "id": "Q3",
            "label": "Q3",
            "option_indices": {},
            "values": [10, 12, 13, 14, None],
        },
        {
            "id": "Q4",
            "label": "Q4",
            "option_indices": {"abc": 1, "def": 2, "ghy": 3, "xyz": 4},
            "values": ["abc", "def", "xyz", "ghy", None],
        },
    ]

    assert_frame_equal(
        survey.get_df(select_dtype="text", multiselect_compact=True),
        polars.DataFrame(
            {
                "Q1": ["a", "b", "c", "a", None],
                "Q2": [["x", "y", "z"], ["x", "y"], ["x"], ["y", "z"], ["z"]],
                "Q3": [10, 12, 13, 14, None],
                "Q4": ["abc", "def", "xyz", "ghy", None],
            }
        ),
    )

    assert_frame_equal(
        survey.get_df(
            select_dtype="number", multiselect_compact=False, multiselect_dtype="number"
        ),
        polars.DataFrame(
            {
                "Q1": [1, 2, 3, 1, None],
                f"Q2{MULTISELECT}1": [1, 1, 1, 0, 0],
                f"Q2{MULTISELECT}2": [1, 1, 0, 1, 0],
                f"Q2{MULTISELECT}3": [1, 0, 0, 1, 1],
                "Q3": [10, 12, 13, 14, None],
                "Q4": [1, 2, 4, 3, None],
            },
            schema={
                "Q1": polars.Int64,
                f"Q2{MULTISELECT}1": polars.Int8,
                f"Q2{MULTISELECT}2": polars.Int8,
                f"Q2{MULTISELECT}3": polars.Int8,
                "Q3": polars.Int64,
                "Q4": polars.Int64,
            },
        ),
    )

    assert_frame_equal(
        survey.get_df(
            select_dtype="text", multiselect_compact=False, multiselect_dtype="text"
        ),
        polars.DataFrame(
            {
                "Q1": ["a", "b", "c", "a", None],
                f"Q2{MULTISELECT}1": ["x", "x", "x", None, None],
                f"Q2{MULTISELECT}2": ["y", "y", None, "y", None],
                f"Q2{MULTISELECT}3": ["z", None, None, "z", "z"],
                "Q3": [10, 12, 13, 14, None],
                "Q4": ["abc", "def", "xyz", "ghy", None],
            },
            schema={
                "Q1": polars.String,
                f"Q2{MULTISELECT}1": polars.String,
                f"Q2{MULTISELECT}2": polars.String,
                f"Q2{MULTISELECT}3": polars.String,
                "Q3": polars.Int64,
                "Q4": polars.String,
            },
        ),
    )


def test_update_survey():
    survey = read_polars(non_null_df)

    survey.update(
        [
            {
                "id": "Q1",
                "label": "Question 1",
                "option_indices": {"b": 1, "a": 2, "c": 3},
            },
            {
                "id": "Q2",
                "label": "Question 2",
                "option_indices": {"y": 1, "x": 2, "z": 3},
            },
        ]
    )

    assert survey.to_dict() == [
        {
            "id": "Q1",
            "label": "Question 1",
            "option_indices": {"a": 2, "b": 1, "c": 3},
            "values": ["a", "b", "c", "a", "a"],
        },
        {
            "id": "Q2",
            "label": "Question 2",
            "option_indices": {"x": 2, "y": 1, "z": 3},
            "values": [["x", "y", "z"], ["x", "y"], ["x"], ["y", "z"], ["z"]],
        },
        {
            "id": "Q3",
            "label": "Q3",
            "option_indices": {},
            "values": [10, 12, 13, 14, 20],
        },
        {
            "id": "Q4",
            "label": "Q4",
            "option_indices": {"abc": 1, "czxc": 2, "def": 3, "ghy": 4, "xyz": 5},
            "values": ["abc", "def", "xyz", "ghy", "czxc"],
        },
    ]

    assert isinstance(survey.get_info(), list)
    assert isinstance(survey.get_info(as_yml=True), str)
    assert isinstance(survey.sps, str)

    with pytest.raises(DataStructureError):
        survey.update(
            [
                {"id": "Q1", "label": "Question 1", "option_indices": {"a": 2, "c": 3}},
            ]
        )
        assert survey.questions


def test_update_survey_by_yml():
    survey = read_polars(non_null_df)

    survey.update_by_yml("""
- id: Q1
  label: Question 1
  option_indices:
    a: 2
    b: 1
    c: 3
- id: Q2
  label: Question 2
  option_indices:
    x: 2
    y: 1
    z: 3
""")

    assert survey.to_dict() == [
        {
            "id": "Q1",
            "label": "Question 1",
            "option_indices": {"a": 2, "b": 1, "c": 3},
            "values": ["a", "b", "c", "a", "a"],
        },
        {
            "id": "Q2",
            "label": "Question 2",
            "option_indices": {"x": 2, "y": 1, "z": 3},
            "values": [["x", "y", "z"], ["x", "y"], ["x"], ["y", "z"], ["z"]],
        },
        {
            "id": "Q3",
            "label": "Q3",
            "option_indices": {},
            "values": [10, 12, 13, 14, 20],
        },
        {
            "id": "Q4",
            "label": "Q4",
            "option_indices": {"abc": 1, "czxc": 2, "def": 3, "ghy": 4, "xyz": 5},
            "values": ["abc", "def", "xyz", "ghy", "czxc"],
        },
    ]

    assert isinstance(survey.get_info(), list)
    assert isinstance(survey.get_info(as_yml=True), str)
    assert isinstance(survey.sps, str)

    with pytest.raises(DataStructureError):
        survey.update(
            [
                {"id": "Q1", "label": "Question 1", "option_indices": {"a": 2, "c": 3}},
            ]
        )
        assert survey.questions
