import argparse
import os
from pathlib import Path

from .db import connect, load_catalogue, load_schemas
from .ingest.events import ingest_event_file
from .ingest.leads import ingest_lead_file
from .reports.writer import write_reports


def _paths(drop):
    base = Path(drop)
    lead_files = sorted((base / "leads").glob("*/*.csv"), key=lambda p: (p.name, str(p)))
    event_files = sorted((base / "events").glob("*.jsonl"), key=lambda p: p.name)
    return lead_files, event_files


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ledger")
    parser.add_argument("--db", default=os.environ.get("LEDGER_DB", "solution/ledger.db"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ingest").add_argument("drop")
    commands.add_parser("report").add_argument("--out", required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    schemas = load_schemas(root)
    with connect(args.db) as connection:
        load_catalogue(connection, root)
        if args.command == "ingest":
            lead_files, event_files = _paths(args.drop)
            for path in lead_files:
                workflow = path.parent.name
                if workflow not in schemas:
                    raise ValueError("No workflow schema for: " + workflow)
                ingest_lead_file(connection, args.drop, path, schemas[workflow])
            for path in event_files:
                ingest_event_file(connection, args.drop, path)
            print("Ingest complete.")
        else:
            write_reports(connection, args.out, root)
            print("Reports written to " + str(Path(args.out)))


if __name__ == "__main__":
    main()
