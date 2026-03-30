import polars
from survy.analyze.crosstab import crosstab
from survy.survey.question import Question
from survy.survey.survey import Survey


def test_crosstab_category():
    q1 = Question(
        series=polars.Series(
            "Q1",
            ["a", "b", "c", "a", "a", "a", "a", "b"],
        ),
    )
    q2 = Question(
        series=polars.Series(
            "Q2",
            [
                ["x", "y", "z"],
                ["x", "y"],
                ["x"],
                ["y", "z"],
                ["y", "z"],
                ["x", "y", "z"],
                ["x", "y", "z"],
                ["y", "z"],
            ],
        ),
    )
    q3 = Question(
        series=polars.Series(
            "Q3",
            ["d", "e", "d", "e", "d", "f", "f", "f"],
        ),
    )
    q4 = Question(
        series=polars.Series(
            "Q4",
            [
                ["g", "h", "y"],
                ["h", "y"],
                ["g", "y"],
                ["g", "h"],
                ["g"],
                ["g", "h", "y"],
                ["g", "h", "y"],
                ["y"],
            ],
        ),
    )
    survey = Survey(questions=[q1, q2, q3, q4])

    # select vs multiselect
    assert crosstab(survey["Q1"], survey["Q2"], as_percent=False)
    assert crosstab(survey["Q1"], survey["Q2"], as_percent=True)
    assert crosstab(survey["Q1"], survey["Q2"], as_percent=False, sig_level=0.05)
    assert crosstab(survey["Q1"], survey["Q2"], as_percent=True, sig_level=0.05)
    assert crosstab(survey["Q1"], survey["Q2"], as_num=True)

    # select vs multiselect, filter by select
    assert crosstab(survey["Q1"], survey["Q2"], survey["Q3"], as_percent=False)
    assert crosstab(survey["Q1"], survey["Q2"], survey["Q3"], as_percent=True)
    assert crosstab(
        survey["Q1"], survey["Q2"], survey["Q3"], as_percent=False, sig_level=0.05
    )
    assert crosstab(
        survey["Q1"], survey["Q2"], survey["Q3"], as_percent=True, sig_level=0.05
    )
    assert crosstab(survey["Q1"], survey["Q2"], survey["Q3"], as_num=True)

    # select vs multiselect, filter by multiselect
    assert crosstab(survey["Q1"], survey["Q2"], survey["Q3"], as_percent=False)
    assert crosstab(survey["Q1"], survey["Q2"], survey["Q3"], as_percent=True)
    assert crosstab(
        survey["Q1"], survey["Q2"], survey["Q3"], as_percent=False, sig_level=0.05
    )
    assert crosstab(
        survey["Q1"], survey["Q2"], survey["Q3"], as_percent=True, sig_level=0.05
    )
    assert crosstab(survey["Q1"], survey["Q2"], survey["Q3"], as_num=True)

    # select vs select
    assert crosstab(survey["Q1"], survey["Q3"], as_percent=False)
    assert crosstab(survey["Q1"], survey["Q3"], as_percent=True)
    assert crosstab(survey["Q1"], survey["Q3"], as_percent=False, sig_level=0.05)
    assert crosstab(survey["Q1"], survey["Q3"], as_percent=True, sig_level=0.05)
    assert crosstab(survey["Q1"], survey["Q3"], as_num=True)

    # select vs select, filter by select
    assert crosstab(survey["Q1"], survey["Q3"], survey["Q3"], as_percent=False)
    assert crosstab(survey["Q1"], survey["Q3"], survey["Q3"], as_percent=True)
    assert crosstab(
        survey["Q1"], survey["Q3"], survey["Q3"], as_percent=False, sig_level=0.05
    )
    assert crosstab(
        survey["Q1"], survey["Q3"], survey["Q3"], as_percent=True, sig_level=0.05
    )
    assert crosstab(survey["Q1"], survey["Q3"], survey["Q3"], as_num=True)

    # select vs select, filter by multiselect
    assert crosstab(survey["Q1"], survey["Q3"], survey["Q2"], as_percent=False)
    assert crosstab(survey["Q1"], survey["Q3"], survey["Q2"], as_percent=True)
    assert crosstab(
        survey["Q1"], survey["Q3"], survey["Q2"], as_percent=False, sig_level=0.05
    )
    assert crosstab(
        survey["Q1"], survey["Q3"], survey["Q2"], as_percent=True, sig_level=0.05
    )
    assert crosstab(survey["Q1"], survey["Q3"], survey["Q2"], as_num=True)

    # multiselect vs multiselect
    assert crosstab(survey["Q2"], survey["Q4"], as_percent=False)
    assert crosstab(survey["Q2"], survey["Q4"], as_percent=True)
    assert crosstab(survey["Q2"], survey["Q4"], as_percent=False, sig_level=0.05)
    assert crosstab(survey["Q2"], survey["Q4"], as_percent=True, sig_level=0.05)
    assert crosstab(survey["Q2"], survey["Q4"], as_num=True)

    # multiselect vs multiselect, filter by select
    assert crosstab(survey["Q2"], survey["Q4"], survey["Q1"], as_percent=False)
    assert crosstab(survey["Q2"], survey["Q4"], survey["Q1"], as_percent=True)
    assert crosstab(
        survey["Q2"], survey["Q4"], survey["Q1"], as_percent=False, sig_level=0.05
    )
    assert crosstab(
        survey["Q2"], survey["Q4"], survey["Q1"], as_percent=True, sig_level=0.05
    )
    assert crosstab(survey["Q2"], survey["Q4"], survey["Q1"], as_num=True)

    # multiselect vs multiselect, filter by multiselect
    assert crosstab(survey["Q2"], survey["Q4"], survey["Q2"], as_percent=False)
    assert crosstab(survey["Q2"], survey["Q4"], survey["Q2"], as_percent=True)
    assert crosstab(
        survey["Q2"], survey["Q4"], survey["Q2"], as_percent=False, sig_level=0.05
    )
    assert crosstab(
        survey["Q2"], survey["Q4"], survey["Q2"], as_percent=True, sig_level=0.05
    )
    assert crosstab(survey["Q2"], survey["Q4"], survey["Q2"], as_num=True)


