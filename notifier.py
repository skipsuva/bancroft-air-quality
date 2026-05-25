import logging
import threading
from datetime import datetime, timedelta

import requests

import config

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self) -> None:
        self._cooldowns: dict[str, datetime] = {}
        self._lock = threading.Lock()

    def _can_send(self, key: str) -> bool:
        threshold = datetime.now() - timedelta(minutes=config.ALERT_COOLDOWN_MIN)
        with self._lock:
            last = self._cooldowns.get(key)
            return last is None or last < threshold

    def _mark_sent(self, key: str) -> None:
        with self._lock:
            self._cooldowns[key] = datetime.now()

    def _send(self, title: str, message: str, priority: str = "default") -> None:
        url = f"{config.NTFY_BASE_URL}/{config.NTFY_TOPIC}"
        try:
            requests.post(
                url,
                data=message.encode("utf-8"),
                headers={
                    "Title": title,
                    "Priority": priority,
                    "Tags": "air_quality",
                },
                timeout=5,
            )
            logger.info("ntfy sent: %s", title)
        except requests.RequestException as e:
            logger.warning("ntfy send failed: %s", e)

    def check_and_alert(self, reading: dict, co2_high_streak: int, pm_elevated_streak: int) -> None:
        co2 = reading.get("co2_ppm") or 0
        pm25 = reading.get("pm25") or 0
        pm10 = reading.get("pm10") or 0

        if co2 > config.CO2_CRITICAL_PPM and self._can_send("co2_critical"):
            self._send(
                "CO₂ Critical",
                f"CO₂ is {co2:.0f} ppm — dangerously high.",
                priority="high",
            )
            self._mark_sent("co2_critical")

        if (
            co2_high_streak >= 30
            and co2 > config.CO2_WARN_PPM
            and self._can_send("co2_high")
        ):
            self._send(
                "CO₂ Elevated",
                f"CO₂ has been above {config.CO2_WARN_PPM} ppm for 5+ minutes ({co2:.0f} ppm).",
            )
            self._mark_sent("co2_high")

        if pm25 > config.PM25_CRITICAL and self._can_send("pm25_unhealthy"):
            self._send(
                "PM2.5 Unhealthy",
                f"PM2.5 is {pm25:.0f} µg/m³ — unhealthy level.",
                priority="high",
            )
            self._mark_sent("pm25_unhealthy")
        elif (
            pm25 > config.PM25_WARN
            and pm_elevated_streak >= 3
            and self._can_send("pm25_elevated")
        ):
            self._send(
                "PM2.5 Elevated",
                f"PM2.5 is {pm25:.0f} µg/m³.",
            )
            self._mark_sent("pm25_elevated")

        if pm10 > config.PM10_CRITICAL and self._can_send("pm10_unhealthy"):
            self._send(
                "PM10 Unhealthy",
                f"PM10 is {pm10:.0f} µg/m³ — unhealthy level.",
                priority="high",
            )
            self._mark_sent("pm10_unhealthy")
        elif (
            pm10 > config.PM10_WARN
            and pm_elevated_streak >= 3
            and self._can_send("pm10_elevated")
        ):
            self._send(
                "PM10 Elevated",
                f"PM10 is {pm10:.0f} µg/m³.",
            )
            self._mark_sent("pm10_elevated")

    def send_daily_summary(self, summary: dict) -> None:
        co2_avg = summary.get("co2_avg") or 0
        co2_max = summary.get("co2_max") or 0
        co2_max_time = summary.get("co2_max_time") or "--:--"
        pm25_avg = summary.get("pm25_avg") or 0
        pm10_avg = summary.get("pm10_avg") or 0
        temp_avg = summary.get("temp_avg") or 0
        target_date = summary.get("date", "")

        message = (
            f"bancroft-air overnight summary — {target_date}\n"
            f"CO₂ avg: {co2_avg:.0f} ppm | peak: {co2_max:.0f} ppm at {co2_max_time}\n"
            f"PM2.5 avg: {pm25_avg:.1f} µg/m³ | PM10 avg: {pm10_avg:.1f} µg/m³ | Temp avg: {temp_avg:.1f}°C"
        )
        self._send("bancroft-air daily summary", message, priority="low")
