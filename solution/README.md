# Solution: Interaction Ledger & Reporting Pipeline

A batch data pipeline that cleans lead CSVs, records call events in an append-only ledger, links records via hashed phone numbers, and outputs 5 client report files.

## Architecture

- `pipeline/parsers/`: Pure parsing functions for phone numbers, dates, decimals, headers, and timestamps.
- `pipeline/ingest/`: Ingestion engines for leads (validation, rejection, merging) and events (deduplication, schema validation).
- `pipeline/reports/`: SQL-driven aggregation queries and CSV/JSON output writer.
- `pipeline/pii.py`: HMAC-SHA256 keyed phone hashing and AES-GCM encryption for private fields.
- `pipeline/db.py` & `pipeline/schema.sql`: SQLite database initialization, triggers, and views.
- `pipeline/domain.py`: Pure domain logic for disposition override resolution and lead buckets.
- `tests/`: 22 automated tests covering parsers, domain rules, late-lead resolution, and idempotency.

## Quick Start

```bash
# Install dependencies with uv
uv sync

# Configure environment keys
export PII_HMAC_KEY="0123456789abcdef0123456789abcdef01234567"
export PII_ENC_KEY="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

# Ingest data drops
uv run python -m pipeline.cli ingest data/drop_1
uv run python -m pipeline.cli ingest data/drop_2

# Produce reports
uv run python -m pipeline.cli report --out reports/

# Run tests
uv run pytest -v
```
