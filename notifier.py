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

    def check_and_alert(
        self,
        reading: dict,
        co2_high_streak: int,
        pm_elevated_streak: int,
        node: str = "office",
        co2_high_streak_threshold: int = 30,
    ) -> None:
        label = config.NODE_LABELS.get(node, node)
        co2 = reading.get("co2_ppm") or 0
        pm25 = reading.get("pm25") or 0
        pm10 = reading.get("pm10") or 0

        if co2 > config.CO2_CRITICAL_PPM and self._can_send(f"co2_critical:{node}"):
            self._send(
                f"CO₂ Critical — {label}",
                f"CO₂ is {co2:.0f} ppm — dangerously high.",
                priority="high",
            )
            self._mark_sent(f"co2_critical:{node}")

        if (
            co2_high_streak >= co2_high_streak_threshold
            and co2 > config.CO2_WARN_PPM
            and self._can_send(f"co2_high:{node}")
        ):
            self._send(
                f"CO₂ Elevated — {label}",
                f"CO₂ has been above {config.CO2_WARN_PPM} ppm for 5+ minutes ({co2:.0f} ppm).",
            )
            self._mark_sent(f"co2_high:{node}")

        if pm25 > config.PM25_CRITICAL and self._can_send(f"pm25_unhealthy:{node}"):
            self._send(
                f"PM2.5 Unhealthy — {label}",
                f"PM2.5 is {pm25:.0f} µg/m³ — unhealthy level.",
                priority="high",
            )
            self._mark_sent(f"pm25_unhealthy:{node}")
        elif (
            pm25 > config.PM25_WARN
            and pm_elevated_streak >= 3
            and self._can_send(f"pm25_elevated:{node}")
        ):
            self._send(
                f"PM2.5 Elevated — {label}",
                f"PM2.5 is {pm25:.0f} µg/m³.",
            )
            self._mark_sent(f"pm25_elevated:{node}")

        if pm10 > config.PM10_CRITICAL and self._can_send(f"pm10_unhealthy:{node}"):
            self._send(
                f"PM10 Unhealthy — {label}",
                f"PM10 is {pm10:.0f} µg/m³ — unhealthy level.",
                priority="high",
            )
            self._mark_sent(f"pm10_unhealthy:{node}")
        elif (
            pm10 > config.PM10_WARN
            and pm_elevated_streak >= 3
            and self._can_send(f"pm10_elevated:{node}")
        ):
            self._send(
                f"PM10 Elevated — {label}",
                f"PM10 is {pm10:.0f} µg/m³.",
            )
            self._mark_sent(f"pm10_elevated:{node}")

    def send_daily_summary(self, summaries: dict[str, dict]) -> None:
        """Send a single combined daily summary covering all nodes that have data."""
        if not summaries:
            return

        target_date = next(iter(summaries.values())).get("date", "")
        lines = [f"Bancroft Air daily summary — {target_date}"]

        for node in config.NODES:
            summary = summaries.get(node)
            if not summary:
                continue
            label = config.NODE_LABELS.get(node, node)
            co2_avg = summary.get("co2_avg") or 0
            co2_max = summary.get("co2_max") or 0
            co2_max_time = summary.get("co2_max_time") or "--:--"
            temp_avg = summary.get("temp_avg") or 0
            line = f"{label}: CO₂ avg {co2_avg:.0f} ppm, peak {co2_max:.0f} at {co2_max_time}, temp {temp_avg:.1f}°C"
            pm25_avg = summary.get("pm25_avg")
            pm10_avg = summary.get("pm10_avg")
            if pm25_avg is not None:
                line += f", PM2.5 {pm25_avg:.1f} µg/m³"
            if pm10_avg is not None:
                line += f", PM10 {pm10_avg:.1f} µg/m³"
            lines.append(line)

        self._send("Bancroft Air daily summary", "\n\n".join(lines), priority="low")
