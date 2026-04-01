from typing import Literal
import warnings
import polars
from survy.separator import MULTISELECT
from survy.survey._utils import QuestionType
from survy.survey.strategies.base_strategy import BaseStrategy
from survy.utils.spss import mrset, value_labels, variable_labels, variable_level


class MultiSelectStrategy(BaseStrategy):
    def __init__(self, series: polars.Series, option_indices: dict[str, int]) -> None:
        self.series = series
        self.option_indices = option_indices

    def get_df(self, **kwargs) -> polars.DataFrame:
        dtype: Literal["number", "text"] = kwargs["dtype"]
        compact: bool = kwargs["compact"]
        id = self.series.name
        df = self.series.to_frame()

        if compact:
            return df

        if dtype == "number":
            number_df = df.with_columns(
                [
                    polars.col(id)
                    .list.contains(val)
                    .cast(polars.Int8)
                    .alias(f"{id}{MULTISELECT}{index}")
                    for val, index in self.option_indices.items()
                ]
            )
            return number_df.drop(id)
        else:
            text_df = df.with_columns(
                [
                    polars.col(id)
                    .list.contains(val)
                    .cast(polars.Int8)
                    .replace_strict({1: val}, default=None)
                    .alias(f"{id}{MULTISELECT}{index}")
                    for val, index in self.option_indices.items()
                ]
            )
            return text_df.drop(id)

    @property
    def sub_bases(self) -> dict[str, int]:
        id = self.series.name
        df = self.get_df(dtype="text", compact=True).explode(id)

        result = (
            df.filter(polars.col(id).is_not_null())
            .group_by(id)
            .agg(polars.col(id).count().alias("base"))
            .rename({id: "option"})
            .sort("option")
            .to_dicts()
        )

        return {item["option"]: item["base"] for item in result}

    def get_sps(self, label: str) -> str:
        id = self.series.name

        assert len(label) < 250
        label = label.replace("'", "").replace('"', "")

        var_label_str = variable_labels(
            QuestionType.MULTISELECT, id, label, self.option_indices
        )
        value_label_str = value_labels(
            QuestionType.MULTISELECT, id, self.option_indices
        )
        var_level_str = variable_level(
            QuestionType.MULTISELECT, id, "NOMINAL", self.option_indices
        )

        if len(self.option_indices) == 1:
            mrset_str = ""
            warnings.warn(f"{id} have only 1 key for option. Mrset will be None")
        else:
            mrset_str = mrset(id, label, self.option_indices)

        return "\n".join([var_label_str, value_label_str, var_level_str, mrset_str])
