import pytest
import polars

from survy.analyze.crosstab.functions import crosstab
from survy.variable.variable import Variable


@pytest.fixture
def sample_data():
    v_select = Variable(polars.Series("Q1", ["a", "b", "a", "a", "b", "a"]))

    v_numeric = Variable(polars.Series("Q2", [20, 30, 40, 23, 21, 304]))

    v_multi = Variable(
        polars.Series(
            "Q3",
            [
                ["d", "e"],
                ["a", "b", "d"],
                ["a", "d", "e"],
                ["a", "b", "c", "d", "e"],
                ["a", "e"],
                ["b", "c"],
            ],
        )
    )

    v_filter = Variable(polars.Series("F", ["X", "X", "Y", "Y", "X", "Y"]))

    return v_select, v_numeric, v_multi, v_filter


def test_crosstab_count_basic(sample_data):
    col, _, _, _ = sample_data

    result = crosstab(col, col, aggfunc="count")

    assert isinstance(result, dict)
    assert "Total" in result
    assert isinstance(result["Total"], polars.DataFrame)


def test_crosstab_percent_basic(sample_data):
    col, _, _, _ = sample_data

    result = crosstab(col, col, aggfunc="percent")

    assert "Total" in result
    assert isinstance(result["Total"], polars.DataFrame)


def test_crosstab_mean_basic(sample_data):
    col, num, _, _ = sample_data

    result = crosstab(col, num, aggfunc="mean")

    assert "Total" in result
    assert isinstance(result["Total"], polars.DataFrame)


def test_crosstab_with_filter(sample_data):
    col, _, _, flt = sample_data

    result = crosstab(col, col, filter=flt, aggfunc="count")

    assert isinstance(result, dict)
    assert set(result.keys()) == set(flt.value_indices.keys())


def test_crosstab_multiselect_column(sample_data):
    _, _, multi, _ = sample_data

    result = crosstab(multi, multi, aggfunc="count")

    assert "Total" in result
    assert isinstance(result["Total"], polars.DataFrame)


def test_crosstab_multiselect_row(sample_data):
    col, _, multi, _ = sample_data

    result = crosstab(col, multi, aggfunc="count")

    assert "Total" in result
    assert isinstance(result["Total"], polars.DataFrame)


def test_crosstab_numeric_with_filter(sample_data):
    col, num, _, flt = sample_data

    result = crosstab(col, num, filter=flt, aggfunc="mean")

    assert isinstance(result, dict)
    assert len(result) > 0
    for df in result.values():
        assert isinstance(df, polars.DataFrame)


def test_crosstab_invalid_filter(sample_data):
    col, num, _, _ = sample_data

    with pytest.raises(Exception):
        crosstab(col, col, filter=num, aggfunc="count")
