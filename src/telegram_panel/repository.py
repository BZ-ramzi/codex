from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


ALLOWED_PARSE_MODES = {"HTML", "MarkdownV2"}


@dataclass
class Target:
    id: int
    name: str
    chat_id: str
    active: bool


@dataclass
class Campaign:
    id: int
    title: str
    message: str
    parse_mode: str
    created_at: str


@dataclass
class ScheduleItem:
    id: int
    campaign_id: int
    target_id: int
    run_at: str
    interval_minutes: int | None
    status: str
    last_error: str | None
    sent_at: str | None


class Repository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def add_target(self, name: str, chat_id: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO targets(name, chat_id, active) VALUES(?, ?, 1)",
            (name, chat_id),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def add_campaign(self, title: str, message: str, parse_mode: str = "HTML") -> int:
        parse_mode = parse_mode.strip() or "HTML"
        if parse_mode not in ALLOWED_PARSE_MODES:
            raise ValueError(f"parse_mode non supportato: {parse_mode}")

        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            "INSERT INTO campaigns(title, message, parse_mode, created_at) VALUES(?, ?, ?, ?)",
            (title, message, parse_mode, now),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def schedule_campaign(
        self,
        campaign_id: int,
        target_ids: list[int],
        run_at_iso: str,
        interval_minutes: int | None = None,
    ) -> int:
        if interval_minutes is not None and interval_minutes <= 0:
            raise ValueError("interval_minutes deve essere > 0")

        count = 0
        for target_id in target_ids:
            self.conn.execute(
                """
                INSERT INTO schedules(campaign_id, target_id, run_at, interval_minutes, status)
                VALUES(?, ?, ?, ?, 'scheduled')
                """,
                (campaign_id, target_id, run_at_iso, interval_minutes),
            )
            count += 1
        self.conn.commit()
        return count

    def get_due_schedules(self, now_iso: str) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT s.id, s.campaign_id, s.target_id, s.run_at, s.interval_minutes, s.status,
                       c.message, c.title, c.parse_mode, t.chat_id, t.name AS target_name
                FROM schedules s
                JOIN campaigns c ON c.id = s.campaign_id
                JOIN targets t ON t.id = s.target_id
                WHERE s.status = 'scheduled'
                  AND t.active = 1
                  AND s.run_at <= ?
                ORDER BY s.run_at ASC
                """,
                (now_iso,),
            )
        )

    def mark_sent(self, schedule_id: int, sent_at_iso: str) -> None:
        self.conn.execute(
            "UPDATE schedules SET status='sent', sent_at=?, last_error=NULL WHERE id=?",
            (sent_at_iso, schedule_id),
        )
        self.conn.commit()

    def mark_sent_or_reschedule(self, schedule_id: int, sent_at_iso: str, interval_minutes: int | None) -> None:
        if interval_minutes and interval_minutes > 0:
            sent_dt = datetime.fromisoformat(sent_at_iso)
            next_run = (sent_dt + timedelta(minutes=interval_minutes)).isoformat()
            self.conn.execute(
                """
                UPDATE schedules
                SET status='scheduled', run_at=?, sent_at=?, last_error=NULL
                WHERE id=?
                """,
                (next_run, sent_at_iso, schedule_id),
            )
        else:
            self.conn.execute(
                "UPDATE schedules SET status='sent', sent_at=?, last_error=NULL WHERE id=?",
                (sent_at_iso, schedule_id),
            )
        self.conn.commit()

    def mark_failed(self, schedule_id: int, error: str) -> None:
        self.conn.execute(
            "UPDATE schedules SET status='failed', last_error=? WHERE id=?",
            (error, schedule_id),
        )
        self.conn.commit()

    def list_targets(self) -> list[sqlite3.Row]:
        return list(self.conn.execute("SELECT id, name, chat_id, active FROM targets ORDER BY id"))

    def list_campaigns(self) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT id, title, message, parse_mode, created_at FROM campaigns ORDER BY id DESC"
            )
        )

    def list_schedules(self) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT s.id, c.title, t.name AS target_name, s.run_at, s.interval_minutes, s.status, s.last_error
                FROM schedules s
                JOIN campaigns c ON c.id = s.campaign_id
                JOIN targets t ON t.id = s.target_id
                ORDER BY s.id DESC
                """
            )
        )
