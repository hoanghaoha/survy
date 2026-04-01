from typing import Literal
import polars
from survy.separator import MULTISELECT
from survy.survey.strategies.base_strategy import BaseStrategy


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
