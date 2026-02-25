# Telegram Panel MVP

Sì, il progetto è in Python, ma ora il pannello è stato migliorato in stile più moderno:
- **UI web single-page** (HTML + JS)
- **API JSON** (`/api/...`) per target, campagne, schedule e run scheduler
- **Schedule ricorrente**: post ogni X minuti (stile cron semplice) su uno o più gruppi
- **Campagne con supporto Telegram HTML + emoji** (parse mode selezionabile: `HTML`/`MarkdownV2`)
- **Motore invio** separato (scheduler + client Telegram mock)

## Avvio pannello web
```bash
python -m src.telegram_panel.main --db demo.db run-web --host 127.0.0.1 --port 8080
```
Apri: `http://127.0.0.1:8080`

## Endpoint API principali
- `GET /api/targets`
- `POST /api/targets`
- `GET /api/campaigns`
- `POST /api/campaigns` (body: `title`, `message`, `parse_mode`)
- `GET /api/schedules`
- `POST /api/schedules` (`campaign_id`, `target_ids`, `run_at`, opzionale `interval_minutes`)
- `POST /api/run-once`

## CLI (supporto)
- `add-target <name> <chat_id>`
- `add-campaign <title> <message> [--parse-mode HTML|MarkdownV2]`
- `schedule <campaign_id> <run_at_iso> <target_ids...> [--every-minutes X]`
- `run-web [--host ... --port ...]`
- `run-once`
- `list-targets`
- `list-schedules`

## Nota produzione
`TelegramClient` è mock: per produzione va sostituito con integrazione reale Telegram Bot API e gestione rate-limit/retry robusta.
