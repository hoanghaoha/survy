from typing import Literal
import polars
from polars.testing import assert_frame_equal
import pytest
from pathlib import Path
from survy import read_csv
import survy
from survy.analyze.crosstab._utils import AggFunc
from survy.survey.survey import Survey
from survy.variable._utils import VarType
from survy.variable.variable import Variable
from survy.errors import DataStructureError, VarTypeError
# import survy
# from survy.analyze.crosstab._utils import AggFunc
# from survy.errors import DataStructureError, VarTypeError

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def survey() -> Survey:
    return read_csv(
        FIXTURES / "test_data_01_compact.csv", compact_ids=["Q2", "Q5/1", "Q5/2"]
    )


@pytest.fixture
def survey_normal() -> Survey:
    return read_csv(FIXTURES / "test_data_01_normal.csv")


def test_similar_survey(survey: Survey, survey_normal: Survey):
    assert_frame_equal(survey.get_df(), survey_normal.get_df())


def test_survey(survey: Survey):
    assert len(survey.variables) == 7
    assert isinstance(survey.sps, str)


def test_survey_update(survey: Survey):
    survey.update(
        [{"id": "Q1", "label": "Gender", "value_indices": {"Male": 1, "Female": 2}}]
    )
    assert survey["Q1"].label == "Gender"


def test_survey_update_error(survey: Survey):
    with pytest.raises(DataStructureError):
        survey.update([{"id": "Q1", "label": "Gender", "value_indices": {"Male": 1}}])


@pytest.mark.parametrize("id", ["Q1", "Q2", "Q3", "Q4/1", "Q4/2", "Q5/1", "Q5/2"])
def test_survey_variables(survey: Survey, id: str):
    var_ids = [var.id for var in survey.variables]
    assert id in var_ids

    assert isinstance(survey[id], Variable)
    assert isinstance(survey[id].series, polars.Series)
    assert isinstance(survey[id].id, str)
    assert isinstance(survey[id].label, str)
    assert isinstance(survey[id].value_indices, dict)
    assert isinstance(survey[id].vtype, VarType)
    assert isinstance(survey[id].base, int)


@pytest.mark.parametrize(
    "select_dtype, multiselect_dtype",
    [
        ["text", "text"],
        ["text", "number"],
        ["text", "compact"],
        ["number", "text"],
        ["number", "number"],
        ["number", "compact"],
    ],
)
def test_survey_df(
    survey: Survey,
    select_dtype: Literal["text", "number"],
    multiselect_dtype: Literal["text", "number", "compact"],
):
    df = survey.get_df(select_dtype, multiselect_dtype)

    assert df.height == 100

    if multiselect_dtype == "compact":
        assert df.width == 7
    else:
        assert df.width == 11


@pytest.mark.parametrize("aggfunc", ["count", "percent", "mean"])
@pytest.mark.parametrize("column_id", ["Q1", "Q2", "Q4/1", "Q4/2", "Q5/1", "Q5/2"])
@pytest.mark.parametrize("row_id", ["Q1", "Q2", "Q3", "Q4/1", "Q4/2", "Q5/1", "Q5/2"])
def test_crosstab_no_filter(
    survey: Survey,
    aggfunc: AggFunc,
    column_id: str,
    row_id: str,
):
    result = survy.crosstab(survey[column_id], survey[row_id], None, aggfunc)
    assert isinstance(result, dict)
    assert "Total" in result.keys()
    assert result["Total"].height > 0
    assert result["Total"].width > 0


@pytest.mark.parametrize("aggfunc", ["count", "percent", "mean"])
@pytest.mark.parametrize("column_id", ["Q1", "Q2"])
@pytest.mark.parametrize("row_id", ["Q1", "Q2", "Q3"])
@pytest.mark.parametrize("filter_id", ["Q1", "Q2", "Q4/1", "Q5/2"])
def test_crosstab_with_filter(
    survey: Survey, aggfunc: AggFunc, column_id: str, row_id: str, filter_id: str
):
    crosstab = survy.crosstab(
        survey[column_id], survey[row_id], survey[filter_id], aggfunc
    )
    for key in survey[filter_id].value_indices.keys():
        assert key in crosstab
        assert crosstab[key].height > 0
        assert crosstab[key].width > 0


@pytest.mark.parametrize("aggfunc", ["count", "percent", "mean"])
@pytest.mark.parametrize("column_id", ["Q1", "Q2", "Q4/1", "Q5/2"])
@pytest.mark.parametrize("row_id", ["Q1", "Q2", "Q3"])
def test_crosstab_error(survey: Survey, aggfunc: AggFunc, column_id: str, row_id: str):
    with pytest.raises(VarTypeError):
        assert survy.crosstab(
            survey[column_id],
            survey[row_id],
            survey["Q3"],
            aggfunc,
        )


def test_survey_export_csv(survey: Survey, tmp_path: Path):
    survey.to_csv(tmp_path, "test_survey")

    assert (tmp_path / "test_survey_data.csv").exists()
    assert (tmp_path / "test_survey_variables_info.csv").exists()
    assert (tmp_path / "test_survey_values_info.csv").exists()


def test_survey_export_json(survey: Survey, tmp_path: Path):
    survey.to_json(tmp_path, "test_survey")

    assert (tmp_path / "test_survey.json").exists()


def test_survey_export_spss(survey: Survey, tmp_path: Path):
    for var in survey.variables:
        var.series = var.series.rename(var.series.name.replace("/", "."))

    survey.to_spss(tmp_path, "test_survey")

    assert (tmp_path / "test_survey_data.sav").exists()
    assert (tmp_path / "test_survey_syntax.sps").exists()
