"""Transactional application schema and forward-only migrations."""
from __future__ import annotations
import sqlite3

SCHEMA_VERSION = 1

def migrate(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied REAL NOT NULL)")
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS device_identities (
      identity TEXT PRIMARY KEY, vid TEXT, pid TEXT, serial TEXT, fingerprint TEXT NOT NULL,
      quality TEXT NOT NULL, first_seen REAL NOT NULL, last_seen REAL NOT NULL,
      history_json TEXT NOT NULL DEFAULT '[]'
    );
    CREATE TABLE IF NOT EXISTS incidents (
      incident_id TEXT PRIMARY KEY, identity TEXT, state TEXT NOT NULL, verdict TEXT,
      risk INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL, updated REAL NOT NULL,
      FOREIGN KEY(identity) REFERENCES device_identities(identity)
    );
    CREATE TABLE IF NOT EXISTS findings (
      id INTEGER PRIMARY KEY, incident_id TEXT NOT NULL, path TEXT, engine TEXT,
      rule_version TEXT, severity TEXT, evidence_json TEXT, created REAL NOT NULL,
      FOREIGN KEY(incident_id) REFERENCES incidents(incident_id)
    );
    CREATE TABLE IF NOT EXISTS engine_versions (
      engine TEXT PRIMARY KEY, version TEXT NOT NULL, signature TEXT, updated REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS metrics (
      name TEXT PRIMARY KEY, value REAL NOT NULL, updated REAL NOT NULL
    );
    """)
    row = connection.execute("SELECT version FROM schema_migrations WHERE version=?", (SCHEMA_VERSION,)).fetchone()
    if row is None:
        import time
        connection.execute("INSERT INTO schema_migrations VALUES (?, ?)", (SCHEMA_VERSION, time.time()))
    connection.commit()
