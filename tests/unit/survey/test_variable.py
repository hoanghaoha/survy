import pytest
import polars
from polars.testing import assert_frame_equal
import warnings

from survy.errors import DataStructureError, VarTypeError
from survy.variable.variable import Variable
from survy.variable._utils import VarType


def test_variable_id():
    s = polars.Series("Q1", ["A", "B"])
    q = Variable(s)

    assert q.id == "Q1"


def test_variable_str():
    s = polars.Series("Q1", ["A", "B"])
    q = Variable(s)
    q.label = "Question 1"
    assert (
        str(q)
        == """Variable(id=Q1, base=2, label=Question 1, value_indices={'A': 1, 'B': 2})"""
    )

    assert q.id == "Q1"


def test_variable_len():
    s = polars.Series("Q1", ["A", "B"])
    q = Variable(s)
    q.label = "Question 1"
    assert len(q) == 2


def test_variable_iter():
    s = polars.Series("Q1", ["A", "B"])
    q = Variable(s)
    assert [d for d in q] == ["A", "B"]


def test_variable_getitem():
    s = polars.Series("Q1", ["A", "B", "C"])
    q = Variable(s)
    assert q[0] == "A"
    assert q[0:2].to_list() == ["A", "B"]


def test_variable_rename():
    s = polars.Series("Q1", ["A", "B"])
    q = Variable(s)
    q.id = "Q1@1"

    assert q.id == "Q1@1"


def test_variable_replace():
    s = polars.Series("Q1", ["A", "B"])
    q = Variable(s)
    q.replace({"A": "A1"})

    assert q.value_indices == {"A1": 1, "B": 2}


def test_len_property():
    s = polars.Series("Q1", ["A", "B", None])
    q = Variable(s)

    assert q.len == 3


def test_base_counts_non_empty():
    s = polars.Series("Q1", ["A", "", None, "B"])
    q = Variable(s)

    assert q.base == 2


def test_vtype_select():
    s = polars.Series("Q1", ["A", "B"])
    q = Variable(s)

    assert q.vtype == VarType.SELECT


def test_vtype_number():
    s = polars.Series("Q1", [1, 2, 3])
    q = Variable(s)

    assert q.vtype == VarType.NUMBER


def test_vtype_multiselect():
    s = polars.Series("Q1", [["A", "B"], ["B"]])
    q = Variable(s)

    assert q.vtype == VarType.MULTISELECT


def test_vtype_fallback_to_select_with_warning():
    s = polars.Series("Q1", [True, False])

    with warnings.catch_warnings(record=True) as w:
        q = Variable(s)
        assert q.vtype == VarType.SELECT
        assert len(w) > 0


def test_vtype_error_on_invalid_cast(monkeypatch):
    s = polars.Series("Q1", [object()])

    def broken_cast(*args, **kwargs):
        raise Exception("fail")

    monkeypatch.setattr(s, "cast", broken_cast)

    with pytest.raises(VarTypeError):
        Variable(s).vtype


def test_label_default():
    s = polars.Series("Q1", ["A"])
    q = Variable(s)

    assert q.label == "Q1"


def test_label_custom():
    s = polars.Series("Q1", ["A"])
    q = Variable(s)
    q.label = "Custom"

    assert q.label == "Custom"


def test_value_indices_auto():
    s = polars.Series("Q1", ["A", "B", "A"])
    q = Variable(s)

    mapping = q.value_indices

    assert set(mapping.keys()) == {"A", "B"}


def test_value_indices_numeric_empty():
    s = polars.Series("Q1", [1, 2, 3])
    q = Variable(s)

    assert q.value_indices == {}


def test_value_indices_set_valid():
    s = polars.Series("Q1", ["A", "B"])
    q = Variable(s)

    q.value_indices = {"A": 1, "B": 2}

    assert q.value_indices == {"A": 1, "B": 2}


def test_value_indices_set_invalid():
    s = polars.Series("Q1", ["A", "B"])
    q = Variable(s)

    with pytest.raises(DataStructureError):
        q.value_indices = {"A": 1}


def test_strategy_select():
    s = polars.Series("Q1", ["A", "B"])
    q = Variable(s)

    assert q.strategy.__class__.__name__ == "_SelectStrategy"


def test_strategy_number():
    s = polars.Series("Q1", [1, 2])
    q = Variable(s)

    assert q.strategy.__class__.__name__ == "_NumberStrategy"


def test_strategy_multiselect():
    s = polars.Series("Q1", [["A"], ["B"]])
    q = Variable(s)

    assert q.strategy.__class__.__name__ == "_MultiSelectStrategy"


def test_to_dict():
    s = polars.Series("Q1", ["A", "B"])
    q = Variable(s)

    d = q.to_dict()

    assert d["id"] == "Q1"
    assert "data" in d
    assert "vtype" in d


