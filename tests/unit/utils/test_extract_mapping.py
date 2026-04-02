from survy.utils.functions import extract_mapping


def test_extract_mapping_basic():
    result = extract_mapping(["B", "A", "B", None])
    assert result == {"A": 1, "B": 2}


def test_extract_mapping_all_none():
    result = extract_mapping([None, None])
    assert result == {}


def test_extract_mapping_nested_lists():
    result = extract_mapping([["A", "B"], ["B", "C"]])
    assert result == {"A": 1, "B": 2, "C": 3}


def test_extract_mapping_nested_with_none():
    result = extract_mapping([["A", None], ["B", None]])
    assert result == {"A": 1, "B": 2}


def test_extract_mapping_ignores_falsy():
    result = extract_mapping(["A", "", None, "B"])
    assert result == {"A": 1, "B": 2}


def test_extract_mapping_numeric():
    result = extract_mapping([3, 1, 2, 1])
    assert result == {1: 1, 2: 2, 3: 3}


def test_extract_mapping_sorted_order():
    result = extract_mapping(["C", "A", "B"])
    assert list(result.keys()) == ["A", "B", "C"]
