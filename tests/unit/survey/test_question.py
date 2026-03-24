import pytest
import polars
from polars.testing import assert_frame_equal

from survy.errors import DataStructureError
from survy.survey._utils import QuestionType
from survy.survey.question import Question


@pytest.mark.parametrize(
    "data, dtype, qtype, mapping, text_data, number_data, sub_bases",
    [
        [
            ["a", "b", "c", "d", None],
            polars.String,
            QuestionType.SELECT,
            {"a": 1, "b": 2, "c": 3, "d": 4},
            ["a", "b", "c", "d", None],
            [1, 2, 3, 4, None],
            {"a": 1, "b": 1, "c": 1, "d": 1},
        ],
        [
            [["a", "b"], ["a", "b", "c"], ["b"], ["b", "c"]],
            polars.List,
            QuestionType.MULTISELECT,
            {"a": 1, "b": 2, "c": 3},
            [["a", "b"], ["a", "b", "c"], ["b"], ["b", "c"]],
            [["a", "b"], ["a", "b", "c"], ["b"], ["b", "c"]],
            {"a": 2, "b": 4, "c": 2},
        ],
        [
            [12, 24, 1, 2, None],
            polars.Int64,
            QuestionType.NUMBER,
            {},
            [12, 24, 1, 2, None],
            [12, 24, 1, 2, None],
            {1: 1, 2: 1, 12: 1, 24: 1},
        ],
    ],
)
def test_init_question(data, dtype, qtype, mapping, text_data, number_data, sub_bases):
    values = polars.Series("Q1", data)
    question = Question(
        label="Test Question",
        mapping=mapping,
        values=values,
    )

    assert question.id == "Q1"
    assert question.dtype == dtype
    assert question.qtype == qtype
    assert question.base == 4
    assert question.sub_bases == sub_bases
    assert question.to_dict() == {
        "id": "Q1",
        "label": "Test Question",
        "mapping": mapping,
        "values": data,
    }

    assert_frame_equal(
        question.get_df(dtype="text"),
        polars.DataFrame({"Q1": text_data}),
    )

    assert_frame_equal(
        question.get_df(dtype="number"),
        polars.DataFrame({"Q1": number_data}),
    )


@pytest.mark.parametrize(
    "data, mapping, new_label, new_mapping, correct_label, correct_mapping",
    [
        [
            ["a", "b", "c", "d", None],
            {"a": 1, "b": 2, "c": 3, "d": 4},
            "New question",
            {"a": 2, "b": 1, "c": 3, "d": 4},
            "New question",
            {"a": 2, "b": 1, "c": 3, "d": 4},
        ],
        [
            ["a", "b", "c", "d", None],
            {"a": 1, "b": 2, "c": 3, "d": 4},
            "",
            {"a": 2, "b": 1, "c": 3, "d": 4, "e": 5},
            "Question 1",
            {"a": 2, "b": 1, "c": 3, "d": 4, "e": 5},
        ],
        [
            [["a", "b"], ["a", "b", "c"], ["b"], ["b", "c"]],
            {"a": 1, "b": 2, "c": 3},
            "New question",
            {"a": 2, "b": 1, "c": 3},
            "New question",
            {"a": 2, "b": 1, "c": 3},
        ],
    ],
)
def test_update_question_valid(
    data, mapping, new_label, new_mapping, correct_label, correct_mapping
):
    question = Question(
        label="Question 1", mapping=mapping, values=polars.Series("Q1", data)
    )
    question.update(new_label, new_mapping)
    assert question.label == correct_label
    assert question.mapping == correct_mapping


@pytest.mark.parametrize(
    "data, mapping, new_mapping",
    [
        [
            ["a", "b", "c", "d", None],
            {"a": 1, "b": 2, "c": 3, "d": 4},
            {"a": 2, "b": 1},
        ],
        [
            [["a", "b"], ["a", "b", "c"], ["b"], ["b", "c"]],
            {"a": 1, "b": 2, "c": 3},
            {"a": 2, "b": 1},
        ],
    ],
)
def test_update_question_invalid(data, mapping, new_mapping):
    question = Question(
        label="Question 1", mapping=mapping, values=polars.Series("Q1", data)
    )
    with pytest.raises(DataStructureError):
        question.update("", new_mapping)
