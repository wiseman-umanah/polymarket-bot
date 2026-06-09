# Changelog

All notable changes to PolyShock are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- **Poll broadcasting** — `/poll Question | Option A | Option B` sends a native
  Telegram poll to all subscribers. Votes are forwarded to the admin chat in
  real time with username and choice. First vote per user is final; subsequent
  changes are silently ignored. Admin-only command, hidden from regular users.
- **Conversational market search** — tapping 🔍 Search Market now prompts for a
  keyword instead of showing a command hint; reply routes directly through the
  agent's `search_markets` tool.
- **My Stats inline settings** — stats view now shows the settings keyboard
  inline so users can change preferences immediately without a separate tap.

---

## [0.3.0] - 2026-06-09

### Added
- **LLM agent** — free-text Q&A powered by Groq (llama-3.3-70b-versatile).
  Users can ask questions in plain language; the bot answers using live market data.
- **Conversational settings** — users can update their alert preferences through
  natural language ("set my filter to strong", "mute alerts from 11pm to 6am").
- **Personalized recommendations** — `get_recommendations` surfaces markets
  related to what the user has previously searched, scored by price movement and
  filtered by their volume preference.
- **Per-user rate limiting** — agent requests capped at 5 per minute per user
  (configurable via `AGENT_RATE_LIMIT`).
- New config vars: `GROQ_API_KEY`, `AGENT_MODEL`, `AGENT_RATE_LIMIT`.

### Changed
- **Database layer fully rewritten** — raw dual-backend SQL replaced with
  SQLModel/SQLAlchemy async ORM. Supports Postgres and SQLite with one codebase;
  all existing call-site APIs preserved (dict-based return types unchanged).
- Window-function queries (`ROW_NUMBER OVER PARTITION BY`) replace backend-specific
  `DISTINCT ON` / `LATERAL JOIN` / SQLite subquery pairs throughout.

### Removed
- `bot/db/core.py` — old raw-SQL `Database` class with separate Postgres/SQLite
  code paths. Replaced by `bot/db/engine.py` + `bot/db/models.py`.

### Fixed
- `BigInteger` autoincrement primary keys now use `with_variant(Integer, "sqlite")`
  to avoid `NOT NULL constraint failed` on SQLite (SQLite only autoincrements
  `INTEGER PRIMARY KEY`, not `BIGINT`).
- Added `idx_alerts_market_signal_time` index — the cooldown check (`get_last_alert`)
  was doing a full table scan on every market every poll cycle (~300/min). Now an
  index seek.
- Added `idx_snapshots_ts` index for efficient timestamp-range deletes in
  `prune_old_snapshots` (the existing `(market_id, timestamp)` index couldn't be
  used for a timestamp-only `WHERE` clause).

---

## [0.2.0] - 2026-06-04

### Added
- **Multi-user support** — subscribers table, per-user preferences (signal filter,
  quiet hours, min volume, price threshold), admin-only commands.
- **Persistent reply keyboard** — category buttons always visible below the input box.
- **Inline settings menus** — numeric keypad + enum selector for tap-driven
  settings changes; unsubscribe feedback flow.
- **Reset all settings** button — returns all preferences to global defaults.
- **Admin log handler** — errors and above are forwarded to the admin chat via
  Telegram in real time.
- **Webhook support** — `WEBHOOK_URL` / `WEBHOOK_SECRET` / `PORT` config vars;
  falls back to polling when unset.
- `LOG_LEVEL` config var.

### Removed
- Health check HTTP server (replaced by Railway's built-in health checks).

---

## [0.1.0] - 2026-05-01

### Added
- Initial release — single-user Polymarket monitoring bot.
- Polls top-100 active markets every 30 seconds via the Gamma API.
- Three signal detectors: price movement (≥4%), volume spike (≥2× average),
  strong signal (both together).
- 15-minute per-market cooldown stored in SQLite.
- `/start`, `/stop`, `/status`, `/thresholds` commands.
- SQLite (local) and PostgreSQL (Railway) dual-backend support.
