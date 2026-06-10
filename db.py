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
    pm10         REAL,
    node         TEXT DEFAULT 'office',
    aqi          INTEGER,
    tvoc         INTEGER
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
    pm10         REAL,
    node         TEXT DEFAULT 'office',
    aqi          INTEGER,
    tvoc         INTEGER
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

_CREATE_NODE_CURRENT = """
CREATE TABLE IF NOT EXISTS node_current (
    node         TEXT PRIMARY KEY,
    timestamp    TEXT,
    co2_ppm      REAL,
    temp_c       REAL,
    humidity_pct REAL,
    pm25         REAL,
    pm10         REAL,
    aqi          INTEGER,
    tvoc         INTEGER
)
"""


def get_connection() -> sqlite3.Connection:
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def _migrate(con: sqlite3.Connection) -> None:
    """Add new columns to existing tables that predate schema updates."""
    # PRAGMA table_info returns rows: (cid, name, type, notnull, dflt_value, pk)
    existing = {
        row[1]
        for row in con.execute("PRAGMA table_info(readings_1min)").fetchall()
    }
    if "node" not in existing:
        con.execute("ALTER TABLE readings_1min ADD COLUMN node TEXT DEFAULT 'office'")
    if "aqi" not in existing:
        con.execute("ALTER TABLE readings_1min ADD COLUMN aqi INTEGER")
    if "tvoc" not in existing:
        con.execute("ALTER TABLE readings_1min ADD COLUMN tvoc INTEGER")

    existing = {
        row[1]
        for row in con.execute("PRAGMA table_info(readings_10min)").fetchall()
    }
    if "node" not in existing:
        con.execute("ALTER TABLE readings_10min ADD COLUMN node TEXT DEFAULT 'office'")
    if "aqi" not in existing:
        con.execute("ALTER TABLE readings_10min ADD COLUMN aqi INTEGER")
    if "tvoc" not in existing:
        con.execute("ALTER TABLE readings_10min ADD COLUMN tvoc INTEGER")

    existing = {
        row[1]
        for row in con.execute("PRAGMA table_info(node_current)").fetchall()
    }
    if "aqi" not in existing:
        con.execute("ALTER TABLE node_current ADD COLUMN aqi INTEGER")
    if "tvoc" not in existing:
        con.execute("ALTER TABLE node_current ADD COLUMN tvoc INTEGER")

    con.commit()


def init_db() -> None:
    con = get_connection()
    try:
        con.execute(_CREATE_READINGS_1MIN)
        con.execute(_CREATE_READINGS_10MIN)
        con.execute(_CREATE_DAILY_SUMMARIES)
        con.execute(_CREATE_CURRENT)
        con.execute(_CREATE_NODE_CURRENT)
        con.commit()
        _migrate(con)
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
    """Upsert the single-row office current reading (legacy, used by sensor_daemon)."""
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


def upsert_node_current(reading: dict) -> None:
    """Upsert the latest reading for a specific node (keyed by node name)."""
    con = get_connection()
    try:
        con.execute(
            """INSERT OR REPLACE INTO node_current
               (node, timestamp, co2_ppm, temp_c, humidity_pct, pm25, pm10, aqi, tvoc)
               VALUES (:node, :timestamp, :co2_ppm, :temp_c, :humidity_pct, :pm25, :pm10, :aqi, :tvoc)""",
            {**reading, "aqi": reading.get("aqi"), "tvoc": reading.get("tvoc")},
        )
        con.commit()
    finally:
        con.close()


def get_all_node_current() -> dict:
    """Return a dict keyed by node name with each node's latest reading."""
    con = get_connection()
    try:
        rows = con.execute("SELECT * FROM node_current").fetchall()
        return {row["node"]: dict(row) for row in rows}
    finally:
        con.close()


