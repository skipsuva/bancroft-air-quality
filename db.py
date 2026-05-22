import sqlite3
from datetime import date, datetime, timedelta

import config

_CREATE_READINGS_1MIN = """
CREATE TABLE IF NOT EXISTS readings_1min (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT NOT NULL,
    co2_ppm      REAL,
    temp_c       REAL,
    humidity_pct REAL,
    pm25         REAL,
    pm10         REAL
)
"""

_CREATE_READINGS_10MIN = """
CREATE TABLE IF NOT EXISTS readings_10min (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT NOT NULL,
    co2_ppm      REAL,
    temp_c       REAL,
    humidity_pct REAL,
    pm25         REAL,
    pm10         REAL
)
"""

_CREATE_DAILY_SUMMARIES = """
CREATE TABLE IF NOT EXISTS daily_summaries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT UNIQUE NOT NULL,
    co2_avg      REAL,
    co2_max      REAL,
    co2_max_time TEXT,
    temp_avg     REAL,
    humidity_avg REAL,
    pm25_avg     REAL,
    pm25_max     REAL
)
"""

_CREATE_CURRENT = """
CREATE TABLE IF NOT EXISTS current_reading (
    id           INTEGER PRIMARY KEY CHECK (id = 1),
    timestamp    TEXT,
    co2_ppm      REAL,
    temp_c       REAL,
    humidity_pct REAL,
    pm25         REAL,
    pm10         REAL
)
"""


def get_connection() -> sqlite3.Connection:
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def init_db() -> None:
    con = get_connection()
    try:
        con.execute(_CREATE_READINGS_1MIN)
        con.execute(_CREATE_READINGS_10MIN)
        con.execute(_CREATE_DAILY_SUMMARIES)
        con.execute(_CREATE_CURRENT)
        con.commit()
    finally:
        con.close()
    prune_old_readings()


def prune_old_readings() -> None:
    cutoff = (datetime.now() - timedelta(days=config.RETENTION_1MIN_DAYS)).isoformat()
    con = get_connection()
    try:
        con.execute("DELETE FROM readings_1min WHERE timestamp < ?", (cutoff,))
        con.commit()
    finally:
        con.close()


def upsert_current(reading: dict) -> None:
    con = get_connection()
    try:
        con.execute(
            """INSERT OR REPLACE INTO current_reading
               (id, timestamp, co2_ppm, temp_c, humidity_pct, pm25, pm10)
               VALUES (1, :timestamp, :co2_ppm, :temp_c, :humidity_pct, :pm25, :pm10)""",
            reading,
        )
        con.commit()
    finally:
        con.close()


def insert_reading(table: str, reading: dict) -> None:
    if table not in ("readings_1min", "readings_10min"):
        raise ValueError(f"Unknown table: {table}")
    con = get_connection()
    try:
        con.execute(
            f"""INSERT INTO {table}
                (timestamp, co2_ppm, temp_c, humidity_pct, pm25, pm10)
                VALUES (:timestamp, :co2_ppm, :temp_c, :humidity_pct, :pm25, :pm10)""",
            reading,
        )
        con.commit()
    finally:
        con.close()


def insert_daily_summary(summary: dict) -> None:
    con = get_connection()
    try:
        con.execute(
            """INSERT OR IGNORE INTO daily_summaries
               (date, co2_avg, co2_max, co2_max_time, temp_avg, humidity_avg, pm25_avg, pm25_max)
               VALUES (:date, :co2_avg, :co2_max, :co2_max_time, :temp_avg, :humidity_avg, :pm25_avg, :pm25_max)""",
            summary,
        )
        con.commit()
    finally:
        con.close()


def get_current() -> dict | None:
    con = get_connection()
    try:
        row = con.execute("SELECT * FROM current_reading WHERE id = 1").fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def get_history(range_str: str) -> list[dict]:
    now = datetime.now()
    if range_str == "24h":
        cutoff = (now - timedelta(hours=24)).isoformat()
        table = "readings_1min"
    elif range_str == "7d":
        cutoff = (now - timedelta(days=7)).isoformat()
        table = "readings_10min"
    elif range_str == "30d":
        cutoff = (now - timedelta(days=30)).isoformat()
        table = "readings_10min"
    else:
        return []

    con = get_connection()
    try:
        rows = con.execute(
            f"SELECT * FROM {table} WHERE timestamp >= ? ORDER BY timestamp",
            (cutoff,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def get_readings_for_date(target_date: date) -> list[dict]:
    date_str = target_date.isoformat()
    con = get_connection()
    try:
        rows = con.execute(
            "SELECT * FROM readings_1min WHERE timestamp LIKE ? ORDER BY timestamp",
            (f"{date_str}%",),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()
