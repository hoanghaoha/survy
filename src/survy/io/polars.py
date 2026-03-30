from typing import Iterable
import polars

from survy.separator import MATRIX
from survy.survey.question import Question
from survy.survey.survey import Survey
from survy.utils.parse_id import parse_id


def read_polars(
    df: polars.DataFrame,
    multiselects_as_single_column: list[str] = [],
    multiselect_separator: str = ";",
    name_pattern: str = "id(.matrix)?(_multi)?",
) -> Survey:
    def _process_list(li: Iterable):
        return sorted([i for i in li if i])

    def _process_series(series: polars.Series) -> Question:
        series = series.replace({"": None}) if series.dtype == polars.String else series
        question = Question(
            series=series,
        )
        return question

    raw_data = df.to_dict(as_series=False)

    results = {}
    multiselect_qids = set()

    for name, data in raw_data.items():
        if name in multiselects_as_single_column:
            qid = name
            results[qid] = [
                _process_list(d.split(multiselect_separator)) if d else [] for d in data
            ]
        else:
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

    processed_df = polars.DataFrame(results)
    processed_df = processed_df.select(
        [c for c in processed_df.columns if processed_df[c].dtype != polars.Null]
    )

    questions = [_process_series(processed_df[col]) for col in processed_df.columns]

    return Survey(questions=questions)
