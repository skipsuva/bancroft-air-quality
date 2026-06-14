"""
mqtt_listener.py — Bancroft Air MQTT Listener

Subscribes to bancroft/+/readings, receives JSON payloads from ESP32 room nodes,
and persists 1-minute and 10-minute averages to SQLite.

Each ESP32 publishes every 60 seconds, so each arriving message is treated as a
1-minute sample and written directly to readings_1min.  A per-node accumulator
drives the 10-minute average writes (flush after ≥ 600 seconds per node).

Most ESP32 nodes have SCD40 + ENS160 only (no PMS5003), so pm25/pm10 are NULL.
The kitchen node is an exception: it has ENS160 + PMS5003 but no SCD40, so
co2_ppm is NULL and eco2 is used as the CO₂ proxy.

Run via mqtt_listener.service; logs go to stdout (captured by journald).
"""

import json
import logging
import signal
import time
from datetime import datetime

import paho.mqtt.client as mqtt

import config
import db
from notifier import Notifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Per-node state for 10-minute averaging and streak tracking
# { node: {"accum": [...], "last_write": datetime, "co2_high_streak": int} }
_node_state: dict[str, dict] = {}

_notifier = Notifier()
_shutdown = False


def _handle_message(client, userdata, msg) -> None:
    """Callback: called by paho network thread on each received message."""
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning("Bad payload on %s: %s", msg.topic, e)
        return

    node = payload.get("node")
    if not node:
        # Try to extract node from topic (bancroft/<node>/readings)
        parts = msg.topic.split("/")
        node = parts[1] if len(parts) >= 2 else "unknown"

    if node == "office":
        # Office publishes its own readings; the sensor_daemon owns that node.
        # Skip to avoid double-writing.
        return

    co2       = payload.get("co2")
    temp_c    = payload.get("temp_c")
    humidity  = payload.get("humidity")
    aqi       = payload.get("aqi")
    tvoc      = payload.get("tvoc")
    eco2      = payload.get("eco2")
    pm25      = payload.get("pm25")
    pm10      = payload.get("pm10")
    timestamp = payload.get("timestamp") or datetime.now().isoformat(timespec="seconds")

    reading = {
        "node":         node,
        "timestamp":    timestamp,
        "co2_ppm":      float(co2)      if co2      is not None else None,
        "temp_c":       float(temp_c)   if temp_c   is not None else None,
        "humidity_pct": float(humidity) if humidity is not None else None,
        "pm25":         float(pm25)     if pm25     is not None else None,
        "pm10":         float(pm10)     if pm10     is not None else None,
        "aqi":          int(aqi)        if aqi      is not None else None,
        "tvoc":         int(tvoc)       if tvoc     is not None else None,
        "eco2":         int(eco2)       if eco2     is not None else None,
    }

    logger.info(
        "node=%-12s  CO2=%s  temp=%.1f°C  hum=%.1f%%",
        node,
        f"{co2:.0f}" if co2 is not None else "N/A",
        temp_c   if temp_c   is not None else 0.0,
        humidity if humidity is not None else 0.0,
    )

    # Persist as 1-minute reading immediately
    try:
        db.insert_reading("readings_1min", reading)
        db.upsert_node_current(reading)
    except Exception as e:
        logger.error("DB insert error for node %s: %s", node, e)
        return

    # Accumulate for 10-minute average and track CO₂ streak for alerting
    if node not in _node_state:
        _node_state[node] = {"accum": [], "last_write": datetime.now(), "co2_high_streak": 0}

    state = _node_state[node]
    state["accum"].append(reading)

    co2 = reading.get("co2_ppm") or 0
    if co2 > config.CO2_WARN_PPM:
        state["co2_high_streak"] += 1
    else:
        state["co2_high_streak"] = 0

    try:
        _notifier.check_and_alert(
            reading,
            co2_high_streak=state["co2_high_streak"],
            node=node,
            co2_high_streak_threshold=config.CO2_HIGH_STREAK_MQTT,
        )
    except Exception as e:
        logger.error("Notifier error for node %s: %s", node, e)

    elapsed = (datetime.now() - state["last_write"]).total_seconds()
    if elapsed >= 600 and state["accum"]:
        avg = _average(state["accum"])
        try:
            db.insert_reading("readings_10min", avg)
            logger.info("Wrote 10min avg for node=%s (%d readings)", node, len(state["accum"]))
        except Exception as e:
            logger.error("DB 10min insert error for node %s: %s", node, e)
        state["accum"].clear()
        state["last_write"] = datetime.now()


def _average(readings: list[dict]) -> dict:
    keys = ["co2_ppm", "temp_c", "humidity_pct", "pm25", "pm10", "aqi", "tvoc", "eco2"]
    result: dict = {}
    for k in keys:
        vals = [r[k] for r in readings if r.get(k) is not None]
        result[k] = round(sum(vals) / len(vals), 2) if vals else None
    result["timestamp"] = readings[-1]["timestamp"]
    result["node"] = readings[-1]["node"]
    return result


def _on_connect(client, userdata, connect_flags, reason_code, properties) -> None:
    if reason_code.is_failure:
        logger.warning("MQTT connect failed: %s", reason_code)
    else:
        logger.info("MQTT connected, subscribing to %s", config.MQTT_TOPIC_SUBSCRIBE)
        client.subscribe(config.MQTT_TOPIC_SUBSCRIBE, qos=0)


def _on_disconnect(client, userdata, disconnect_flags, reason_code, properties) -> None:
    if reason_code.value != 0:
        logger.warning("MQTT disconnected unexpectedly (rc=%s), will reconnect", reason_code)


def main() -> None:
    global _shutdown

    db.init_db()

    def _handle_signal(signum, frame):
        global _shutdown
        logger.info("Signal %s received, shutting down", signum)
        _shutdown = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect    = _on_connect
    client.on_disconnect = _on_disconnect
    client.on_message    = _handle_message

    # Enable automatic reconnection
    client.reconnect_delay_set(min_delay=5, max_delay=60)

    logger.info("Connecting to MQTT broker at %s:%d", config.MQTT_BROKER, config.MQTT_PORT)

    while not _shutdown:
        try:
            client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=60)
            break
        except Exception as e:
            logger.warning("Initial MQTT connect failed (%s), retrying in 10s…", e)
            time.sleep(10)

    if not _shutdown:
        # loop_forever() handles reconnection automatically
        client.loop_forever()

    logger.info("mqtt_listener stopped")


if __name__ == "__main__":
    main()
