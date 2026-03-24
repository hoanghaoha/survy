import polars as pl
from typing import Any, Iterable

from survy.separator import MATRIX
from survy.utils.parse_id import parse_id


def process_raw_df(
    raw_data: dict[str, list[Any]], name_pattern: str = "id(.matrix)?(_multi)?"
) -> pl.DataFrame:
    def _process_list(li: Iterable):
        return sorted([i for i in li if i])

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

    return pl.DataFrame(results)
