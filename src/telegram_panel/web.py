from __future__ import annotations

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .db import connect, init_db
from .repository import Repository
from .scheduler import SchedulerService
from .telegram_client import TelegramClient


APP_HTML = """<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>Telegram Panel</title>
  <style>
    body { font-family: Inter, Arial, sans-serif; margin: 0; background: #f6f7fb; color: #1f2937; }
    header { background: #111827; color: #fff; padding: 14px 20px; }
    main { max-width: 1100px; margin: 20px auto; padding: 0 14px; }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .card { background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; }
    h2 { margin: 4px 0 12px 0; font-size: 18px; }
    table { width: 100%; border-collapse: collapse; background: white; }
    th, td { border-bottom: 1px solid #eee; text-align: left; padding: 8px; font-size: 14px; }
    input, textarea, select, button { width: 100%; padding: 8px; margin: 6px 0; border: 1px solid #d1d5db; border-radius: 8px; }
    button { background: #111827; color: white; cursor: pointer; }
    .actions { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
    .muted { color: #6b7280; font-size: 13px; }
  </style>
</head>
<body>
<header><strong>Telegram Panel MVP</strong> <span class='muted'>Pannello web + motore invio</span></header>
<main>
  <div class='grid'>
    <section class='card'>
      <h2>Nuovo target</h2>
      <form id='targetForm'>
        <input name='name' placeholder='Nome gruppo/canale' required>
        <input name='chat_id' placeholder='-100123456...' required>
        <button type='submit'>Aggiungi target</button>
      </form>
    </section>

    <section class='card'>
      <h2>Nuova campagna</h2>
      <form id='campaignForm'>
        <input name='title' placeholder='Titolo campagna' required>
        <textarea name='message' rows='3' placeholder='Messaggio Telegram (supporta HTML + emoji 😎🔥)' required></textarea>
        <select name='parse_mode' required><option value='HTML'>HTML</option><option value='MarkdownV2'>MarkdownV2</option></select>
        <button type='submit'>Crea campagna</button>
      </form>
    </section>

    <section class='card'>
      <h2>Pianifica invio</h2>
      <form id='scheduleForm'>
        <select name='campaign_id' id='campaignSelect' required></select>
        <select name='target_ids' id='targetSelect' multiple size='4' required></select>
        <input type='datetime-local' name='run_at' required>
        <input type='number' min='1' name='interval_minutes' placeholder='Ogni X minuti (opzionale)'>
        <button type='submit'>Schedula</button>
      </form>
      <p class='muted'>Usa Ctrl/Cmd per multi-selezionare target.</p>
    </section>
  </div>

  <div class='actions' style='margin-top:12px;'>
    <button onclick='runDueJobs()'>Esegui job dovuti ora</button>
    <button onclick='refreshAll()'>Aggiorna dashboard</button>
    <div class='card'><strong id='kpiTargets'>0</strong><br><span class='muted'>Target</span></div>
    <div class='card'><strong id='kpiSchedules'>0</strong><br><span class='muted'>Schedule</span></div>
  </div>

  <section class='card' style='margin-top:12px;'>
    <h2>Target</h2>
    <table id='targetsTable'><thead><tr><th>ID</th><th>Nome</th><th>Chat ID</th><th>Attivo</th></tr></thead><tbody></tbody></table>
  </section>

  <section class='card' style='margin-top:12px;'>
    <h2>Campagne</h2>
    <table id='campaignsTable'><thead><tr><th>ID</th><th>Titolo</th><th>Messaggio</th><th>Parse Mode</th><th>Data creazione</th></tr></thead><tbody></tbody></table>
  </section>

  <section class='card' style='margin-top:12px;'>
    <h2>Scheduling</h2>
    <table id='schedulesTable'><thead><tr><th>ID</th><th>Campagna</th><th>Target</th><th>Run At</th><th>Ogni X min</th><th>Stato</th><th>Errore</th></tr></thead><tbody></tbody></table>
  </section>
</main>
<script>
async function api(path, opts={}) {
  const res = await fetch(path, { headers: {'Content-Type':'application/json'}, ...opts });
  if (!res.ok) throw new Error(await res.text());
  return res.status === 204 ? null : res.json();
}

function fillTable(id, rows) {
  document.querySelector(`#${id} tbody`).innerHTML = rows.join('');
}

async function refreshAll() {
  const [targets, campaigns, schedules] = await Promise.all([
    api('/api/targets'), api('/api/campaigns'), api('/api/schedules')
  ]);

  fillTable('targetsTable', targets.map(t => `<tr><td>${t.id}</td><td>${t.name}</td><td>${t.chat_id}</td><td>${t.active}</td></tr>`));
  fillTable('campaignsTable', campaigns.map(c => `<tr><td>${c.id}</td><td>${c.title}</td><td>${c.message}</td><td>${c.parse_mode}</td><td>${c.created_at}</td></tr>`));
  fillTable('schedulesTable', schedules.map(s => `<tr><td>${s.id}</td><td>${s.title}</td><td>${s.target_name}</td><td>${s.run_at}</td><td>${s.interval_minutes ?? ''}</td><td>${s.status}</td><td>${s.last_error ?? ''}</td></tr>`));

  document.getElementById('campaignSelect').innerHTML = campaigns.map(c => `<option value='${c.id}'>${c.id} - ${c.title}</option>`).join('');
  document.getElementById('targetSelect').innerHTML = targets.map(t => `<option value='${t.id}'>${t.id} - ${t.name}</option>`).join('');
  document.getElementById('kpiTargets').innerText = targets.length;
  document.getElementById('kpiSchedules').innerText = schedules.length;
}

document.getElementById('targetForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  await api('/api/targets', {method:'POST', body: JSON.stringify({name:f.get('name'), chat_id:f.get('chat_id')})});
  e.target.reset();
  refreshAll();
});

document.getElementById('campaignForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  await api('/api/campaigns', {method:'POST', body: JSON.stringify({title:f.get('title'), message:f.get('message'), parse_mode:f.get('parse_mode')})});
  e.target.reset();
  refreshAll();
});

document.getElementById('scheduleForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  const targets = [...document.getElementById('targetSelect').selectedOptions].map(o => Number(o.value));
  await api('/api/schedules', {method:'POST', body: JSON.stringify({
    campaign_id: Number(f.get('campaign_id')),
    target_ids: targets,
    run_at: f.get('run_at'),
    interval_minutes: f.get('interval_minutes') ? Number(f.get('interval_minutes')) : null
  })});
  e.target.reset();
  refreshAll();
});

async function runDueJobs() {
  await api('/api/run-once', {method:'POST'});
  refreshAll();
}

refreshAll();
</script>
</body>
</html>
"""


