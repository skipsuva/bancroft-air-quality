"""Tests for status thresholds.

config.STATUS_THRESHOLDS is the single source of truth shared with the frontend
(static/shared.js). These tests pin the boundary values and the GOOD/OK/POOR/BAD
classification so the backend and the JS nodeStatus() can't silently diverge.
"""

import config


def classify(value, bands):
    """Mirror of nodeStatus() banding in static/shared.js."""
    if value is None:
        return "OFFLINE"
    if value < bands[0]:
        return "GOOD"
    if value < bands[1]:
        return "OK"
    if value < bands[2]:
        return "POOR"
    return "BAD"


def test_threshold_values_pinned():
    # If these change, static/shared.js banding and these tests must change together.
    assert config.STATUS_THRESHOLDS["co2"] == [800, 1000, 1500]
    assert config.STATUS_THRESHOLDS["pm25"] == [12, 35, 55]


def test_co2_derived_from_labels():
    # CO₂ bands are derived from CO2_LABELS — guard against drift.
    derived = [t for t, _ in config.CO2_LABELS if t != float("inf")]
    assert config.STATUS_THRESHOLDS["co2"] == derived


def test_co2_bands():
    bands = config.STATUS_THRESHOLDS["co2"]
    assert classify(799, bands) == "GOOD"
    assert classify(800, bands) == "OK"      # boundary is inclusive of next band
    assert classify(999, bands) == "OK"
    assert classify(1000, bands) == "POOR"
    assert classify(1499, bands) == "POOR"
    assert classify(1500, bands) == "BAD"
    assert classify(3000, bands) == "BAD"


def test_pm25_bands():
    bands = config.STATUS_THRESHOLDS["pm25"]
    assert classify(11.9, bands) == "GOOD"
    assert classify(12, bands) == "OK"
    assert classify(35, bands) == "POOR"
    assert classify(55, bands) == "BAD"


def test_none_is_offline():
    assert classify(None, config.STATUS_THRESHOLDS["co2"]) == "OFFLINE"
