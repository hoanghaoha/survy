import pytest
import polars
from polars.testing import assert_frame_equal
import warnings

from survy.survey.question import Question
from survy.errors import DataStructureError, QuestionTypeError
from survy.survey._utils import QuestionType


# -------------------------
# Basic properties
# -------------------------


def test_question_id():
    s = polars.Series("Q1", ["A", "B"])
    q = Question(s)

    assert q.id == "Q1"


def test_len_property():
    s = polars.Series("Q1", ["A", "B", None])
    q = Question(s)

    assert q.len == 3


def test_base_counts_non_empty():
    s = polars.Series("Q1", ["A", "", None, "B"])
    q = Question(s)

    assert q.base == 2


# -------------------------
# qtype inference
# -------------------------


def test_qtype_select():
    s = polars.Series("Q1", ["A", "B"])
    q = Question(s)

    assert q.qtype == QuestionType.SELECT


def test_qtype_number():
    s = polars.Series("Q1", [1, 2, 3])
    q = Question(s)

    assert q.qtype == QuestionType.NUMBER


def test_qtype_multiselect():
    s = polars.Series("Q1", [["A", "B"], ["B"]])
    q = Question(s)

    assert q.qtype == QuestionType.MULTISELECT


def test_qtype_fallback_to_select_with_warning():
    s = polars.Series("Q1", [True, False])

    with warnings.catch_warnings(record=True) as w:
        q = Question(s)
        assert q.qtype == QuestionType.SELECT
        assert len(w) > 0


def test_qtype_error_on_invalid_cast(monkeypatch):
    s = polars.Series("Q1", [object()])

    def broken_cast(*args, **kwargs):
        raise Exception("fail")

    monkeypatch.setattr(s, "cast", broken_cast)

    with pytest.raises(QuestionTypeError):
        Question(s).qtype


# -------------------------
# label logic
# -------------------------


def test_label_default():
    s = polars.Series("Q1", ["A"])
    q = Question(s)

    assert q.label == "Q1"


def test_label_custom():
    s = polars.Series("Q1", ["A"])
    q = Question(s)
    q.label = "Custom"

    assert q.label == "Custom"


def test_label_with_loop():
    s = polars.Series("Q1", ["A"])
    q = Question(s)
    q.loop_id = "L1"

    assert q.label.startswith("[L1]")


def test_label_truncation_warning():
    s = polars.Series("Q1", ["A"])
    q = Question(s)
    q.label = "x" * 300

    with warnings.catch_warnings(record=True) as w:
        label = q.label
        assert len(label) == 249
        assert len(w) == 1


# -------------------------
# option_indices
# -------------------------


def test_option_indices_auto():
    s = polars.Series("Q1", ["A", "B", "A"])
    q = Question(s)

    mapping = q.option_indices

    assert set(mapping.keys()) == {"A", "B"}


def test_option_indices_numeric_empty():
    s = polars.Series("Q1", [1, 2, 3])
    q = Question(s)

    assert q.option_indices == {}


def test_option_indices_set_valid():
    s = polars.Series("Q1", ["A", "B"])
    q = Question(s)

    q.option_indices = {"A": 1, "B": 2}

    assert q.option_indices == {"A": 1, "B": 2}


def test_option_indices_set_invalid():
    s = polars.Series("Q1", ["A", "B"])
    q = Question(s)

    with pytest.raises(DataStructureError):
        q.option_indices = {"A": 1}


# -------------------------
# strategy selection
# -------------------------


def test_strategy_select():
    s = polars.Series("Q1", ["A", "B"])
    q = Question(s)

    assert q.strategy.__class__.__name__ == "SelectStrategy"


def test_strategy_number():
    s = polars.Series("Q1", [1, 2])
    q = Question(s)

    assert q.strategy.__class__.__name__ == "NumberStrategy"


def test_strategy_multiselect():
    s = polars.Series("Q1", [["A"], ["B"]])
    q = Question(s)

    assert q.strategy.__class__.__name__ == "MultiSelectStrategy"


# -------------------------
# to_dict
# -------------------------


def test_to_dict():
    s = polars.Series("Q1", ["A", "B"])
    q = Question(s)

    d = q.to_dict()

    assert d["id"] == "Q1"
    assert "values" in d
    assert "qtype" in d


# -------------------------
# delegation (strategy methods)
# -------------------------
#


def test_sub_bases_select():
    s = polars.Series("Q1", ["A", "B", "B"])
    q = Question(s)

    assert q.sub_bases == {"A": 1, "B": 2}


def test_sps_calls_strategy(monkeypatch):
    s = polars.Series("Q1", ["A"])
    q = Question(s)

    class FakeStrategy:
        def __init__(self, *args, **kwargs):
            pass

        def get_sps(self, label: str):
            return "SPS"

    monkeypatch.setattr("survy.survey.question.SelectStrategy", FakeStrategy)

    assert q.sps == "SPS"


def test_get_df_calls_strategy():
    s = polars.Series("Q1", ["A"])
    q = Question(s)

    assert isinstance(q.get_df(), polars.DataFrame)


# -------------------------
# DataFrame
# -------------------------


def test_get_df_select():
    s = polars.Series("Q1", ["A", "B", "C", "A"])
    q = Question(s)

    assert_frame_equal(q.get_df("text"), polars.DataFrame({"Q1": ["A", "B", "C", "A"]}))
    assert_frame_equal(q.get_df("number"), polars.DataFrame({"Q1": [1, 2, 3, 1]}))


def test_get_df_select_null():
    s = polars.Series("Q1", ["A", "B", "C", "A", None])
    q = Question(s)

    assert_frame_equal(
        q.get_df("text"), polars.DataFrame({"Q1": ["A", "B", "C", "A", None]})
    )
    assert_frame_equal(q.get_df("number"), polars.DataFrame({"Q1": [1, 2, 3, 1, None]}))


def test_get_df_number():
    s = polars.Series("Q1", [1, 2, 3, 4, 20])
    q = Question(s)

    assert_frame_equal(q.get_df(), polars.DataFrame({"Q1": [1, 2, 3, 4, 20]}))


def test_get_df_null():
    s = polars.Series("Q1", [1, 2, 3, 4, 20, 0, None])
    q = Question(s)

    assert_frame_equal(q.get_df(), polars.DataFrame({"Q1": [1, 2, 3, 4, 20, 0, None]}))


def test_get_df_multiselect():
    s = polars.Series("Q1", [["A", "B"], ["B"], ["B", "C"]])
    q = Question(s)

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
    q = Question(s)

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
