# Bancroft-Air Cleanup & Refactor — recovered plan

> Recovered 2026-06-24 from a prior session (transcript b2e64f39) that died mid-refactor.
> Phases 1–5 are complete in the working tree. **Phase 0 (tests) and the final
> Verification pass were never done.** Delete this file once the refactor is committed.

## Status

- [x] Phase 1 — Repo hygiene (requirements, delete index.OLD, .gitignore, service, shebangs)
- [x] Phase 2 — Backend de-dup: new `util.py` (average/setup_logging/READING_FIELDS), OFFICE_NODE, explicit CO2_HIGH_STREAK_SENSOR
- [x] Phase 3 — Remove legacy `current_reading` path; trim dead daily-summary params
- [x] Phase 4 — STATUS_THRESHOLDS + STALE_SECONDS single source of truth in config.py
- [x] Phase 5 — Frontend `static/shared.js` + window.BANCROFT bootstrap
- [x] **Phase 0 — pytest + ruff safety net (tests/ written: average, status, history-range, notifier — 32 tests)**
- [x] **Verification pass — ruff clean, 32 tests green, daemons import, /api/now + history-alias parity, templates render**

## Must-preserve (looks like a bug, isn't)

- `web_app.py` displays Wife's Office as **"Em's Office"** — keep the string.
- CO₂ streak thresholds differ by design: office `30` (10s cadence), MQTT `5` (60s) — both ≈ 5 min.

## Phase 0 — remaining tests to write (pure, deterministic, no hardware/network)

- `tests/test_average.py` — `util.average`: None-skipping, 2dp rounding, timestamp = last reading, keys default.
- `tests/test_status.py` — mirror JS `nodeStatus` boundaries for CO₂ (800/1000/1500) and PM2.5 (12/35/55) against `config.STATUS_THRESHOLDS`.
- `tests/test_history_range.py` — `db.get_history` range→table/alias mapping (`24h`→`1d`, `7d`→`1w`, `30d`→`1m`) against a temp seeded SQLite DB.
- `tests/test_notifier.py` — `Notifier.check_and_alert` with `_send` monkeypatched: critical fires immediately, high fires only at streak threshold, cooldown suppresses repeats.

## Verification checklist

1. `ruff check .` clean; `pytest` green.
2. `python3 sensor_daemon.py` + `python3 mqtt_listener.py` boot with no import/logging errors; reading round-trips into `node_current` + `readings_1min`.
3. `curl localhost:5000/api/now` returns all nodes incl. office; spot-check `/api/history?range=1d&node=office` and alias `range=24h`.
4. Load `/` and `/room/<node>` (kitchen for PM/eco2, office/bedroom for CO₂); status colors/hero/charts/pills identical; "Em's Office" label still shows.
5. Alerts: critical-immediate vs high-at-streak vs cooldown (covered by test_notifier).
