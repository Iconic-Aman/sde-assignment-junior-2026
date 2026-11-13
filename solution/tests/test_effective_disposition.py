from pipeline.domain import effective_disposition


def test_override_takes_priority_over_set():
    sets = [("2026-10-05T10:00:00", 1, "callback_requested")]
    overrides = [("2026-10-05T11:00:00", 2, "renewed")]
    assert effective_disposition(sets, overrides) == "renewed"


def test_latest_override_wins():
    sets = [("2026-10-05T10:00:00", 1, "callback_requested")]
    overrides = [
        ("2026-10-05T11:00:00", 2, "not_interested"),
        ("2026-10-05T12:00:00", 3, "renewed"),
    ]
    assert effective_disposition(sets, overrides) == "renewed"


def test_latest_set_when_no_overrides():
    sets = [
        ("2026-10-05T10:00:00", 1, "callback_requested"),
        ("2026-10-05T10:30:00", 2, "payment_link_sent"),
    ]
    assert effective_disposition(sets, []) == "payment_link_sent"


def test_seq_tie_breaker_same_timestamp():
    sets = [
        ("2026-10-05T10:00:00", 1, "callback_requested"),
        ("2026-10-05T10:00:00", 5, "payment_link_sent"),
    ]
    assert effective_disposition(sets, []) == "payment_link_sent"


def test_empty_dispositions_returns_none():
    assert effective_disposition([], []) is None
