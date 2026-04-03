import pytest
import polars
from polars.testing import assert_frame_equal

from survy.io.polars import read_polars


raw_data_1 = {
    "Q1": ["a", "b", "c", "a", "a"],
    "Q2_1": ["x", "x", "x", "", ""],
    "Q2_2": ["y", "y", "", "y", ""],
    "Q2_3": ["z", "", "", "z", "z"],
    "Q3": [10, 12, 13, 14, 20],
    "Q4": ["abc", "def", "xyz", "ghy", "czxc"],
    "Q5": ["a;c", "b;a", "a;b;c", "a", None],
}

raw_data_2 = {
    "Q1": ["a", "b", "c", "a", "a"],
    "1_Q2": ["x", "x", "x", "", ""],
    "2_Q2": ["y", "y", "", "y", ""],
    "3_Q2": ["z", "", "", "z", "z"],
    "Q3": [10, 12, 13, 14, 20],
    "Q4": ["abc", "def", "xyz", "ghy", "czxc"],
    "Q5": ["a;c", "b;a", "a;b;c", "a", None],
}


@pytest.fixture
def sample_df_pattern_1():
    return polars.DataFrame(raw_data_1)


@pytest.fixture
def sample_df_pattern_2():
    return polars.DataFrame(raw_data_2)


@pytest.fixture
def sample_df_with_null():
    return polars.DataFrame(
        {
            **raw_data_1,
            **{"Q11": [None, None, None, None, None], "Q12": [[], [], [], [], []]},
        }
    )


expected_df = polars.DataFrame(
    {
        "Q1": ["a", "b", "c", "a", "a"],
        "Q2": [["x", "y", "z"], ["x", "y"], ["x"], ["y", "z"], ["z"]],
        "Q3": [10, 12, 13, 14, 20],
        "Q4": ["abc", "def", "xyz", "ghy", "czxc"],
        "Q5": [["a", "c"], ["a", "b"], ["a", "b", "c"], ["a"], []],
    }
)


@pytest.mark.parametrize(
    "df_fixture, name_pattern",
    [
        ("sample_df_pattern_1", "id(_multi)?"),
        ("sample_df_pattern_2", "(multi_)?id"),
    ],
)
def test_read_polars(
    request: pytest.FixtureRequest, df_fixture: str, name_pattern: str
):
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


def test_read_df_with_null(sample_df_with_null):
    with pytest.warns(UserWarning):
        survey = read_polars(
            sample_df_with_null,
            compact_ids=["Q5", "Q9"],
            compact_separator=";",
            name_pattern="id(_multi)?",
            exclude_null=True,
        )
        assert survey
