import polars

from survy.io._utils import process_polars_df
from survy.survey.survey import Survey


def read_polars(
    df: polars.DataFrame, name_pattern: str = "id(.matrix)?(_multi)?"
) -> Survey:
    return Survey(questions=process_polars_df(df, name_pattern))
