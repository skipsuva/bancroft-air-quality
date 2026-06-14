# bancroft-air

Multi-room air quality monitor. The Pi Zero 2W (office node) reads CO₂, temperature, humidity (SCD40) and AQI/TVOC (ENS160). ESP32 room nodes publish via MQTT. All nodes persist to SQLite on the Pi, served by a Flask web dashboard, with ntfy.sh alerts on threshold breaches.

Keep the design simple — this is a home system, not a product.

---

## Hardware (office node — Pi Zero 2W)

| Device | Interface | Address/Port |
|---|---|---|
| SCD40 | I²C | 0x62 on /dev/i2c-1 |
| ENS160 | I²C | 0x53 on /dev/i2c-1 |
| SH1106 OLED 128×64 | I²C | 0x3C on /dev/i2c-1 (listed as SSD1306, requires sh1106 driver) |

User `skipsuva` is in `i2c`, `dialout`, `gpio` groups — no sudo needed at runtime.

The office node no longer has a PMS5003. PM data comes from the kitchen node (ESP32).

---

## Nodes

| Node | Label | Sensors |
|---|---|---|
| `office` | Office | SCD40 + ENS160 (Pi, this device) |
| `bedroom` | Bedroom | SCD40 + ENS160 (ESP32) |
| `toddler` | Mari's Room | SCD40 + ENS160 (ESP32) |
| `wifesoffice` | Wife's Office | SCD40 + ENS160 (ESP32) |
| `basement` | Basement | SCD40 only (ESP32) |
| `kitchen` | Kitchen | ENS160 + PMS5003, no SCD40 — eco2 used as CO₂ proxy (ESP32) |

`NODE_SENSORS` in `config.py` is the authoritative per-node capability map. The derived lists `ENS160_NODES`, `PM_NODES`, `ECO2_NODES` are used by the web app to conditionally render columns.

ESP32 nodes publish to `bancroft/<node>/readings` every 60 seconds.

---

## Running

Two systemd services must both be running:

```bash
# Main sensor daemon (office node + Flask)
sudo cp bancroft-air.service /etc/systemd/system/
sudo systemctl enable --now bancroft-air

# MQTT listener (ESP32 nodes)
sudo cp mqtt_listener.service /etc/systemd/system/
sudo systemctl enable --now mqtt_listener
```

Flask dashboard at `http://localhost:5000`.

**Logs:**
```bash
journalctl -u bancroft-air -f
journalctl -u mqtt_listener -f
```

**Dependencies:**
```bash
sudo apt install python3-flask python3-smbus2 python3-serial python3-requests python3-luma.oled python3-paho-mqtt
```

`paho-mqtt` is required for both services. `requirements.txt` lists Python deps for reference.

---

## Architecture

**`bancroft-air` service** — single process, three threads:

```
main thread      sensor_loop() — reads SCD40 + ENS160 every 10s, writes SQLite, fires alerts, publishes to MQTT
display thread   OLEDDisplay.run() — cycles OLED screens every 5s
flask thread     Flask dev server on port 5000 (daemon=True, use_reloader=False)
```

**`mqtt_listener` service** — separate process:

```
main thread      paho loop_forever() — receives ESP32 readings, persists to SQLite, fires alerts
```

Shared state in `sensor_daemon.py`: `_state: dict` + `_state_lock: threading.Lock`. Both the display thread and Flask read from it. Lock held briefly (copy and release) — never during I/O.

MQTT broker is Mosquitto running locally at `localhost:1883`. The office node publishes its own 1-min averages to `bancroft/office/readings`; `mqtt_listener` skips that topic to avoid double-writing.

---

## File Map

| File | Role |
|---|---|
| `sensor_daemon.py` | Main entrypoint. SCD40 + ENS160 reads, averaging, MQTT publish, thread startup |
| `mqtt_listener.py` | MQTT subscriber. Receives ESP32 readings, persists 1min/10min averages, fires alerts |
| `config.py` | All constants — thresholds, node definitions, hardware addresses, MQTT config, timing |
| `db.py` | All SQLite logic. Every function opens/closes its own connection (WAL mode, never share across threads) |
| `display.py` | `OLEDDisplay` class. Uses luma.oled sh1106 driver. Gracefully skips if hardware absent |
| `notifier.py` | `Notifier` class. ntfy.sh POST with per-node, per-condition 30-min cooldown |
| `web_app.py` | Flask factory `create_app(state, lock)`. Routes: `/`, `/api/now`, `/api/history` |
| `templates/index.html` | Single-file dashboard. Chart.js from CDN |
| `bancroft-air.service` | systemd unit for sensor_daemon |
| `mqtt_listener.service` | systemd unit for mqtt_listener |
| `air_quality.db` | SQLite database (auto-created on first run) |