def test_frequencies_select():
    s = polars.Series("Q1", ["A", "B", "B"])
    q = Variable(s)

    assert_frame_equal(
        q.frequencies,
        polars.DataFrame(
            {
                "Q1": ["A", "B"],
                "count": [1, 2],
                "proportion": [1 / 3, 2 / 3],
            },
            schema={
                "Q1": polars.String,
                "count": polars.UInt32,
                "proportion": polars.Float64,
            },
        ),
    )


def test_frequencies_multiselect():
    s = polars.Series("Q1", [["X", "Y"], ["X"], ["Y"]])
    q = Variable(s)

    assert_frame_equal(
        q.frequencies,
        polars.DataFrame(
            {
                "Q1": ["X", "Y"],
                "count": [2, 2],
                "proportion": [2 / 3, 2 / 3],
            },
            schema={
                "Q1": polars.String,
                "count": polars.UInt32,
                "proportion": polars.Float64,
            },
        ),
    )


def test_sps_calls_strategy(monkeypatch):
    s = polars.Series("Q1", ["A"])
    q = Variable(s)

    class FakeStrategy:
        def __init__(self, *args, **kwargs):
            pass

        def get_sps(self, label: str):
            return "SPS"

    monkeypatch.setattr("survy.variable.variable._SelectStrategy", FakeStrategy)

    assert q.sps == "SPS"


def test_get_df_calls_strategy():
    s = polars.Series("Q1", ["A"])
    q = Variable(s)

    assert isinstance(q.get_df(), polars.DataFrame)


def test_get_df_select():
    s = polars.Series("Q1", ["A", "B", "C", "A"])
    q = Variable(s)

    assert_frame_equal(q.get_df("text"), polars.DataFrame({"Q1": ["A", "B", "C", "A"]}))
    assert_frame_equal(q.get_df("number"), polars.DataFrame({"Q1": [1, 2, 3, 1]}))


def test_get_df_select_null():
    s = polars.Series("Q1", ["A", "B", "C", "A", None])
    q = Variable(s)

    assert_frame_equal(
        q.get_df("text"), polars.DataFrame({"Q1": ["A", "B", "C", "A", None]})
    )
    assert_frame_equal(q.get_df("number"), polars.DataFrame({"Q1": [1, 2, 3, 1, None]}))


def test_get_df_number():
    s = polars.Series("Q1", [1, 2, 3, 4, 20])
    q = Variable(s)

    assert_frame_equal(q.get_df(), polars.DataFrame({"Q1": [1, 2, 3, 4, 20]}))


def test_get_df_null():
    s = polars.Series("Q1", [1, 2, 3, 4, 20, 0, None])
    q = Variable(s)

    assert_frame_equal(q.get_df(), polars.DataFrame({"Q1": [1, 2, 3, 4, 20, 0, None]}))


def test_get_df_multiselect():
    s = polars.Series("Q1", [["A", "B"], ["B"], ["B", "C"]])
    q = Variable(s)

    assert_frame_equal(
        q.get_df(dtype="compact"),
        polars.DataFrame({"Q1": [["A", "B"], ["B"], ["B", "C"]]}),
    )

    assert_frame_equal(
        q.get_df(dtype="text"),
        polars.DataFrame(
            {
                "Q1_1": ["A", None, None],
                "Q1_2": ["B", "B", "B"],
                "Q1_3": [None, None, "C"],
            }
        ),
    )

    assert_frame_equal(
        q.get_df(dtype="number"),
        polars.DataFrame(
            {"Q1_1": [1, 0, 0], "Q1_2": [1, 1, 1], "Q1_3": [0, 0, 1]},
            schema={"Q1_1": polars.Int8, "Q1_2": polars.Int8, "Q1_3": polars.Int8},
        ),
    )


def test_get_df_multiselect_null():
    s = polars.Series("Q1", [["A", "B"], ["B"], ["B", "C"], []])
    q = Variable(s)

    assert_frame_equal(
        q.get_df(dtype="compact"),
        polars.DataFrame({"Q1": [["A", "B"], ["B"], ["B", "C"], []]}),
    )

    assert_frame_equal(
        q.get_df(dtype="text"),
        polars.DataFrame(
            {
                "Q1_1": ["A", None, None, None],
                "Q1_2": ["B", "B", "B", None],
                "Q1_3": [None, None, "C", None],
            }
        ),
    )

    assert_frame_equal(
        q.get_df(dtype="number"),
        polars.DataFrame(
            {"Q1_1": [1, 0, 0, 0], "Q1_2": [1, 1, 1, 0], "Q1_3": [0, 0, 1, 0]},
            schema={"Q1_1": polars.Int8, "Q1_2": polars.Int8, "Q1_3": polars.Int8},
        ),
    )
