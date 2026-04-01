from typing import Literal
import polars
from survy.survey._utils import QuestionType
from survy.survey.strategies.base_strategy import BaseStrategy
from survy.utils.spss import value_labels, variable_labels, variable_level


class SelectStrategy(BaseStrategy):
    def __init__(self, series: polars.Series, option_indices: dict[str, int]) -> None:
        self.series = series
        self.option_indices = option_indices

    def get_df(self, **kwargs) -> polars.DataFrame:
        dtype: Literal["number", "text"] = kwargs["dtype"]

        if dtype == "number":
            return self.series.replace_strict(
                self.option_indices, default=None
            ).to_frame()

        return self.series.to_frame()

    @property
    def sub_bases(self) -> dict[str, int]:
        df = self.get_df(dtype="text")
        id = self.series.name

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
            QuestionType.SELECT, id, label, self.option_indices
        )
        value_label_str = value_labels(QuestionType.SELECT, id, self.option_indices)
        var_level_str = variable_level(
            QuestionType.SELECT, id, "NOMINAL", self.option_indices
        )

        return "\n".join([var_label_str, value_label_str, var_level_str])