class PanelHandler(BaseHTTPRequestHandler):
    repo: Repository

    def _send_html(self, content: str, status: int = 200) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
        return json.loads(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            self._send_html(APP_HTML)
            return
        if self.path == "/api/targets":
            rows = self.repo.list_targets()
            self._send_json([dict(r) for r in rows])
            return
        if self.path == "/api/campaigns":
            rows = self.repo.list_campaigns()
            self._send_json([dict(r) for r in rows])
            return
        if self.path == "/api/schedules":
            rows = self.repo.list_schedules()
            self._send_json([dict(r) for r in rows])
            return
        self._send_json({"error": "not_found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/targets":
            data = self._read_json()
            name = str(data.get("name", "")).strip()
            chat_id = str(data.get("chat_id", "")).strip()
            if not name or not chat_id:
                self._send_json({"error": "name and chat_id required"}, status=400)
                return
            new_id = self.repo.add_target(name, chat_id)
            self._send_json({"id": new_id}, status=201)
            return

        if self.path == "/api/campaigns":
            data = self._read_json()
            title = str(data.get("title", "")).strip()
            message = str(data.get("message", "")).strip()
            parse_mode = str(data.get("parse_mode", "HTML")).strip() or "HTML"
            if not title or not message:
                self._send_json({"error": "title and message required"}, status=400)
                return
            try:
                new_id = self.repo.add_campaign(title, message, parse_mode)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            self._send_json({"id": new_id}, status=201)
            return

        if self.path == "/api/schedules":
            data = self._read_json()
            try:
                campaign_id = int(data.get("campaign_id", 0))
                target_ids = [int(v) for v in data.get("target_ids", [])]
                run_at_raw = str(data.get("run_at", ""))
                interval_minutes = data.get("interval_minutes")
                interval_minutes = int(interval_minutes) if interval_minutes is not None else None
                run_at = datetime.fromisoformat(run_at_raw)
                if run_at.tzinfo is None:
                    run_at = run_at.replace(tzinfo=timezone.utc)
            except Exception:  # noqa: BLE001
                self._send_json({"error": "invalid payload"}, status=400)
                return

            if not campaign_id or not target_ids:
                self._send_json({"error": "campaign_id and target_ids required"}, status=400)
                return

            if interval_minutes is not None and interval_minutes <= 0:
                self._send_json({"error": "interval_minutes deve essere > 0"}, status=400)
                return

            inserted = self.repo.schedule_campaign(
                campaign_id,
                target_ids,
                run_at.astimezone(timezone.utc).isoformat(),
                interval_minutes,
            )
            self._send_json({"inserted": inserted}, status=201)
            return

        if self.path == "/api/run-once":
            scheduler = SchedulerService(self.repo, TelegramClient())
            result = scheduler.run_due_jobs(datetime.now(timezone.utc))
            self._send_json(result, status=200)
            return

        self._send_json({"error": "not_found"}, status=404)


def run_server(db_path: str, host: str = "127.0.0.1", port: int = 8080) -> None:
    conn = connect(db_path)
    init_db(conn)
    repo = Repository(conn)

    class Handler(PanelHandler):
        pass

    Handler.repo = repo
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Panel avviato su http://{host}:{port} (db={db_path})")
    server.serve_forever()
