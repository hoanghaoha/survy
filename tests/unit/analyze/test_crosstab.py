import polars
from survy.survey.question import Question
from survy.survey.survey import Survey


df = polars.DataFrame(
    {
        "Q1": ["a", "b", "c", "a", "a", "a", "a", "b"],
        "Q2": [
            ["x", "y", "z"],
            ["x", "y"],
            ["x"],
            ["y", "z"],
            ["z"],
            ["x", "y", "z"],
            ["x", "y", "z"],
            ["x", "y", "z"],
        ],
        "Q3": [10, 12, 13, 14, 20, 1234, 314, 132],
        "Q4": ["ab", "cd", "ef", "ab", "ac", "ae", "ab", "ab"],
    }
)


def test_crosstab_category():
    q1 = Question(
        label="Q1",
        mapping={"a": 1, "b": 2, "c": 3},
        values=polars.Series(
            "Q1",
            ["a", "b", "c", "a", "a", "a", "a", "b"],
        ),
    )
    q2 = Question(
        label="Q3",
        mapping={"x": 1, "y": 2, "z": 3},
        values=polars.Series(
            "Q2",
            [
                ["x", "y", "z"],
                ["x", "y"],
                ["x"],
                ["y", "z"],
                ["z"],
                ["x", "y", "z"],
                ["x", "y", "z"],
                ["x", "y", "z"],
            ],
        ),
    )
    q3 = Question(
        label="Q3",
        mapping={"d": 1, "e": 2, "f": 3},
        values=polars.Series(
            "Q3",
            ["d", "e", "d", "e", "d", "f", "f", "f"],
        ),
    )
    survey = Survey(questions=[q1, q2, q3])

    # placeholder
    assert survey
