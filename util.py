"""Shared helpers used by both daemons (sensor_daemon.py and mqtt_listener.py)."""

import logging

# Canonical numeric reading fields, in the order they are averaged/persisted.
# `eco2` is only populated by the kitchen node; other nodes leave it None.
READING_FIELDS = ["co2_ppm", "temp_c", "humidity_pct", "pm25", "pm10", "aqi", "tvoc", "eco2"]


def average(readings: list[dict], node: str | None = None, keys: list[str] | None = None) -> dict:
    """Average a non-empty list of reading dicts.

    For each field, None values are skipped; a field with no values averages to
    None. Results are rounded to 2 decimal places. The timestamp is taken from
    the last reading. `node` defaults to the last reading's node.

    Caller must guarantee `readings` is non-empty.
    """
    if keys is None:
        keys = READING_FIELDS
    result: dict = {}
    for k in keys:
        vals = [r[k] for r in readings if r.get(k) is not None]
        result[k] = round(sum(vals) / len(vals), 2) if vals else None
    result["timestamp"] = readings[-1]["timestamp"]
    result["node"] = node if node is not None else readings[-1].get("node")
    return result


def setup_logging() -> None:
    """Configure root logging consistently for both daemon entrypoints."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(threadName)s %(levelname)s %(message)s",
    )
