"""Tests for util.average — the shared reading-averaging helper."""

import util


def _r(**kw):
    """Build a reading dict with all READING_FIELDS present (None unless given)."""
    base = {k: None for k in util.READING_FIELDS}
    base["timestamp"] = kw.pop("timestamp", "2026-06-24T12:00:00")
    base["node"] = kw.pop("node", "office")
    base.update(kw)
    return base


def test_simple_mean():
    rows = [_r(co2_ppm=400), _r(co2_ppm=600)]
    out = util.average(rows)
    assert out["co2_ppm"] == 500


def test_rounds_to_two_dp():
    rows = [_r(temp_c=1), _r(temp_c=2), _r(temp_c=2)]  # 1.6666...
    assert util.average(rows)["temp_c"] == 1.67


def test_none_values_skipped():
    rows = [_r(co2_ppm=400), _r(co2_ppm=None), _r(co2_ppm=800)]
    assert util.average(rows)["co2_ppm"] == 600


def test_field_all_none_averages_to_none():
    rows = [_r(co2_ppm=400), _r(co2_ppm=500)]
    # eco2 left None on every row -> None, not a ZeroDivisionError
    assert util.average(rows)["eco2"] is None


def test_timestamp_is_last_reading():
    rows = [_r(timestamp="2026-06-24T12:00:00"), _r(timestamp="2026-06-24T12:01:00")]
    assert util.average(rows)["timestamp"] == "2026-06-24T12:01:00"


def test_node_defaults_to_last_reading():
    rows = [_r(node="office"), _r(node="kitchen")]
    assert util.average(rows)["node"] == "kitchen"


def test_node_override():
    rows = [_r(node="kitchen")]
    assert util.average(rows, node="office")["node"] == "office"


def test_custom_keys_subset():
    rows = [_r(co2_ppm=400, temp_c=20), _r(co2_ppm=600, temp_c=22)]
    out = util.average(rows, keys=["co2_ppm"])
    assert out["co2_ppm"] == 500
    assert "temp_c" not in out


def test_all_fields_present_by_default():
    out = util.average([_r(co2_ppm=400)])
    for k in util.READING_FIELDS:
        assert k in out
