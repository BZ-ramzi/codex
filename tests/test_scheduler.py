from __future__ import annotations

import sqlite3
import unittest
from datetime import datetime, timedelta, timezone

from src.telegram_panel.db import init_db
from src.telegram_panel.repository import Repository
from src.telegram_panel.scheduler import SchedulerService
from src.telegram_panel.telegram_client import TelegramClient


class SchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        init_db(self.conn)
        self.repo = Repository(self.conn)
        self.service = SchedulerService(self.repo, TelegramClient())

    def test_due_job_marked_as_sent(self) -> None:
        target_id = self.repo.add_target("Gruppo", "-100111")
        campaign_id = self.repo.add_campaign("Promo", "Testo promo")
        run_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        self.repo.schedule_campaign(campaign_id, [target_id], run_at)

        result = self.service.run_due_jobs(datetime.now(timezone.utc))

        self.assertEqual(result["due"], 1)
        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["failed"], 0)
        rows = self.repo.list_schedules()
        self.assertEqual(rows[0]["status"], "sent")

    def test_recurring_job_rescheduled(self) -> None:
        target_id = self.repo.add_target("Gruppo", "-100444")
        campaign_id = self.repo.add_campaign("Ricorrente", "Post periodico")
        run_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        self.repo.schedule_campaign(campaign_id, [target_id], run_at, interval_minutes=5)

        first_now = datetime.now(timezone.utc)
        result = self.service.run_due_jobs(first_now)

        self.assertEqual(result["sent"], 1)
        row = self.repo.list_schedules()[0]
        self.assertEqual(row["status"], "scheduled")

        next_run = datetime.fromisoformat(row["run_at"])
        expected = first_now + timedelta(minutes=5)
        self.assertGreaterEqual(next_run, expected - timedelta(seconds=1))
        self.assertLessEqual(next_run, expected + timedelta(seconds=1))

    def test_invalid_chat_id_marked_failed(self) -> None:
        target_id = self.repo.add_target("Gruppo", "100111")
        campaign_id = self.repo.add_campaign("Promo", "Testo promo")
        run_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        self.repo.schedule_campaign(campaign_id, [target_id], run_at)

        result = self.service.run_due_jobs(datetime.now(timezone.utc))

        self.assertEqual(result["due"], 1)
        self.assertEqual(result["sent"], 0)
        self.assertEqual(result["failed"], 1)
        rows = self.repo.list_schedules()
        self.assertEqual(rows[0]["status"], "failed")
        self.assertIsNotNone(rows[0]["last_error"])

    def test_markdown_parse_mode_campaign_sent(self) -> None:
        target_id = self.repo.add_target("Gruppo", "-100222")
        campaign_id = self.repo.add_campaign("Promo", "*Testo* promo", "MarkdownV2")
        run_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        self.repo.schedule_campaign(campaign_id, [target_id], run_at)

        result = self.service.run_due_jobs(datetime.now(timezone.utc))

        self.assertEqual(result["sent"], 1)

    def test_invalid_parse_mode_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.repo.add_campaign("Promo", "Messaggio", "PLAINTEXT")


if __name__ == "__main__":
    unittest.main()
