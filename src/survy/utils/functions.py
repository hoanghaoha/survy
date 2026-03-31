import re
from itertools import chain
from typing import Any

from survy.separator import SEPARATORS
from survy.errors import ParseError


def extract_mapping(li: list[Any | list[Any]]) -> dict:
    def _extract_list(li: list[Any]):
        sorted_set = sorted(set([i for i in li if i]))
        return {value: index for index, value in enumerate(sorted_set, 1)}

    if all([i is None for i in li]):
        return {}

    if all([isinstance(v, list) for v in li]):
        return _extract_list(list(chain.from_iterable(li)))

    return _extract_list(li)


def parse_id(s: str, fmt: str) -> dict:
    def build_regex(fmt: str):
        excluded = "".join(re.escape(s) for s in SEPARATORS)

        TOKEN_REGEX = {
            "id": rf"(?P<id>[^{excluded}]+)",
            "loop": rf"(?P<loop>[^{excluded}]+)",
            "multi": rf"(?P<multi>[^{excluded}]+)",
        }

        pattern = fmt

        for key, rgx in TOKEN_REGEX.items():
            pattern = pattern.replace(key, rgx)

        for sep in SEPARATORS:
            pattern = pattern.replace(sep, re.escape(sep))

        return f"^{pattern}$"

    regex = build_regex(fmt)
    match = re.match(regex, s)
    if not match:
        raise ParseError(f"Can not match {s} with pattern {fmt}")
    return match.groupdict()
