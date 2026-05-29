import json
import logging
import signal
import threading
import time
from datetime import date, datetime, timedelta

import paho.mqtt.client as mqtt
import smbus2

import config
import db
from display import OLEDDisplay
from notifier import Notifier
import web_app

logger = logging.getLogger(__name__)

_state: dict = {
    "timestamp": None,
    "co2_ppm": None,
    "temp_c": None,
    "humidity_pct": None,
    "pm25": None,
    "pm10": None,
}
_state_lock = threading.Lock()
_shutdown = threading.Event()


def _scd40_init(bus: smbus2.SMBus) -> None:
    msg = smbus2.i2c_msg.write(config.SCD40_ADDR, [0x3F, 0x86])
    bus.i2c_rdwr(msg)
    time.sleep(0.5)
    msg = smbus2.i2c_msg.write(config.SCD40_ADDR, [0x21, 0xB1])
    bus.i2c_rdwr(msg)
    time.sleep(5)
    logger.info("SCD40 initialized")


def _scd40_read(bus: smbus2.SMBus) -> tuple[float, float, float] | None:
    write_msg = smbus2.i2c_msg.write(config.SCD40_ADDR, [0xE4, 0xB8])
    bus.i2c_rdwr(write_msg)
    time.sleep(0.001)
    read_msg = smbus2.i2c_msg.read(config.SCD40_ADDR, 3)
    bus.i2c_rdwr(read_msg)
    status = list(read_msg)
    if not (status[1] & 0x07):
        return None

    write_msg = smbus2.i2c_msg.write(config.SCD40_ADDR, [0xEC, 0x05])
    bus.i2c_rdwr(write_msg)
    time.sleep(0.001)
    read_msg = smbus2.i2c_msg.read(config.SCD40_ADDR, 9)
    bus.i2c_rdwr(read_msg)
    data = list(read_msg)

    co2 = float((data[0] << 8) | data[1])
    temp_raw = (data[3] << 8) | data[4]
    temp_c = -45.0 + 175.0 * temp_raw / 65535.0
    hum_raw = (data[6] << 8) | data[7]
    humidity = 100.0 * hum_raw / 65535.0

    return co2, temp_c, humidity


def _pms5003_read(ser) -> tuple[float, float] | None:
    ser.reset_input_buffer()
    deadline = time.monotonic() + 5.0

    synced = False
    while time.monotonic() < deadline:
        b = ser.read(1)
        if not b:
            continue
        if b == b"\x42":
            b2 = ser.read(1)
            if b2 == b"\x4D":
                synced = True
                break

    if not synced:
        return None

    rest = ser.read(30)
    if len(rest) < 30:
        return None

    frame = b"\x42\x4D" + rest
    checksum = sum(frame[:-2])
    expected = (frame[-2] << 8) | frame[-1]
    if checksum != expected:
        logger.warning("PMS5003 checksum mismatch")
        return None

    # Atmospheric concentration values (standard for indoor air quality)
    pm25 = float((rest[10] << 8) | rest[11])
    pm10 = float((rest[12] << 8) | rest[13])
    return pm25, pm10


def _average(readings: list[dict], node: str = "office") -> dict:
    keys = ["co2_ppm", "temp_c", "humidity_pct", "pm25", "pm10"]
    result: dict = {}
    for k in keys:
        vals = [r[k] for r in readings if r.get(k) is not None]
        result[k] = round(sum(vals) / len(vals), 2) if vals else None
    result["timestamp"] = readings[-1]["timestamp"]
    result["node"] = node
    return result


def _mqtt_connect() -> mqtt.Client | None:
    """Create and connect an MQTT client; return None on failure (non-fatal)."""
    try:
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=60)
        client.loop_start()
        logger.info("MQTT connected to %s:%d", config.MQTT_BROKER, config.MQTT_PORT)
        return client
    except Exception as e:
        logger.warning("MQTT connect failed (will retry on next 1min write): %s", e)
        return None


