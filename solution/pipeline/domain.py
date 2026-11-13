def effective_disposition(sets, overrides):
    """sets/overrides: lists of (occurred_at_utc, seq, code). Unknown codes already removed."""
    pool = overrides or sets
    return max(pool)[2] if pool else None


def bucket(calls, is_terminal=None):
    if not calls:
        return "yet_to_reach_out"
    if any(c.get("terminal") or (is_terminal and is_terminal(c.get("disposition"))) for c in calls):
        return "completed"
    if all(c.get("failed") for c in calls):
        return "in_progress_telephony_failed"
    return "in_progress_dialed"
