import polars

from survy.survey.survey import Survey


def test_survey():
    df = polars.DataFrame(
        {
            "Q1": ["a", "b", "c", "a", "a"],
            "Q2": [["x", "y", "z"], ["x", "y"], ["x"], ["y", "z"], ["z"]],
            "Q3": [10, 12, 13, 14, 20],
            "Q4": ["abc", "def", "xyz", "ghy", "czxc"],
        }
    )

    survey = Survey(df=df)

    assert survey.to_dict() == [
        {
            "id": "Q1",
            "label": "Q1",
            "mapping": {"a": 1, "b": 2, "c": 3},
            "values": ["a", "b", "c", "a", "a"],
        },
        {
            "id": "Q2",
            "label": "Q2",
            "mapping": {"x": 1, "y": 2, "z": 3},
            "values": [["x", "y", "z"], ["x", "y"], ["x"], ["y", "z"], ["z"]],
        },
        {"id": "Q3", "label": "Q3", "mapping": {}, "values": [10, 12, 13, 14, 20]},
        {
            "id": "Q4",
            "label": "Q4",
            "mapping": {"abc": 1, "czxc": 2, "def": 3, "ghy": 4, "xyz": 5},
            "values": ["abc", "def", "xyz", "ghy", "czxc"],
        },
    ]
