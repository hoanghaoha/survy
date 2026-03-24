from survy.utils.parse_id import parse_id


def test_parse_id():
    assert parse_id("Q1_A", "id_multi") == {
        "id": "Q1",
        "multi": "A",
    }

    assert parse_id("Q1.A", "id.multi") == {
        "id": "Q1",
        "multi": "A",
    }

    assert parse_id("Q1_A", "id_matrix") == {
        "id": "Q1",
        "matrix": "A",
    }

    assert parse_id("Q1.A", "id.matrix") == {
        "id": "Q1",
        "matrix": "A",
    }

    assert parse_id("Q1.A", "id.matrix") == {
        "id": "Q1",
        "matrix": "A",
    }

    assert parse_id("Q1.1_2", "id.matrix_multi") == {
        "id": "Q1",
        "matrix": "1",
        "multi": "2",
    }

    assert parse_id("Q1.1_2", "id.multi_matrix") == {
        "id": "Q1",
        "multi": "1",
        "matrix": "2",
    }

    assert parse_id("ABC_Q1/DEF", "multi_id/matrix") == {
        "id": "Q1",
        "matrix": "DEF",
        "multi": "ABC",
    }

    assert parse_id("Dog and Cat_Q1/Man and Women", "multi_id/matrix") == {
        "id": "Q1",
        "matrix": "Man and Women",
        "multi": "Dog and Cat",
    }

    assert parse_id("Q1_A", "id(.matrix)?_multi") == {
        "id": "Q1",
        "multi": "A",
        "matrix": None,
    }

    assert parse_id("Q1.A", "id(.matrix)?(_multi)?") == {
        "id": "Q1",
        "multi": None,
        "matrix": "A",
    }

    assert parse_id("Q1", "id(.matrix)?(_multi)?") == {
        "id": "Q1",
        "multi": None,
        "matrix": None,
    }
