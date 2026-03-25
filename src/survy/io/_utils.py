import polars
from typing import Iterable

from survy.separator import MATRIX
from survy.survey.question import Question
from survy.utils.functions import extract_mapping
from survy.utils.parse_id import parse_id


def process_polars_df(df: polars.DataFrame, name_pattern: str) -> list[Question]:
    def _process_list(li: Iterable):
        return sorted([i for i in li if i])

    def _process_series(series: polars.Series) -> Question:
        mapping = (
            {}
            if series.dtype.is_numeric() or series.dtype == polars.Datetime
            else extract_mapping(series.to_list())
        )
        values = series.replace({"": None}) if series.dtype == polars.String else series
        question = Question(
            label=series.name,
            values=values,
            mapping=mapping,
        )
        return question

    raw_data = df.to_dict(as_series=False)

    results = {}
    multiselect_qids = set()

    for name, data in raw_data.items():
        parsed_items = parse_id(name, name_pattern)
        qid = parsed_items["id"]
        matrix_id = parsed_items.get("matrix")
        multi_id = parsed_items.get("multi")

        if matrix_id:
            qid = f"{qid}{MATRIX}{matrix_id}"

        if multi_id:
            multiselect_qids.add(qid)
            results.setdefault(qid, [])
            results[qid].append(data)
        else:
            results[qid] = data

    for qid, data in results.items():
        if qid in multiselect_qids:
            results[qid] = [_process_list(d) for d in zip(*data)]

    df = polars.DataFrame(results)

    return [_process_series(df[col]) for col in df.columns]
