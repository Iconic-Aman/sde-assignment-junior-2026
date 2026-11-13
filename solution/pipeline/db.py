import csv
import json
import sqlite3
from pathlib import Path


def connect(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    sql = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    connection.executescript(sql)
    return connection


def load_catalogue(connection, root):
    schema_dir = Path(root) / "assignment-a-data" / "schemas"
    with (schema_dir / "dispositions.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            connection.execute(
                "INSERT OR REPLACE INTO dispositions VALUES (?, ?, ?, ?)",
                (row["workflow_id"], row["code"], row["is_terminal"] == "true",
                 row["is_success"] == "true"),
            )
    connection.commit()


def load_schemas(root):
    directory = Path(root) / "assignment-a-data" / "schemas"
    return {
        item["workflow_id"]: item
        for file in sorted(directory.glob("*.json"))
        for item in [json.loads(file.read_text(encoding="utf-8"))]
    }
