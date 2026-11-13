# Submission

## Candidate
- **Assignment chosen:** A (Interaction Ledger & Reporting Pipeline)
- **Time spent:** ~6h

## How to run
```bash
# Setup virtual environment and dependencies with uv
uv sync

# Set required PII encryption and hashing keys in environment
export PII_HMAC_KEY="0123456789abcdef0123456789abcdef01234567"
export PII_ENC_KEY="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

# Ingest drops incrementally
uv run python -m pipeline.cli ingest data/drop_1
uv run python -m pipeline.cli ingest data/drop_2

# Generate all 5 reports
uv run python -m pipeline.cli report --out reports/

# Run complete test suite (22 tests)
uv run pytest -v
```

## Design
- **Append-only ledger:** `events` table is strictly append-only, enforced by SQLite `BEFORE UPDATE` and `BEFORE DELETE` triggers that raise abort.
- **Report-time resolution:** Late-arriving leads link to earlier orphan events dynamically through SQL views (`linked_events`, `call_lead`). Zero event updates required.
- **PII at rest:** Phones hashed using keyed `HMAC-SHA256` for joins without plaintext exposure. All fields marked `pii: true` are encrypted at rest with `AES-GCM` using a 256-bit key. Reports display masked phones (`+91******1234`).
- **Idempotency:** `ingested_files` tracks `(drop_path, rel_path, sha256)`. Seen files skip execution within a single transaction per file. Duplicate `event_id` rows are ignored via `INSERT OR IGNORE`.

## Decisions & assumptions

| Decision | Why | Alternative considered |
|---|---|---|
| SQLite with WAL mode | Zero infrastructure, fast embedded SQL views, easy reviewer verification | PostgreSQL (unnecessary setup overhead for batch scale) |
| HMAC-SHA256 for phone matching | Standard SHA-256 is vulnerable to rainbow table brute-forcing on 10-digit Indian numbers | Plain hashing or reversible encryption |
| Report-time SQL view linking | Allows Day 1 orphan events to link automatically when Day 2 leads arrive | Updating past event records upon lead ingest |
| Lead merge: first file sets batch_id | Contract specifies first valid file stem remains batch_id permanently | Updating batch_id on subsequent merges |
| Naive timestamps treated as IST | Indian campaign operational context | Defaulting to UTC |

## Failure modes considered
- **Dirty input headers:** Normalized by trimming, lowercasing, and collapsing whitespace/underscores against alias lists.
- **Schema validation order:** Validated in strict schema field order; first failure logged to `rejections.csv` (no PII recorded).
- **Duplicate events across drops:** Deduplicated via primary key constraint on `event_id`.
- **Re-runs of identical drops:** File registry hashes detect previously ingested files and skip with zero database mutations.
- **Corrupted JSON events:** Caught and counted in `data_quality.json` under `malformed_events`.

## Testing
- **Unit parsers:** 6 valid phone variants, invalid phones, 4 date formats, currency symbols (`Rs.`, `₹`, `INR`), decimal rounding, and timestamp parsing.
- **Domain logic:** Effective disposition override vs set priority, sequence tie-breakers, and 4 lead bucket classifications.
- **Idempotency:** Verified re-ingesting `drop_1` twice produces 0 duplicate records.
- **Late leads:** Verified orphan count drops from 1 to 0 when lead arrives in subsequent drop.
- **Total suite:** 22 tests passing in 0.77s.

## Results
- Evaluated on seed 42 small scale: 2,057 leads (1,949 valid, 108 rejected), 8,745 events (8,737 valid, 8 malformed, 237 duplicates). All 5 report files match contract format.

## If I had another day
1. Implement partition tables on PostgreSQL for events grouped by month for 100k+ daily scale.
2. Add automated golden-file snapshot diff testing against pre-computed report outputs.
3. Add CLI flags for CSV delimiter selection and parallel batch processing workers.
