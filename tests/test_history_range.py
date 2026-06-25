"""Tests for db.get_history range/alias/table mapping against a temp SQLite DB."""

from datetime import datetime, timedelta

import pytest

import config
import db


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Point db at a fresh temp database seeded with known rows."""
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()

    now = datetime.now()

    def row(ts, node="office", co2=500):
        return {
            "timestamp": ts.isoformat(),
            "co2_ppm": co2,
            "temp_c": 21.0,
            "humidity_pct": 45.0,
            "pm25": None,
            "pm10": None,
            "node": node,
            "aqi": None,
            "tvoc": None,
            "eco2": None,
        }

    # 1min table: one recent (1h ago) + one stale (3 days ago)
    db.insert_reading("readings_1min", row(now - timedelta(hours=1)))
    db.insert_reading("readings_1min", row(now - timedelta(days=3)))
    db.insert_reading("readings_1min", row(now - timedelta(hours=1), node="kitchen"))

    # 10min table: one recent (1h ago) + one mid (10 days ago)
    db.insert_reading("readings_10min", row(now - timedelta(hours=1)))
    db.insert_reading("readings_10min", row(now - timedelta(days=10)))
    return now


def test_alias_24h_maps_to_1d(temp_db):
    assert db.get_history("24h") == db.get_history("1d")


def test_alias_7d_maps_to_1w(temp_db):
    assert db.get_history("7d") == db.get_history("1w")


def test_alias_30d_maps_to_1m(temp_db):
    assert db.get_history("30d") == db.get_history("1m")


def test_1d_uses_1min_table_and_cutoff(temp_db):
    # Only the 1h-ago office row falls inside 24h (3-days-ago is excluded).
    rows = db.get_history("1d", node="office")
    assert len(rows) == 1


def test_node_filter(temp_db):
    assert all(r["node"] == "kitchen" for r in db.get_history("1d", node="kitchen"))
    assert len(db.get_history("1d")) == 2  # office + kitchen, unfiltered


def test_1w_uses_10min_table(temp_db):
    # 1w reads readings_10min; both the 1h and 10-day rows are within 7 days? No —
    # 10 days ago is outside 7d, so only the recent row is returned.
    rows = db.get_history("1w", node="office")
    assert len(rows) == 1


def test_1m_uses_10min_table(temp_db):
    # 30 days covers both 10min rows (1h and 10 days ago).
    rows = db.get_history("1m", node="office")
    assert len(rows) == 2


def test_smooth_forces_10min_for_short_range(temp_db):
    # smooth=1 on a short range reads readings_10min instead of readings_1min.
    rows = db.get_history("1d", node="office", smooth=True)
    assert len(rows) == 1  # the recent 10min row


def test_unknown_range_returns_empty(temp_db):
    assert db.get_history("nonsense") == []


def test_non_office_node_skips_office_only_ranges(temp_db):
    assert db.get_history("1y", node="kitchen") == []
    assert db.get_history("all", node="kitchen") == []
