import polars
from survy.survey.strategies.base_strategy import BaseStrategy


class NumberStrategy(BaseStrategy):
    def __init__(self, series: polars.Series, option_indices: dict[str, int]) -> None:
        self.series = series
        self.option_indices = option_indices

    def get_df(self, **kwargs) -> polars.DataFrame:
        df = self.series.to_frame()
        return df

    @property
    def sub_bases(self) -> dict[str, int]:
        id = self.series.name
        df = self.get_df()

        result = (
            df.filter(polars.col(id).is_not_null())
            .group_by(id)
            .agg(polars.col(id).count().alias("base"))
            .rename({id: "option"})
            .sort("option")
            .to_dicts()
        )

        return {item["option"]: item["base"] for item in result}
