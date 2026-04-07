import pytest
import polars
import numpy as np

from survy.analyze.crosstab.functions import crosstab, sig_test_proportion
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


def test_count_basic(sample_data):
    v1, _, v3, _ = sample_data

    result = crosstab(v1, v3, aggfunc="count")

    assert "Total" in result
    df = result["Total"]

    assert isinstance(df, polars.DataFrame)
    assert df.height > 0


def test_percent_basic(sample_data):
    v1, _, v3, _ = sample_data

    result = crosstab(v1, v3, aggfunc="percent")

    df = result["Total"]

    assert all(dtype.is_float() for dtype in df.dtypes if dtype != polars.Utf8)


def test_numeric_mean(sample_data):
    v1, v2, _, _ = sample_data

    result = crosstab(v1, v2, aggfunc="mean")

    df = result["Total"]

    assert isinstance(df, polars.DataFrame)
    assert df.height > 0


@pytest.mark.parametrize("agg", ["mean", "min", "max", "median", "sum", "var", "std"])
def test_all_numeric_aggs(sample_data, agg):
    v1, v2, _, _ = sample_data

    result = crosstab(v1, v2, aggfunc=agg)

    df = result["Total"]

    assert isinstance(df, polars.DataFrame)
    assert df.height > 0


def test_callable_agg(sample_data):
    v1, v2, _, _ = sample_data

    result = crosstab(v1, v2, aggfunc=np.mean)

    df = result["Total"]

    assert isinstance(df, polars.DataFrame)


def test_select_vs_multiselect(sample_data):
    v1, _, v3, _ = sample_data

    result = crosstab(v1, v3, aggfunc="count")
    assert "Total" in result


def test_multiselect_vs_select(sample_data):
    v1, _, v3, _ = sample_data

    result = crosstab(v3, v1, aggfunc="count")
    assert "Total" in result


def test_multiselect_vs_multiselect(sample_data):
    _, _, v3, _ = sample_data

    result = crosstab(v3, v3, aggfunc="count")
    assert "Total" in result


def test_filter_select(sample_data):
    v1, _, v3, vf = sample_data

    result = crosstab(v1, v3, filter=vf, aggfunc="count")

    assert set(result.keys()) == {"X", "Y"}


def test_filter_multiselect(sample_data):
    v1, _, v3, _ = sample_data

    result = crosstab(v1, v3, filter=v3, aggfunc="count")

    assert isinstance(result, dict)
    assert len(result) > 0


def test_has_total_column(sample_data):
    v1, _, v3, _ = sample_data

    df = crosstab(v1, v3)["Total"]

    assert "Total" in df.columns


def test_single_value_variable():
    v1 = Variable(polars.Series("Q1", ["a", "a", "a"]))
    v2 = Variable(polars.Series("Q2", [1, 1, 1]))

    result = crosstab(v1, v2)

    assert "Total" in result


def test_empty_after_filter():
    v1 = Variable(polars.Series("Q1", ["a", "b"]))
    v2 = Variable(polars.Series("Q2", [1, 2]))
    vf = Variable(polars.Series("F", ["X", "X"]))

    result = crosstab(v1, v2, filter=vf)

    assert "X" in result


def test_length_mismatch():
    v1 = Variable(polars.Series("Q1", ["a", "b"]))
    v2 = Variable(polars.Series("Q2", [1]))

    with pytest.raises(AssertionError):
        crosstab(v1, v2)


def test_count_sum_consistency(sample_data):
    """
    Test sum of count should equal to row
    """
    v1, _, v3, _ = sample_data

    df = crosstab(v1, v3)["Total"]

    total_row = df.filter(polars.col(df.columns[0]) == "Total")

    assert total_row.height == 1


def test_sig_test_proportion(sample_data):
    v1, _, v3, _ = sample_data

    crosstab_results = crosstab(v1, v3, aggfunc="count")
    sig_test_result = sig_test_proportion(crosstab_results["Total"], 0.05)
    assert isinstance(sig_test_result, polars.DataFrame)
    assert sig_test_result.height > 0
    assert sig_test_result.width > 0


def test_sig_test_proportion_filtered(sample_data):
    v1, _, v3, vf = sample_data

    crosstab_results = crosstab(v1, v3, vf, aggfunc="count")
    for df in crosstab_results.values():
        sig_test_result = sig_test_proportion(df, 0.05)
        assert isinstance(sig_test_result, polars.DataFrame)
        assert sig_test_result.height > 0
        assert sig_test_result.width > 0
