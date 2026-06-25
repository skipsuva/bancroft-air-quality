"""Tests for Notifier.check_and_alert — streak threshold + cooldown logic.

_send is monkeypatched to record calls instead of hitting ntfy.sh.
"""

import pytest

import config
from notifier import Notifier


@pytest.fixture()
def notifier(monkeypatch):
    n = Notifier()
    sent = []
    monkeypatch.setattr(n, "_send", lambda title, message, priority="default": sent.append((title, priority)))
    n.sent = sent  # attach for assertions
    return n


def test_critical_fires_immediately(notifier):
    notifier.check_and_alert({"co2_ppm": config.CO2_CRITICAL_PPM + 1}, co2_high_streak=0)
    assert len(notifier.sent) == 1
    assert notifier.sent[0][1] == "high"


def test_high_does_not_fire_below_streak(notifier):
    reading = {"co2_ppm": config.CO2_WARN_PPM + 1}
    notifier.check_and_alert(reading, co2_high_streak=29, co2_high_streak_threshold=30)
    assert notifier.sent == []


def test_high_fires_at_streak_threshold(notifier):
    reading = {"co2_ppm": config.CO2_WARN_PPM + 1}
    notifier.check_and_alert(reading, co2_high_streak=30, co2_high_streak_threshold=30)
    assert len(notifier.sent) == 1
    assert notifier.sent[0][1] == "default"


def test_mqtt_streak_threshold(notifier):
    reading = {"co2_ppm": config.CO2_WARN_PPM + 1}
    notifier.check_and_alert(reading, co2_high_streak=5, co2_high_streak_threshold=config.CO2_HIGH_STREAK_MQTT)
    assert len(notifier.sent) == 1


def test_cooldown_suppresses_repeat(notifier):
    reading = {"co2_ppm": config.CO2_WARN_PPM + 1}
    notifier.check_and_alert(reading, co2_high_streak=30, co2_high_streak_threshold=30)
    notifier.check_and_alert(reading, co2_high_streak=30, co2_high_streak_threshold=30)
    assert len(notifier.sent) == 1  # second call suppressed by 30-min cooldown


def test_cooldown_is_per_node(notifier):
    reading = {"co2_ppm": config.CO2_WARN_PPM + 1}
    notifier.check_and_alert(reading, co2_high_streak=30, co2_high_streak_threshold=30, node="office")
    notifier.check_and_alert(reading, co2_high_streak=30, co2_high_streak_threshold=30, node="bedroom")
    assert len(notifier.sent) == 2  # different node -> different cooldown key


def test_no_alert_when_co2_normal(notifier):
    notifier.check_and_alert({"co2_ppm": 600}, co2_high_streak=100, co2_high_streak_threshold=30)
    assert notifier.sent == []


def test_missing_co2_is_safe(notifier):
    notifier.check_and_alert({"co2_ppm": None}, co2_high_streak=100)
    assert notifier.sent == []
