import pytest
import polars
from polars.testing import assert_frame_equal

from survy.io.polars import read_polars
from survy.separator import LOOP, MULTISELECT

raw_data_1 = {
    "Q1": ["a", "b", "c", "a", "a"],
    f"Q2{MULTISELECT}1": ["x", "x", "x", "", ""],
    f"Q2{MULTISELECT}2": ["y", "y", "", "y", ""],
    f"Q2{MULTISELECT}3": ["z", "", "", "z", "z"],
    "Q3": [10, 12, 13, 14, 20],
    "Q4": ["abc", "def", "xyz", "ghy", "czxc"],
    "Q5": ["a;c", "b;a", "a;b;c", "a", None],
    f"Q6{LOOP}1": ["a", "b", "c", "a", "a"],
    f"Q6{LOOP}2": ["a", "b", "c", "a", "c"],
    f"Q7{LOOP}1{MULTISELECT}1": ["x", "x", "x", "", ""],
    f"Q7{LOOP}1{MULTISELECT}2": ["y", "y", "", "y", ""],
    f"Q7{LOOP}2{MULTISELECT}1": ["x", "x", "", "x", ""],
    f"Q7{LOOP}2{MULTISELECT}2": ["y", "y", "", "y", "y"],
    f"Q8{LOOP}1": [10, 12, 13, 14, 20],
    f"Q8{LOOP}2": [20, 30, 31, 14, 22],
    f"Q9{LOOP}1": ["a;c", "b;a", "a;b;c", "a", None],
    f"Q9{LOOP}2": ["a;b", "a;b;c", "a;b;c", "a", None],
    f"Q10{LOOP}AB C": ["a", "b", "c", "a", "a"],
    f"Q10{LOOP}DE F G": ["a", "b", "c", "a", "c"],
}

raw_data_2 = {
    "Q1": ["a", "b", "c", "a", "a"],
    f"1{MULTISELECT}Q2": ["x", "x", "x", "", ""],
    f"2{MULTISELECT}Q2": ["y", "y", "", "y", ""],
    f"3{MULTISELECT}Q2": ["z", "", "", "z", "z"],
    "Q3": [10, 12, 13, 14, 20],
    "Q4": ["abc", "def", "xyz", "ghy", "czxc"],
    "Q5": ["a;c", "b;a", "a;b;c", "a", None],
    f"Q6{LOOP}1": ["a", "b", "c", "a", "a"],
    f"Q6{LOOP}2": ["a", "b", "c", "a", "c"],
    f"1{MULTISELECT}Q7{LOOP}1": ["x", "x", "x", "", ""],
    f"2{MULTISELECT}Q7{LOOP}1": ["y", "y", "", "y", ""],
    f"1{MULTISELECT}Q7{LOOP}2": ["x", "x", "", "x", ""],
    f"2{MULTISELECT}Q7{LOOP}2": ["y", "y", "", "y", "y"],
    f"Q8{LOOP}1": [10, 12, 13, 14, 20],
    f"Q8{LOOP}2": [20, 30, 31, 14, 22],
    f"Q9{LOOP}1": ["a;c", "b;a", "a;b;c", "a", None],
    f"Q9{LOOP}2": ["a;b", "a;b;c", "a;b;c", "a", None],
    f"Q10{LOOP}AB C": ["a", "b", "c", "a", "a"],
    f"Q10{LOOP}DE F G": ["a", "b", "c", "a", "c"],
}


@pytest.fixture
def sample_df_pattern_1():
    return polars.DataFrame(raw_data_1)


@pytest.fixture
def sample_df_pattern_2():
    return polars.DataFrame(raw_data_2)


expected_df = polars.DataFrame(
    {
        "Q1": ["a", "b", "c", "a", "a"],
        "Q2": [["x", "y", "z"], ["x", "y"], ["x"], ["y", "z"], ["z"]],
        "Q3": [10, 12, 13, 14, 20],
        "Q4": ["abc", "def", "xyz", "ghy", "czxc"],
        "Q5": [["a", "c"], ["a", "b"], ["a", "b", "c"], ["a"], []],
        f"Q6{LOOP}1": ["a", "b", "c", "a", "a"],
        f"Q6{LOOP}2": ["a", "b", "c", "a", "c"],
        f"Q7{LOOP}1": [["x", "y"], ["x", "y"], ["x"], ["y"], []],
        f"Q7{LOOP}2": [["x", "y"], ["x", "y"], [], ["x", "y"], ["y"]],
        f"Q8{LOOP}1": [10, 12, 13, 14, 20],
        f"Q8{LOOP}2": [20, 30, 31, 14, 22],
        f"Q9{LOOP}1": [["a", "c"], ["a", "b"], ["a", "b", "c"], ["a"], []],
        f"Q9{LOOP}2": [["a", "b"], ["a", "b", "c"], ["a", "b", "c"], ["a"], []],
        f"Q10{LOOP}1": ["a", "b", "c", "a", "a"],
        f"Q10{LOOP}2": ["a", "b", "c", "a", "c"],
    }
)


@pytest.mark.parametrize(
    "df_fixture, name_pattern",
    [
        ("sample_df_pattern_1", "id(.loop)?(_multi)?"),
        ("sample_df_pattern_2", "(multi_)?id(.loop)?"),
    ],
)
def test_read_polars(request, df_fixture, name_pattern):
    df = request.getfixturevalue(df_fixture)
    survey = read_polars(
        df,
        compact_ids=["Q5", "Q9"],
        compact_separator=";",
        name_pattern=name_pattern,
    )

    assert_frame_equal(
        survey.get_df(multiselect_dtype="compact"),
        expected_df,
    )


@pytest.mark.parametrize(
    "df_fixture, name_pattern",
    [
        ("sample_df_pattern_1", "id(.loop)?(_multi)?"),
        ("sample_df_pattern_2", "(multi_)?id(.loop)?"),
    ],
)
def test_loop_id(request, df_fixture, name_pattern):
    df = request.getfixturevalue(df_fixture)
    survey = read_polars(
        df,
        compact_ids=["Q5", "Q9"],
        compact_separator=";",
        name_pattern=name_pattern,
    )

    assert survey["Q6.1"].loop_id == "1"
    assert survey["Q6.2"].loop_id == "2"
    assert survey["Q7.1"].loop_id == "1"
    assert survey["Q7.2"].loop_id == "2"
    assert survey["Q8.1"].loop_id == "1"
    assert survey["Q8.2"].loop_id == "2"
    assert survey["Q9.1"].loop_id == "1"
    assert survey["Q9.2"].loop_id == "2"
    assert survey["Q10.1"].loop_id == "AB C"
    assert survey["Q10.2"].loop_id == "DE F G"
