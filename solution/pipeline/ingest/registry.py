import hashlib
from pathlib import Path


def register_file(connection, drop, path):
    drop_path = str(Path(drop).resolve())
    relative = path.relative_to(drop).as_posix()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    previous = connection.execute(
        "SELECT id, sha256 FROM ingested_files WHERE drop_path=? AND rel_path=?",
        (drop_path, relative),
    ).fetchone()
    if previous:
        if previous["sha256"] != digest:
            raise ValueError("Input file changed after ingestion: " + relative)
        return None
    cursor = connection.execute(
        "INSERT INTO ingested_files(drop_path, rel_path, sha256) VALUES (?, ?, ?)",
        (drop_path, relative, digest),
    )
    connection.execute("INSERT INTO file_stats(file_id) VALUES (?)", (cursor.lastrowid,))
    return cursor.lastrowid
