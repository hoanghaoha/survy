import polars
from polars.testing import assert_frame_equal

from survy.io._utils import process_raw_data
from survy.separator import MULTISELECT


def test_proces_raw_data():
    raw_data = {
        "Q1": ["a", "b", "c", "a", "a"],
        f"Q2{MULTISELECT}1": ["x", "x", "x", "", ""],
        f"Q2{MULTISELECT}2": ["y", "y", "", "y", ""],
        f"Q2{MULTISELECT}3": ["z", "", "", "z", "z"],
        "Q3": [10, 12, 13, 14, 20],
        "Q4": ["abc", "def", "xyz", "ghy", "czxc"],
    }

    df = polars.DataFrame(
        {
            "Q1": ["a", "b", "c", "a", "a"],
            "Q2": [["x", "y", "z"], ["x", "y"], ["x"], ["y", "z"], ["z"]],
            "Q3": [10, 12, 13, 14, 20],
            "Q4": ["abc", "def", "xyz", "ghy", "czxc"],
        }
    )

    assert_frame_equal(process_raw_data(raw_data), df)
