import polars as pl
from typing import Any, Iterable

from survy.separator import MULTISELECT


def process_raw_data(raw_data: dict[str, list[Any]]) -> pl.DataFrame:
    def _process_list(li: Iterable):
        return sorted([i for i in li if i])

    results = {}
    multiselect_qids = set()

    for name, data in raw_data.items():
        if MULTISELECT in name:
            qid, _ = name.split(MULTISELECT)

            multiselect_qids.add(qid)

            results.setdefault(qid, [])
            results[qid].append(data)
        else:
            qid = name
            results[qid] = data

    for qid, data in results.items():
        if qid in multiselect_qids:
            results[qid] = [_process_list(d) for d in zip(*data)]

    return pl.DataFrame(results)
