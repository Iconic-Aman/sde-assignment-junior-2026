from pipeline.domain import bucket


def test_bucket_yet_to_reach_out():
    assert bucket([]) == "yet_to_reach_out"


def test_bucket_completed_with_terminal():
    calls = [
        {"failed": False, "terminal": False, "disposition": "callback_requested"},
        {"failed": False, "terminal": True, "disposition": "renewed"},
    ]
    assert bucket(calls) == "completed"


def test_bucket_completed_with_terminal_callable():
    terminal_codes = {"renewed", "not_interested"}
    calls = [
        {"failed": False, "disposition": "renewed"},
    ]
    assert bucket(calls, is_terminal=lambda code: code in terminal_codes) == "completed"


def test_bucket_all_telephony_failed():
    calls = [
        {"failed": True, "terminal": False},
        {"failed": True, "terminal": False},
    ]
    assert bucket(calls) == "in_progress_telephony_failed"


def test_bucket_in_progress_dialed():
    calls = [
        {"failed": True, "terminal": False},
        {"failed": False, "terminal": False, "disposition": "callback_requested"},
    ]
    assert bucket(calls) == "in_progress_dialed"