def _compute_daily_summary(target_date: date, node: str = "office") -> dict | None:
    readings = db.get_readings_for_date(target_date, node=node)
    if not readings:
        return None

    co2_vals = [r["co2_ppm"] for r in readings if r.get("co2_ppm") is not None]
    temp_vals = [r["temp_c"] for r in readings if r.get("temp_c") is not None]
    hum_vals = [r["humidity_pct"] for r in readings if r.get("humidity_pct") is not None]
    pm25_vals = [r["pm25"] for r in readings if r.get("pm25") is not None]
    pm10_vals = [r["pm10"] for r in readings if r.get("pm10") is not None]

    if not co2_vals:
        return None

    co2_max = max(co2_vals)
    co2_max_reading = max(
        (r for r in readings if r.get("co2_ppm") is not None),
        key=lambda r: r["co2_ppm"],
    )
    co2_max_time = co2_max_reading["timestamp"][11:16]

    return {
        "date": target_date.isoformat(),
        "co2_avg": round(sum(co2_vals) / len(co2_vals), 1),
        "co2_max": round(co2_max, 0),
        "co2_max_time": co2_max_time,
        "temp_avg": round(sum(temp_vals) / len(temp_vals), 1) if temp_vals else None,
        "humidity_avg": round(sum(hum_vals) / len(hum_vals), 1) if hum_vals else None,
        "pm25_avg": round(sum(pm25_vals) / len(pm25_vals), 1) if pm25_vals else None,
        "pm25_max": round(max(pm25_vals), 0) if pm25_vals else None,
        "pm10_avg": round(sum(pm10_vals) / len(pm10_vals), 1) if pm10_vals else None,
        "pm10_max": round(max(pm10_vals), 0) if pm10_vals else None,
    }


