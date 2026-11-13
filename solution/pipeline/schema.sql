PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ingested_files (
  id INTEGER PRIMARY KEY, drop_path TEXT NOT NULL, rel_path TEXT NOT NULL,
  sha256 TEXT NOT NULL, UNIQUE(drop_path, rel_path)
);

CREATE TABLE IF NOT EXISTS file_stats (
  file_id INTEGER PRIMARY KEY REFERENCES ingested_files(id),
  rows_total INTEGER DEFAULT 0, rows_rejected INTEGER DEFAULT 0,
  duplicates_merged INTEGER DEFAULT 0, field_warnings INTEGER DEFAULT 0,
  events_total INTEGER DEFAULT 0, malformed_events INTEGER DEFAULT 0,
  duplicate_events INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dispositions (
  workflow_id TEXT, code TEXT, is_terminal INTEGER, is_success INTEGER,
  PRIMARY KEY(workflow_id, code)
);

CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY, workflow_id TEXT NOT NULL, phone_hash TEXT NOT NULL,
  phone_last4 TEXT NOT NULL, external_ref TEXT, batch_id TEXT NOT NULL,
  fields_json TEXT NOT NULL, pii_enc BLOB,
  UNIQUE(workflow_id, phone_hash)
);

CREATE TABLE IF NOT EXISTS rejections (
  workflow_id TEXT, batch_id TEXT, row_number INTEGER, reason TEXT,
  PRIMARY KEY(workflow_id, batch_id, row_number)
);

CREATE TABLE IF NOT EXISTS events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
  event_type TEXT NOT NULL, workflow_id TEXT NOT NULL, call_id TEXT,
  occurred_at_utc TEXT NOT NULL, phone_hash TEXT, payload_json TEXT NOT NULL,
  disposition_code TEXT, file_id INTEGER REFERENCES ingested_files(id)
);

CREATE INDEX IF NOT EXISTS leads_phone ON leads(workflow_id, phone_hash);
CREATE INDEX IF NOT EXISTS events_call ON events(workflow_id, call_id);
CREATE INDEX IF NOT EXISTS events_phone ON events(workflow_id, phone_hash);

CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;

CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;

CREATE VIEW IF NOT EXISTS event_lead AS
  SELECT e.*, l.id AS lead_id FROM events e
  LEFT JOIN leads l ON l.workflow_id=e.workflow_id AND l.phone_hash=e.phone_hash;

CREATE VIEW IF NOT EXISTS call_lead AS
  SELECT e.workflow_id, e.call_id, MIN(l.id) AS lead_id
  FROM events e JOIN leads l ON l.workflow_id=e.workflow_id AND l.phone_hash=e.phone_hash
  WHERE e.call_id IS NOT NULL AND e.phone_hash IS NOT NULL
  GROUP BY e.workflow_id, e.call_id;

CREATE VIEW IF NOT EXISTS linked_events AS
  SELECT e.*, CASE WHEN e.event_type='disposition.override' THEN c.lead_id
                   ELSE d.lead_id END AS lead_id
  FROM events e
  LEFT JOIN event_lead d ON d.seq=e.seq
  LEFT JOIN call_lead c ON c.workflow_id=e.workflow_id AND c.call_id=e.call_id;
