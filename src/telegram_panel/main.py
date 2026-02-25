from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from .db import connect, init_db
from .repository import Repository
from .scheduler import SchedulerService
from .telegram_client import TelegramClient
from .web import run_server


def _iso_utc(value: str) -> str:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Telegram panel MVP CLI")
    parser.add_argument("--db", default="telegram_panel.db", help="Percorso database SQLite")

    sub = parser.add_subparsers(dest="command", required=True)

    add_target = sub.add_parser("add-target", help="Aggiunge un gruppo/canale target")
    add_target.add_argument("name")
    add_target.add_argument("chat_id")

    add_campaign = sub.add_parser("add-campaign", help="Crea una campagna")
    add_campaign.add_argument("title")
    add_campaign.add_argument("message")
    add_campaign.add_argument("--parse-mode", default="HTML", choices=["HTML", "MarkdownV2"])

    schedule = sub.add_parser("schedule", help="Schedula una campagna")
    schedule.add_argument("campaign_id", type=int)
    schedule.add_argument("run_at", help="ISO datetime, es: 2026-01-31T09:00:00+01:00")
    schedule.add_argument("target_ids", nargs="+", type=int)
    schedule.add_argument("--every-minutes", type=int, default=None, help="Ripeti ogni X minuti")

    run_web = sub.add_parser("run-web", help="Avvia pannello web di gestione")
    run_web.add_argument("--host", default="127.0.0.1")
    run_web.add_argument("--port", type=int, default=8080)

    sub.add_parser("run-once", help="Esegue i job in scadenza")
    sub.add_parser("list-targets", help="Mostra i target")
    sub.add_parser("list-schedules", help="Mostra gli invii")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    db_path = Path(args.db)
    conn = connect(db_path)
    init_db(conn)
    repo = Repository(conn)

    if args.command == "add-target":
        target_id = repo.add_target(args.name, args.chat_id)
        print(f"Target creato con id={target_id}")
        return

    if args.command == "add-campaign":
        campaign_id = repo.add_campaign(args.title, args.message, args.parse_mode)
        print(f"Campagna creata con id={campaign_id}")
        return

    if args.command == "schedule":
        run_at = _iso_utc(args.run_at)
        inserted = repo.schedule_campaign(args.campaign_id, args.target_ids, run_at, args.every_minutes)
        print(f"Schedulati {inserted} invii")
        return

    if args.command == "run-web":
        run_server(str(db_path), host=args.host, port=args.port)
        return

    if args.command == "run-once":
        scheduler = SchedulerService(repo, TelegramClient())
        result = scheduler.run_due_jobs()
        print(f"Due={result['due']} Sent={result['sent']} Failed={result['failed']}")
        return

    if args.command == "list-targets":
        for row in repo.list_targets():
            print(f"{row['id']} | {row['name']} | {row['chat_id']} | active={row['active']}")
        return

    if args.command == "list-schedules":
        for row in repo.list_schedules():
            print(
                f"{row['id']} | {row['title']} | {row['target_name']} | {row['run_at']} | {row['status']} | {row['last_error']}"
            )
        return


if __name__ == "__main__":
    main()
