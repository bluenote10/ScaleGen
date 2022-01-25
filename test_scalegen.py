from scalegen import close_pattern, get_start_pitches


def test_get_start_pitches() -> None:
    assert get_start_pitches([0, 1, 2], 20, 22, False) == [20]
    assert get_start_pitches([0, 1, 2], 20, 23, False) == [20, 21]
    assert get_start_pitches([0, 1, 2], 20, 24, False) == [20, 21, 22]


def test_get_start_pitches__positive_and_negative() -> None:
    assert get_start_pitches([-1, +1], 20, 22, False) == [21]
    assert get_start_pitches([-1, +1], 20, 23, False) == [21, 22]

    assert get_start_pitches([+2, +3], 20, 22, False) == [18, 19]
    assert get_start_pitches([-2, -3], 20, 22, False) == [23, 24]


def test_get_start_pitches__cycle_up_and_down() -> None:
    assert get_start_pitches([0, 1, 2], 20, 22) == [20]
    assert get_start_pitches([0, 1, 2], 20, 23) == [20, 21, 20]
    assert get_start_pitches([0, 1, 2], 20, 24) == [20, 21, 22, 21, 20]


def test_close_pattern() -> None:
    assert close_pattern([0, 1, 2]) == [0, 1, 2, 1, 0]