def test_crosstab_num():
    q1 = Question(
        series=polars.Series(
            "Q1",
            ["a", "b", "c", "a", "a", "a", "a", "b"],
        ),
    )
    q2 = Question(
        series=polars.Series(
            "Q2",
            [
                ["x", "y", "z"],
                ["x", "y"],
                ["x"],
                ["y", "z"],
                ["y", "z"],
                ["x", "y", "z"],
                ["x", "y", "z"],
                ["y", "z"],
            ],
        ),
    )
    q3 = Question(
        series=polars.Series(
            "Q3",
            [124, 3, 313, 39, 4924, 4949, 23, 22],
        ),
    )
    survey = Survey(questions=[q1, q2, q3])

    # select vs number, filter by select
    assert crosstab(survey["Q1"], survey["Q3"], survey["Q1"], as_percent=False)
    assert crosstab(survey["Q1"], survey["Q3"], survey["Q1"], as_percent=True)
    assert crosstab(survey["Q1"], survey["Q3"], survey["Q1"], as_num=True)

    # select vs number, filter by multiselect
    assert crosstab(survey["Q1"], survey["Q3"], survey["Q2"], as_percent=False)
    assert crosstab(survey["Q1"], survey["Q3"], survey["Q2"], as_percent=True)
    assert crosstab(survey["Q1"], survey["Q3"], survey["Q2"], as_num=True)

    # multiselect vs number, filter by select
    assert crosstab(survey["Q2"], survey["Q3"], survey["Q1"], as_percent=False)
    assert crosstab(survey["Q2"], survey["Q3"], survey["Q1"], as_percent=True)
    assert crosstab(survey["Q2"], survey["Q3"], survey["Q1"], as_num=True)

    # multiselect vs number, filter by multiselect
    assert crosstab(survey["Q2"], survey["Q3"], survey["Q2"], as_percent=False)
    assert crosstab(survey["Q2"], survey["Q3"], survey["Q2"], as_percent=True)
    assert crosstab(survey["Q2"], survey["Q3"], survey["Q2"], as_num=True)
