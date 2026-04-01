from typing import Literal
import polars
from survy.survey.strategies.base_strategy import BaseStrategy


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
