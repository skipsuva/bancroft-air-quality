# bancroft-air

Raspberry Pi Zero 2W air quality monitor for a home office. Reads CO₂, temperature, humidity (SCD40), and PM2.5/PM10 (PMS5003). Displays readings on an SH1106 OLED, persists to SQLite, serves a web dashboard via Flask, and sends ntfy.sh alerts on threshold breaches.

This is node 1 of a planned multi-room system. Future nodes are ESP32-based. Keep the design simple — don't over-engineer for that future.

---

## Hardware

| Device | Interface | Address/Port |
|---|---|---|
| SCD40 | I²C | 0x62 on /dev/i2c-1 |
| PMS5003 | UART | /dev/serial0, 9600 baud |
| SH1106 OLED 128×64 | I²C | 0x3C on /dev/i2c-1 (listed as SSD1306, requires sh1106 driver) |

User `skipsuva` is in `i2c`, `dialout`, `gpio` groups — no sudo needed at runtime.

---

## Running

```bash
python3 sensor_daemon.py
```

Flask dashboard at `http://localhost:5000`. The systemd service (`bancroft-air.service`) runs this on boot.

**Install service:**
```bash
sudo cp bancroft-air.service /etc/systemd/system/
sudo systemctl enable --now bancroft-air
```

**Logs:**
```bash
journalctl -u bancroft-air -f
```

**Dependencies** — all installed as system apt packages:
```bash
sudo apt install python3-flask python3-smbus2 python3-serial python3-requests python3-luma.oled
```

---

## Architecture

Single process, three threads:

```
main thread      sensor_loop() — reads sensors every 10s, writes SQLite, fires alerts
display thread   OLEDDisplay.run() — cycles OLED screens every 5s
flask thread     Flask dev server on port 5000 (daemon=True, use_reloader=False)
```

Shared state is `_state: dict` + `_state_lock: threading.Lock` defined at module level in `sensor_daemon.py`. Both the display thread and Flask read from it. Lock is held only briefly (copy and release) — never during I/O.

---

## File Map

| File | Role |
|---|---|
| `sensor_daemon.py` | Main entrypoint. Sensor loop, SCD40/PMS5003 reads, averaging, thread startup |
| `config.py` | All constants — thresholds, paths, hardware addresses, timing |
| `db.py` | All SQLite logic. Every function opens/closes its own connection (WAL mode, never share across threads) |
| `display.py` | `OLEDDisplay` class. Uses luma.oled sh1106 driver. Gracefully skips if hardware absent |
| `notifier.py` | `Notifier` class. ntfy.sh POST with per-condition 30-min cooldown dict |
| `web_app.py` | Flask factory `create_app(state, lock)`. Routes: `/`, `/api/now`, `/api/history` |
| `templates/index.html` | Single-file dashboard. Chart.js from CDN, 10s auto-refresh |
| `bancroft-air.service` | systemd unit |
| `air_quality.db` | SQLite database (auto-created on first run) |

---

## Database

Four tables in `air_quality.db`:

| Table | Retention | Purpose |
|---|---|---|
| `readings_1min` | 7 days | 1-minute averages, used by `/api/history?range=24h` |
| `readings_10min` | forever | 10-minute averages, used by `7d`/`30d` history |
| `daily_summaries` | forever | Generated at 08:00 for the previous day |
| `current_reading` | single row (id=1) | Latest raw reading, upserted every 10s for `/api/now` |

All tables share the same schema: `id, timestamp, co2_ppm, temp_c, humidity_pct, pm25, pm10`.

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

### PMS5003 (UART)

32-byte frames at ~1Hz. **Never** read blindly with `ser.read(32)` — always sync to the frame header first. Always call `ser.reset_input_buffer()` before reading to discard stale buffered data.

Frame sync pattern:
```python
ser.reset_input_buffer()
while True:
    b = ser.read(1)
    if b == b'\x42' and ser.read(1) == b'\x4D':
        break
rest = ser.read(30)  # remaining 30 bytes of the 32-byte frame
```

After syncing, atmospheric PM values are at:
- `pm25 = (rest[10] << 8) | rest[11]`  (frame bytes 12–13)
- `pm10 = (rest[12] << 8) | rest[13]`  (frame bytes 14–15)

Checksum: `sum(frame[:-2]) == (frame[-2] << 8) | frame[-1]`

---

## Alert Thresholds (`config.py`)

| Condition | Trigger | Priority |
|---|---|---|
| CO₂ high | >1000 ppm for 5+ min (30 consecutive 10s readings) | default |
| CO₂ critical | >1500 ppm | high |
| PM2.5 elevated | >25 µg/m³ | default |
| PM2.5 unhealthy | >55 µg/m³ | high |
| Daily summary | 08:00 local time | low |

Cooldown: 30 minutes per condition key. `co2_high_streak` resets to 0 on any missed reading (not just clean readings).

---

## Web API

- `GET /api/now` — current reading as JSON (from `current_reading` table, falls back to in-memory state)
- `GET /api/history?range=24h|7d|30d` — array of averaged readings; `24h` uses `readings_1min`, `7d`/`30d` use `readings_10min`
