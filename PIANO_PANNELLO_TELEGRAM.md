# Piano prodotto: pannello per bot Telegram con pubblicazione programmata

## 1) Obiettivo
Creare un **pannello web** per gestire un bot Telegram che pubblica contenuti (newsletter, offerte, annunci) in modo **programmato** su gruppi/canali aggiunti dal pannello.

## 2) Problema che risolve
- Evita invii manuali ripetitivi.
- Riduce errori di timing e dimenticanze.
- Centralizza gestione gruppi, template e calendario post.
- Permette controllo editoriale (bozza, approvazione, storico).

## 3) Utenti principali
1. **Admin**: configura bot, gruppi, utenti, permessi.
2. **Editor marketing**: crea contenuti e pianifica invii.
3. **Revisore (opzionale)**: approva prima della pubblicazione.

## 4) Funzionalità core (MVP)

### 4.1 Gestione bot e gruppi
- Collegamento bot via token (salvato cifrato).
- Procedura guidata per aggiungere gruppi/canali:
  - aggiungi bot come admin nel gruppo/canale,
  - conferma dal pannello tramite comando o deep-link,
  - acquisizione `chat_id` e metadati.
- Stato gruppo: attivo, sospeso, errore permessi.

### 4.2 Composizione contenuti
- Editor messaggi con:
  - testo, emoji, markdown/HTML Telegram,
  - immagini/video/documenti,
  - pulsanti inline (link CTA),
  - anteprima messaggio.
- Template riutilizzabili (es. “offerta lampo”, “newsletter settimanale”).

### 4.3 Scheduling
- Pianificazione singola o ricorrente (giornaliera, settimanale, cron semplice).
- Timezone per workspace (es. Europe/Rome).
- Finestra silenzio (es. non pubblicare di notte).
- Retry automatico in caso di errore temporaneo Telegram.

### 4.4 Distribuzione
- Selezione multipla gruppi/canali target.
- Segmenti (es. “Clienti premium”, “Offerte locali”).
- Invio test su chat interna prima della pubblicazione reale.

### 4.5 Monitoraggio
- Storico invii con stato: pianificato, inviato, fallito.
- Log errori Telegram (permesso mancante, flood control, ecc.).
- Metriche base: numero invii, successo/fallimento per gruppo.

## 5) Architettura consigliata

### 5.1 Stack suggerito (pragmatico)
- **Frontend**: Next.js + UI kit (shadcn/ui o simile).
- **Backend API**: Node.js (NestJS o Express + TypeScript).
- **DB**: PostgreSQL.
- **Queue/Scheduler**: Redis + BullMQ (job pianificati affidabili).
- **Storage media**: S3-compatible (es. Cloudflare R2, MinIO).
- **Deploy**: Docker + VPS/Cloud.

### 5.2 Moduli backend
1. **Auth & RBAC** (admin/editor/reviewer).
2. **Telegram Connector** (SDK Bot API, webhook, sendMessage/sendMediaGroup).
3. **Content Service** (bozze, template, validazione).
4. **Scheduler Service** (job queue, retry, deduplica).
5. **Delivery Service** (invio ai target + tracking stato).
6. **Analytics Service** (report base).

## 6) Modello dati (essenziale)
- `users` (id, email, role, password_hash)
- `workspaces` (id, name, timezone)
- `telegram_bots` (id, workspace_id, encrypted_token, status)
- `targets` (id, workspace_id, chat_id, title, type[group|channel], status)
- `segments` (id, workspace_id, name)
- `segment_targets` (segment_id, target_id)
- `templates` (id, workspace_id, name, body, media_schema)
- `campaigns` (id, workspace_id, title, status[draft|approved|scheduled|sent|failed])
- `campaign_targets` (campaign_id, target_id)
- `schedules` (id, campaign_id, run_at, recurrence_rule, timezone)
- `deliveries` (id, campaign_id, target_id, telegram_message_id, status, error, sent_at)
- `audit_logs` (id, actor_id, action, entity, created_at)

## 7) Flusso operativo ideale
1. Admin collega il bot e imposta timezone workspace.
2. Admin aggiunge gruppi/canali e verifica permessi.
3. Editor crea campagna da template o da zero.
4. (Opzionale) Revisore approva la campagna.
5. Editor pianifica invio e seleziona target/segmenti.
6. Scheduler inserisce job in coda.
7. Worker invia a Telegram con controllo errori/retry.
8. Dashboard mostra esiti, errori e suggerimenti correttivi.

## 8) Sicurezza e compliance
- Cifratura token bot (AES + secret management).
- RBAC rigoroso e audit log azioni critiche.
- Rate limiting e gestione `429 Too Many Requests` Telegram.
- Backup DB giornaliero.
- Mascheramento dati sensibili nei log.
- Informativa privacy (se tracci utenti/clienti via link).

## 9) Rischi principali e mitigazioni
- **Flood limit Telegram** → coda con throttling per chat/bot.
- **Bot rimosso da gruppo** → health check periodico + alert.
- **Errori formato markdown** → validator + preview realistica.
- **Doppio invio** → idempotency key per delivery.

## 10) Roadmap proposta (6 settimane)

### Settimana 1
- Setup repo, CI, auth base, schema DB iniziale.

### Settimana 2
- Integrazione bot Telegram + onboarding gruppi.

### Settimana 3
- Editor contenuti + template + upload media.

### Settimana 4
- Scheduling con BullMQ + ricorrenza + retry.

### Settimana 5
- Dashboard storico invii + error center.

### Settimana 6
- Hardening sicurezza, test E2E, rilascio beta.

## 11) Backlog post-MVP
- A/B test messaggi.
- Multi-bot per workspace.
- UTM builder e tracking conversioni.
- AI assistant per generare copy offerte.
- Approvazione a due livelli (4-eyes principle).

## 12) KPI per misurare successo
- % invii riusciti > 98%.
- Tempo medio creazione campagna < 5 minuti.
- Riduzione errori manuali invio > 70%.
- Tempo risoluzione errori critici < 30 minuti.

## 13) Bozza UX del pannello
- **Dashboard**: campagne oggi, prossimi invii, errori aperti.
- **Campagne**: lista + stato + pulsante “Nuova campagna”.
- **Editor campagna**: contenuto, media, pulsanti, anteprima.
- **Target**: gruppi/canali, segmenti, stato connessione.
- **Pianificazione**: calendario + ricorrenza + timezone.
- **Log & Audit**: cronologia invii e azioni utenti.

## 14) Prossimo passo operativo
Costruire un **MVP tecnico** con 3 user story prioritarie:
1. Creare campagna e salvarla in bozza.
2. Pianificare invio a gruppi selezionati.
3. Eseguire invio schedulato con log di successo/fallimento.

Questo permette una demo reale già dalla quarta settimana.
