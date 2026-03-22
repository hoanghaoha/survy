from typing import Any
from itertools import chain


def extract_mapping(li: list[Any | list[Any]]) -> dict:
    def _extract_list(li: list[Any]):
        sorted_set = sorted(set(li))
        return {value: index for index, value in enumerate(sorted_set, 1)}

    if all([isinstance(v, list) for v in li]):
        return _extract_list(list(chain.from_iterable(li)))

    return _extract_list(li)
