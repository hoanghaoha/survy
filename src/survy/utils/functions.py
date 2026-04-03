import re
from itertools import chain
from typing import Any

from survy.separator import SEPARATORS
from survy.errors import ParseError


def extract_mapping(li: list[Any | list[Any]]) -> dict:
    """Generate a value-to-index mapping from a list of responses.

    This function normalizes input values and assigns a unique integer index
    (starting from 1) to each distinct, non-null value. It supports both
    flat lists and nested lists (e.g., multi-select responses).

    Args:
        li (list[Any | list[Any]]):
            A list containing values or lists of values. Elements may include
            `None`, which are ignored.

    Returns:
        dict:
            A dictionary mapping each unique non-null value to a 1-based index,
            sorted in ascending order.

    Behavior:
        - If all elements are `None`, returns an empty dictionary.
        - If all elements are lists, the lists are flattened before processing.
        - Otherwise, the input is treated as a flat list.

    Examples:
        >>> extract_mapping(["A", "B", "A", None])
        {'A': 1, 'B': 2}

        >>> extract_mapping([["A", "B"], ["B", "C"]])
        {'A': 1, 'B': 2, 'C': 3}

        >>> extract_mapping([None, None])
        {}
    """

    def _extract_list(li: list[Any]):
        sorted_set = sorted(set([i for i in li if i]))
        return {value: index for index, value in enumerate(sorted_set, 1)}

    if all([i is None for i in li]):
        return {}

    if all([isinstance(v, list) for v in li]):
        return _extract_list(list(chain.from_iterable(li)))

    return _extract_list(li)


def parse_id(s: str, fmt: str) -> dict:
    """Parse a structured identifier string using a format pattern.

    This function extracts named components (e.g., ``id``, ``multi``)
    from a string based on a format template. The format is converted into a
    regular expression with named capture groups.

    Args:
        s (str):
            The input string to parse.
        fmt (str):
            A format string defining the expected structure. Supported tokens:
            - ``id``: Base identifier
            - ``multi``: Multi-select identifier

            Separators defined in ``survy.separator.SEPARATORS`` are treated as
            literal delimiters in the pattern.

    Returns:
        dict:
            A dictionary of extracted components, where keys correspond to
            tokens in the format string (e.g., ``id``, ``multi``).

    Raises:
        ParseError:
            If the input string does not match the provided format.

    Notes:
        - Tokens are converted into named regex groups.
        - Values are matched as any sequence of characters excluding known separators.
        - The match must span the entire string.

    Examples:
        >>> parse_id("Q1_1", "id_multi")
        {'id': 'Q1', 'multi': '1'}

        >>> parse_id("Q1_1", "id/multi")
        {'id': 'Q1', 'multi': '1'}


        >>> parse_id("invalid", "id_multi")
        Traceback (most recent call last):
            ...
        ParseError: Can not match invalid with pattern id_multi
    """

    def build_regex(fmt: str):
        excluded = "".join(re.escape(s) for s in SEPARATORS)

        TOKEN_REGEX = {
            "id": rf"(?P<id>[^{excluded}]+)",
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
