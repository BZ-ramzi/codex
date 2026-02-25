from __future__ import annotations

from datetime import datetime, timezone

from .repository import Repository
from .telegram_client import TelegramClient


class SchedulerService:
    def __init__(self, repository: Repository, telegram_client: TelegramClient) -> None:
        self.repository = repository
        self.telegram_client = telegram_client

    def run_due_jobs(self, now: datetime | None = None) -> dict[str, int]:
        now = now or datetime.now(timezone.utc)
        now_iso = now.isoformat()

        due_jobs = self.repository.get_due_schedules(now_iso)
        sent = 0
        failed = 0

        for job in due_jobs:
            try:
                self.telegram_client.send_message(job["chat_id"], job["message"], parse_mode=job["parse_mode"])
                self.repository.mark_sent_or_reschedule(job["id"], now_iso, job["interval_minutes"])
                sent += 1
            except Exception as exc:  # noqa: BLE001
                self.repository.mark_failed(job["id"], str(exc))
                failed += 1

        return {"due": len(due_jobs), "sent": sent, "failed": failed}
