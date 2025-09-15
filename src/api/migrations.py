"""Simple migrations runner for Muleta Cognitiva.

Usage: import and call apply_migrations() from your setup script or CI.
This runner looks for SQL files in the top-level `migrations/` directory and
applies any new ones in filename order. It records applied migrations in
an `applied_migrations` table and performs a simple file backup before running.
"""

import datetime
import hashlib
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "src" / "api" / "muleta.db"
MIGRATIONS_DIR = ROOT / "migrations"


def _connect(path=DB_PATH):
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    # Recommended PRAGMAs for integrity and performance
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def _ensure_migrations_table(conn):
    conn.execute(
        """
    CREATE TABLE IF NOT EXISTS applied_migrations (
        id INTEGER PRIMARY KEY,
        filename TEXT NOT NULL UNIQUE,
        checksum TEXT,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
    )


def _checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def apply_migrations(
    db_path: Path = DB_PATH, migrations_dir: Path = MIGRATIONS_DIR, backup: bool = True
):
    migrations = sorted([p for p in migrations_dir.glob("*.sql")])
    if not migrations:
        print("No migrations found in", migrations_dir)
        return

    if backup and db_path.exists():
        ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        bak = db_path.with_suffix(f".bak.{ts}")
        # copy the DB file (atomic move can be used on same FS but we prefer copy)
        with open(db_path, "rb") as r, open(bak, "wb") as w:
            w.write(r.read())
        print("Backup created:", bak)

    conn = _connect(db_path)
    try:
        with conn:
            _ensure_migrations_table(conn)
            cur = conn.cursor()
            cur.execute("SELECT filename, checksum FROM applied_migrations")
            applied = {r["filename"]: r["checksum"] for r in cur.fetchall()}
            for m in migrations:
                name = m.name
                sql = m.read_text()
                ch = _checksum(sql)
                if name in applied and applied[name] == ch:
                    print("Skipping already-applied:", name)
                    continue
                print("Applying:", name)
                # execute as a single transaction; complex changes should handle copy/rename themselves
                cur.executescript(sql)
                cur.execute(
                    "INSERT OR REPLACE INTO applied_migrations (filename, checksum, applied_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    (name, ch),
                )
    finally:
        conn.close()


if __name__ == "__main__":
    apply_migrations()