def insert_reading(table: str, reading: dict) -> None:
    if table not in ("readings_1min", "readings_10min"):
        raise ValueError(f"Unknown table: {table}")
    node = reading.get("node", "office")
    con = get_connection()
    try:
        con.execute(
            f"""INSERT INTO {table}
                (timestamp, co2_ppm, temp_c, humidity_pct, pm25, pm10, node, aqi, tvoc)
                VALUES (:timestamp, :co2_ppm, :temp_c, :humidity_pct, :pm25, :pm10, :node, :aqi, :tvoc)""",
            {**reading, "node": node, "aqi": reading.get("aqi"), "tvoc": reading.get("tvoc")},
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


def get_latest_summary_date() -> "date | None":
    """Return the most recent date in daily_summaries, or None if the table is empty."""
    from datetime import date as _date
    con = get_connection()
    try:
        row = con.execute("SELECT MAX(date) FROM daily_summaries").fetchone()
        if row and row[0]:
            return _date.fromisoformat(row[0])
        return None
    finally:
        con.close()


def get_current() -> dict | None:
    """Return the office node's latest current reading (legacy fallback for /api/now)."""
    con = get_connection()
    try:
        row = con.execute("SELECT * FROM current_reading WHERE id = 1").fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def get_smoothed_current(node: str, minutes: int = 5) -> dict | None:
    """Return a rolling average of the last `minutes` 1-min readings for a node.

    Falls back to None if fewer than 2 rows exist (node just came online).
    """
    con = get_connection()
    try:
        row = con.execute(
            """SELECT AVG(co2_ppm)      AS co2_ppm,
                      AVG(temp_c)       AS temp_c,
                      AVG(humidity_pct) AS humidity_pct,
                      AVG(pm25)         AS pm25,
                      AVG(pm10)         AS pm10,
                      AVG(aqi)          AS aqi,
                      AVG(tvoc)         AS tvoc,
                      MAX(timestamp)    AS timestamp,
                      node,
                      COUNT(*)          AS _count
               FROM (
                 SELECT * FROM readings_1min
                 WHERE node = ?
                 ORDER BY timestamp DESC
                 LIMIT ?
               )""",
            (node, minutes),
        ).fetchone()
        if row and row["_count"] >= 2:
            d = dict(row)
            d.pop("_count", None)
            return d
        return None
    finally:
        con.close()


def get_history(range_str: str, node: str | None = None, smooth: bool = False) -> list[dict]:
    # Backward-compat aliases
    _aliases = {"24h": "1d", "7d": "1w", "30d": "1m"}
    range_str = _aliases.get(range_str, range_str)

    # Node filter clause
    if node:
        node_clause = "AND node = ?"
        node_param: tuple = (node,)
    else:
        node_clause = ""
        node_param = ()

    now = datetime.now()
    table_short = "readings_10min" if smooth else "readings_1min"
    con = get_connection()
    try:
        if range_str == "2h":
            cutoff = (now - timedelta(hours=2)).isoformat()
            rows = con.execute(
                f"SELECT * FROM {table_short} WHERE timestamp >= ? {node_clause} ORDER BY timestamp",
                (cutoff,) + node_param,
            ).fetchall()
            return [dict(r) for r in rows]

        elif range_str == "6h":
            cutoff = (now - timedelta(hours=6)).isoformat()
            rows = con.execute(
                f"SELECT * FROM {table_short} WHERE timestamp >= ? {node_clause} ORDER BY timestamp",
                (cutoff,) + node_param,
            ).fetchall()
            return [dict(r) for r in rows]

        elif range_str == "1d":
            cutoff = (now - timedelta(hours=24)).isoformat()
            rows = con.execute(
                f"SELECT * FROM {table_short} WHERE timestamp >= ? {node_clause} ORDER BY timestamp",
                (cutoff,) + node_param,
            ).fetchall()
            return [dict(r) for r in rows]

        elif range_str == "1w":
            cutoff = (now - timedelta(days=7)).isoformat()
            rows = con.execute(
                f"SELECT * FROM readings_10min WHERE timestamp >= ? {node_clause} ORDER BY timestamp",
                (cutoff,) + node_param,
            ).fetchall()
            return [dict(r) for r in rows]

        elif range_str == "1m":
            cutoff = (now - timedelta(days=30)).isoformat()
            rows = con.execute(
                f"SELECT * FROM readings_10min WHERE timestamp >= ? {node_clause} ORDER BY timestamp",
                (cutoff,) + node_param,
            ).fetchall()
            return [dict(r) for r in rows]

        elif range_str in ("3m", "6m"):
            days = 90 if range_str == "3m" else 180
            cutoff = (now - timedelta(days=days)).isoformat()
            rows = con.execute(
                f"""SELECT strftime('%Y-%m-%dT%H:00:00', timestamp) AS timestamp,
                          AVG(co2_ppm)      AS co2_ppm,
                          AVG(temp_c)       AS temp_c,
                          AVG(humidity_pct) AS humidity_pct,
                          AVG(pm25)         AS pm25,
                          AVG(pm10)         AS pm10,
                          node,
                          AVG(aqi)          AS aqi,
                          AVG(tvoc)         AS tvoc
                   FROM readings_10min
                   WHERE timestamp >= ? {node_clause}
                   GROUP BY strftime('%Y-%m-%dT%H:00:00', timestamp), node
                   ORDER BY 1""",
                (cutoff,) + node_param,
            ).fetchall()
            return [dict(r) for r in rows]

        elif range_str == "1y":
            # daily_summaries is office-only; skip for other nodes
            if node and node != "office":
                return []
            cutoff = (now - timedelta(days=365)).date().isoformat()
            rows = con.execute(
                """SELECT date       AS timestamp,
                          co2_avg    AS co2_ppm,
                          temp_avg   AS temp_c,
                          humidity_avg AS humidity_pct,
                          pm25_avg   AS pm25,
                          NULL       AS pm10,
                          'office'   AS node,
                          NULL       AS aqi,
                          NULL       AS tvoc
                   FROM daily_summaries
                   WHERE date >= ?
                   ORDER BY date""",
                (cutoff,),
            ).fetchall()
            return [dict(r) for r in rows]

        elif range_str == "all":
            if node and node != "office":
                return []
            rows = con.execute(
                """SELECT date       AS timestamp,
                          co2_avg    AS co2_ppm,
                          temp_avg   AS temp_c,
                          humidity_avg AS humidity_pct,
                          pm25_avg   AS pm25,
                          NULL       AS pm10,
                          'office'   AS node,
                          NULL       AS aqi,
                          NULL       AS tvoc
                   FROM daily_summaries
                   ORDER BY date""",
            ).fetchall()
            return [dict(r) for r in rows]

        else:
            return []
    finally:
        con.close()


def get_readings_for_date(target_date: date, node: str = "office") -> list[dict]:
    date_str = target_date.isoformat()
    con = get_connection()
    try:
        rows = con.execute(
            "SELECT * FROM readings_1min WHERE timestamp LIKE ? AND node = ? ORDER BY timestamp",
            (f"{date_str}%", node),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()
