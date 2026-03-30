import polars
from polars.testing import assert_frame_equal

from survy.io.polars import read_polars
from survy.separator import MULTISELECT


def test_read_polars():
    raw_data = {
        "Q1": ["a", "b", "c", "a", "a"],
        f"Q2{MULTISELECT}1": ["x", "x", "x", "", ""],
        f"Q2{MULTISELECT}2": ["y", "y", "", "y", ""],
        f"Q2{MULTISELECT}3": ["z", "", "", "z", "z"],
        "Q3": [10, 12, 13, 14, 20],
        "Q4": ["abc", "def", "xyz", "ghy", "czxc"],
        "Q5": ["a;c", "b;a", "a;b;c", "a", None],
    }

    expected_df = polars.DataFrame(
        {
            "Q1": ["a", "b", "c", "a", "a"],
            "Q2": [["x", "y", "z"], ["x", "y"], ["x"], ["y", "z"], ["z"]],
            "Q3": [10, 12, 13, 14, 20],
            "Q4": ["abc", "def", "xyz", "ghy", "czxc"],
            "Q5": [["a", "c"], ["a", "b"], ["a", "b", "c"], ["a"], []],
        }
    )

    assert_frame_equal(
        read_polars(
            polars.DataFrame(raw_data),
            multiselects_as_single_column=["Q5"],
            multiselect_separator=";",
            name_pattern="id(.loop)?(_multi)?",
        ).get_df(multiselect_compact=True),
        expected_df,
    )