---

## Database

Five tables in `air_quality.db`:

| Table | Retention | Purpose |
|---|---|---|
| `readings_1min` | 7 days | 1-minute averages per node |
| `readings_10min` | forever | 10-minute averages per node |
| `daily_summaries` | forever | Generated at 08:00, office node only |
| `current_reading` | single row (id=1) | Legacy office-only fallback for `/api/now` |
| `node_current` | one row per node | Latest reading per node, upserted on every message |

`readings_1min` and `readings_10min` schema: `id, timestamp, co2_ppm, temp_c, humidity_pct, pm25, pm10, node, aqi, tvoc, eco2`. Nullable columns are used selectively per node capability.

`node_current` schema: `node (PK), timestamp, co2_ppm, temp_c, humidity_pct, pm25, pm10, aqi, tvoc, eco2`.

`db.py` has a `_migrate()` function that adds new columns to existing tables at startup — safe to run repeatedly.

**SQLite rules:**
- Never pass a `sqlite3.Connection` across threads — open a new one per call
- `sqlite3.Row` is not JSON-serializable — `db.py` always returns plain `dict`
- WAL mode is set on every new connection

---

## Sensor Protocols

### SCD40 (I²C)

**Critical:** Use `bus.i2c_rdwr(smbus2.i2c_msg.write(...))` — NOT `write_i2c_block_data`. The Adafruit CircuitPython library is incompatible with Python 3.13.

Init sequence (once on startup):
1. Write `[0x3F, 0x86]` — stop periodic measurement (handles restarts cleanly)
2. Sleep 500ms
3. Write `[0x21, 0xB1]` — start periodic measurement
4. Sleep 5s — first measurement takes ~5s

Read sequence (every 10s):
1. Write `[0xE4, 0xB8]` + read 3 bytes — check `bytes[1] & 0x07`; if 0, data not ready, return None
2. Write `[0xEC, 0x05]` + read 9 bytes
3. Parse: `co2 = (b[0]<<8)|b[1]`, `temp = -45 + 175*(b[3]<<8|b[4])/65535`, `hum = 100*(b[6]<<8|b[7])/65535`
4. Bytes 2, 5, 8 are CRC (currently not validated)

### ENS160 (I²C)

Init: set mode register `0x10` to `0xF0` (reset), then `0x02` (normal). Read sequence polls status register `0x20` — retry up to 3 times if status is `0x03` (warming up). AQI at `0x21` (1 byte, 1–5 scale), TVOC at `0x22` (2 bytes, little-endian, ppb).

`write_i2c_block_data` is fine here (unlike SCD40).

### PMS5003 (UART) — kitchen node only, handled on ESP32

For reference: 32-byte frames at ~1Hz. Sync to `0x42 0x4D` header. Atmospheric PM values at frame bytes 12–15.

---

## Alert Thresholds

| Condition | Trigger | Streak required | Priority |
|---|---|---|---|
| CO₂ elevated | >1000 ppm | 5 readings (MQTT: 5 min at 60s/reading; sensor_daemon: 5 min at 10s × 30 readings) | default |
| CO₂ critical | >1500 ppm | immediate | high |
| Daily summary | 08:00 local time | — | low |

Alerts are per-node — cooldown keys are `co2_critical:<node>` and `co2_high:<node>`.

**Streak thresholds differ by source:**
- `sensor_daemon.py` (office): `co2_high_streak >= 30` (30 × 10s = 5 min)
- `mqtt_listener.py` (ESP32 nodes): `co2_high_streak >= 5` (5 × 60s = 5 min) — `CO2_HIGH_STREAK_MQTT = 5` in config

PM2.5/PM10 thresholds have been removed; no node that currently alerts on PM is implemented.

Cooldown: 30 minutes per condition+node key.

**ntfy topic:** `bancroft-air` on `https://ntfy.sh`.

Daily summary covers all nodes with data; formatted as one ntfy message.

---

## Web API

- `GET /api/now` — dict keyed by node name; each value is a 5-minute smoothed average (falls back to raw `node_current`, then in-memory state for office)
- `GET /api/history?range=<range>&node=<node>&smooth=1` — array of readings
  - Ranges: `2h`, `6h`, `1d` (uses `readings_1min`); `1w`, `1m` (uses `readings_10min`); `3m`, `6m` (hourly buckets from `readings_10min`); `1y`, `all` (uses `daily_summaries`, office only)
  - `node` param filters to one node; omit for all nodes
  - `smooth=1` forces `readings_10min` for short ranges
  - Legacy aliases: `24h`→`1d`, `7d`→`1w`, `30d`→`1m`
