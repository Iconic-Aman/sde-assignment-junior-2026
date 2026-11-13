import os
from pathlib import Path

DB_PATH = os.environ.get("LEDGER_DB", "solution/ledger.db")
ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = ROOT / "assignment-a-data" / "schemas"
