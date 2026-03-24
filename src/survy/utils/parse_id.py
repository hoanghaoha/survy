import re

from survy.separator import SEPARATORS
from survy.errors import ParseError


def build_regex(fmt: str):
    excluded = "".join(re.escape(s) for s in SEPARATORS)

    TOKEN_REGEX = {
        "id": rf"(?P<id>[^{excluded}]+)",
        "matrix": rf"(?P<matrix>[^{excluded}]+)",
        "multi": rf"(?P<multi>[^{excluded}]+)",
    }

    pattern = fmt

    for key, rgx in TOKEN_REGEX.items():
        pattern = pattern.replace(key, rgx)

    for sep in SEPARATORS:
        pattern = pattern.replace(sep, re.escape(sep))

    return f"^{pattern}$"


def parse_id(s: str, fmt: str) -> dict:
    regex = build_regex(fmt)
    match = re.match(regex, s)
    if not match:
        raise ParseError(f"Can not match {s} with pattern {fmt}")
    return match.groupdict()
