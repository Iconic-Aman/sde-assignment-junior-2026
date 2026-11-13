# AI Usage Disclosure

## Tools used
- Claude & Gemini (via Antigravity coding agent)

## What I used them for
- Scaffolding unit tests for regex date and decimal parsers.
- Generating test inputs covering edge cases (such as Indian lakh number format and leap year dates).
- Structuring modular package layouts and small git commit splits.

## What I wrote or decided myself
- Database schema design: append-only SQLite ledger using database triggers to prevent updates and deletes.
- Late-arriving lead linking strategy using SQL views (`linked_events` and `call_lead`) instead of backfilling/updating historical rows.
- Cryptographic strategy: keyed HMAC-SHA256 for deterministic joinable phone hashes and AES-GCM for PII encryption at rest.
- Lead merge logic adhering to first-seen batch identity and non-null attribute updates.

## Where the AI was wrong or unhelpful
- Initial SQL view joining `linked_events` with `events` caused ambiguous column references in SQLite (`workflow_id`). Fixed by querying `linked_events` view directly and qualifying column prefixes.
- AI attempted to use deprecated Pydantic v1 `parse_obj` syntax which generated warnings on Pydantic v2; replaced with `model_validate`.
- Timezone initialization raised `ZoneInfoNotFoundError` on Windows without `tzdata`; added fallback to fixed-offset IST timedelta (`+05:30`).

## How I verified AI-generated code
- Automated test suite: 22 unit and integration tests executed with `uv run pytest`.
- Sample data verification: ingested seed 42 small-scale synthetic data (2,057 leads, 8,745 events) and validated all generated CSV and JSON reports against contract schemas.
- Line-by-line inspection of all parsers, SQL statements, and PII encryption routines.