def sensor_loop(notifier: Notifier) -> None:
    import serial

    bus = smbus2.SMBus(config.I2C_BUS)
    ser = serial.Serial(config.PMS5003_PORT, config.PMS5003_BAUD, timeout=2)

    try:
        _scd40_init(bus)
    except Exception as e:
        logger.error("SCD40 init failed: %s", e)

    mqtt_client = _mqtt_connect()

    accum_1min: list[dict] = []
    accum_10min: list[dict] = []
    last_1min_write = datetime.now()
    last_10min_write = datetime.now()
    co2_high_streak = 0
    pm_elevated_streak = 0
    # Seed from DB so a daemon restart after 08:00 doesn't re-send the daily summary.
    _latest_summary = db.get_latest_summary_date()
    now_startup = datetime.now()
    last_summary_date: date | None = (
        now_startup.date()
        if _latest_summary is not None and _latest_summary >= (now_startup.date() - timedelta(days=1))
        and now_startup.hour >= config.SUMMARY_HOUR
        else None
    )

    try:
        while not _shutdown.is_set():
            loop_start = time.monotonic()
            now = datetime.now()

            scd = None
            pms = None
            try:
                scd = _scd40_read(bus)
            except Exception as e:
                logger.error("SCD40 read error: %s", e)
            try:
                pms = _pms5003_read(ser)
            except Exception as e:
                logger.error("PMS5003 read error: %s", e)

            if scd or pms:
                co2, temp_c, humidity = scd if scd else (None, None, None)
                pm25, pm10 = pms if pms else (None, None)

                reading = {
                    "timestamp": now.isoformat(timespec="seconds"),
                    "co2_ppm": co2,
                    "temp_c": round(temp_c, 2) if temp_c is not None else None,
                    "humidity_pct": round(humidity, 2) if humidity is not None else None,
                    "pm25": pm25,
                    "pm10": pm10,
                    "node": "office",
                }

                with _state_lock:
                    _state.update(reading)

                accum_1min.append(reading)
                accum_10min.append(reading)

                if co2 is not None and co2 > config.CO2_WARN_PPM:
                    co2_high_streak += 1
                else:
                    co2_high_streak = 0

                pm25_val = pm25 or 0
                pm10_val = pm10 or 0
                if pm25_val > config.PM25_WARN or pm10_val > config.PM10_WARN:
                    pm_elevated_streak += 1
                else:
                    pm_elevated_streak = 0

                try:
                    db.upsert_current(reading)
                    db.upsert_node_current(reading)
                except Exception as e:
                    logger.error("DB upsert error: %s", e)

                try:
                    notifier.check_and_alert(reading, co2_high_streak, pm_elevated_streak, node="office")
                except Exception as e:
                    logger.error("Notifier error: %s", e)

                logger.debug(
                    "CO2=%s pm25=%s pm10=%s temp=%s hum=%s co2_streak=%d pm_streak=%d",
                    f"{co2:.0f}" if co2 is not None else "N/A",
                    f"{pm25:.0f}" if pm25 is not None else "N/A",
                    f"{pm10:.0f}" if pm10 is not None else "N/A",
                    f"{temp_c:.1f}" if temp_c is not None else "N/A",
                    f"{humidity:.1f}" if humidity is not None else "N/A",
                    co2_high_streak,
                    pm_elevated_streak,
                )
            else:
                co2_high_streak = 0
                pm_elevated_streak = 0

            if (now - last_1min_write).total_seconds() >= 60 and accum_1min:
                avg = _average(accum_1min, node="office")
                try:
                    db.insert_reading("readings_1min", avg)
                    logger.info("Wrote 1min avg (%d readings)", len(accum_1min))
                except Exception as e:
                    logger.error("DB 1min insert error: %s", e)

                # Publish to MQTT; reconnect lazily if needed
                try:
                    if mqtt_client is None:
                        mqtt_client = _mqtt_connect()
                    if mqtt_client is not None:
                        payload = json.dumps({
                            "node":      "office",
                            "co2":       avg["co2_ppm"],
                            "temp_c":    avg["temp_c"],
                            "humidity":  avg["humidity_pct"],
                            "pm25":      avg["pm25"],
                            "pm10":      avg["pm10"],
                            "timestamp": avg["timestamp"],
                        })
                        mqtt_client.publish(config.MQTT_TOPIC_PUBLISH, payload, qos=0)
                        logger.debug("MQTT published to %s", config.MQTT_TOPIC_PUBLISH)
                except Exception as e:
                    logger.warning("MQTT publish failed: %s", e)
                    mqtt_client = None  # will reconnect next cycle

                accum_1min.clear()
                last_1min_write = now

            if (now - last_10min_write).total_seconds() >= 600 and accum_10min:
                try:
                    db.insert_reading("readings_10min", _average(accum_10min, node="office"))
                    logger.info("Wrote 10min avg (%d readings)", len(accum_10min))
                except Exception as e:
                    logger.error("DB 10min insert error: %s", e)
                accum_10min.clear()
                last_10min_write = now

            if now.hour >= config.SUMMARY_HOUR and last_summary_date != now.date():
                yesterday = now.date() - timedelta(days=1)
                try:
                    summaries = {}
                    for node in config.NODES:
                        s = _compute_daily_summary(yesterday, node=node)
                        if s:
                            summaries[node] = s
                    if summaries:
                        if "office" in summaries:
                            db.insert_daily_summary(summaries["office"])
                        notifier.send_daily_summary(summaries)
                        logger.info("Daily summary sent for %s (%d nodes)", yesterday, len(summaries))
                except Exception as e:
                    logger.error("Daily summary error: %s", e)
                last_summary_date = now.date()

            elapsed = time.monotonic() - loop_start
            _shutdown.wait(max(0.0, config.SENSOR_READ_INTERVAL_SEC - elapsed))
    finally:
        bus.close()
        ser.close()
        if mqtt_client is not None:
            try:
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
            except Exception:
                pass


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(threadName)s %(levelname)s %(message)s",
    )

    db.init_db()
    notifier = Notifier()

    disp = OLEDDisplay(_state, _state_lock)
    display_thread = threading.Thread(target=disp.run, name="display", daemon=True)
    display_thread.start()

    flask_app = web_app.create_app(_state, _state_lock)
    flask_thread = threading.Thread(
        target=flask_app.run,
        kwargs={"host": "0.0.0.0", "port": 5000, "debug": False, "use_reloader": False},
        name="flask",
        daemon=True,
    )
    flask_thread.start()
    logger.info("Flask started on port 5000")

    def _handle_signal(signum, frame):
        logger.info("Signal %s received, shutting down", signum)
        _shutdown.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info("bancroft-air sensor loop starting")
    sensor_loop(notifier)
    logger.info("bancroft-air stopped")


if __name__ == "__main__":
    main()
