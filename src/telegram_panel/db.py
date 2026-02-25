from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_campaign_parse_mode_column(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(campaigns)")}
    if "parse_mode" not in columns:
        conn.execute("ALTER TABLE campaigns ADD COLUMN parse_mode TEXT NOT NULL DEFAULT 'HTML'")


def _ensure_schedule_interval_column(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(schedules)")}
    if "interval_minutes" not in columns:
        conn.execute("ALTER TABLE schedules ADD COLUMN interval_minutes INTEGER")


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            chat_id TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            parse_mode TEXT NOT NULL DEFAULT 'HTML',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            run_at TEXT NOT NULL,
            interval_minutes INTEGER,
            status TEXT NOT NULL DEFAULT 'scheduled',
            last_error TEXT,
            sent_at TEXT,
            FOREIGN KEY(campaign_id) REFERENCES campaigns(id),
            FOREIGN KEY(target_id) REFERENCES targets(id)
        );
        """
    )
    _ensure_campaign_parse_mode_column(conn)
    _ensure_schedule_interval_column(conn)
    conn.commit()
