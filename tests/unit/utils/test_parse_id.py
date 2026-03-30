from survy.utils.functions import parse_id


def test_parse_id():
    assert parse_id("Q1_A", "id_multi") == {
        "id": "Q1",
        "multi": "A",
    }

    assert parse_id("Q1.A", "id.multi") == {
        "id": "Q1",
        "multi": "A",
    }

    assert parse_id("Q1_A", "id_loop") == {
        "id": "Q1",
        "loop": "A",
    }

    assert parse_id("Q1.A", "id.loop") == {
        "id": "Q1",
        "loop": "A",
    }

    assert parse_id("Q1.A", "id.loop") == {
        "id": "Q1",
        "loop": "A",
    }

    assert parse_id("Q1.1_2", "id.loop_multi") == {
        "id": "Q1",
        "loop": "1",
        "multi": "2",
    }

    assert parse_id("Q1.1_2", "id.multi_loop") == {
        "id": "Q1",
        "multi": "1",
        "loop": "2",
    }

    assert parse_id("ABC_Q1/DEF", "multi_id/loop") == {
        "id": "Q1",
        "loop": "DEF",
        "multi": "ABC",
    }

    assert parse_id("Dog and Cat_Q1/Man and Women", "multi_id/loop") == {
        "id": "Q1",
        "loop": "Man and Women",
        "multi": "Dog and Cat",
    }

    assert parse_id("Q1_A", "id(.loop)?_multi") == {
        "id": "Q1",
        "multi": "A",
        "loop": None,
    }

    assert parse_id("Q1.A", "id(.loop)?(_multi)?") == {
        "id": "Q1",
        "multi": None,
        "loop": "A",
    }

    assert parse_id("Q1", "id(.loop)?(_multi)?") == {
        "id": "Q1",
        "multi": None,
        "loop": None,
    }
