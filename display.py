import logging
import threading
import time

from PIL import ImageFont

import config

logger = logging.getLogger(__name__)


def _co2_label(co2: float) -> str:
    for threshold, label in config.CO2_LABELS:
        if co2 < threshold:
            return label
    return "BAD!"


_AQI_LABELS = {1: "EXCELLENT", 2: "GOOD", 3: "MODERATE", 4: "POOR", 5: "UNHEALTHY"}


def _aqi_label(aqi: int) -> str:
    return _AQI_LABELS.get(aqi, "--")


class OLEDDisplay:
    def __init__(self, state: dict, lock: threading.Lock) -> None:
        self._state = state
        self._lock = lock
        self._device = None
        self._screen_index = 0

        try:
            self._font_status = ImageFont.load_default(size=20)
            self._font_large = ImageFont.load_default(size=14)
            self._font_small = ImageFont.load_default(size=11)
        except TypeError:
            self._font_status = ImageFont.load_default()
            self._font_large = ImageFont.load_default()
            self._font_small = ImageFont.load_default()

    def _init_device(self) -> None:
        try:
            from luma.core.interface.serial import i2c as luma_i2c
            from luma.oled.device import sh1106

            serial = luma_i2c(port=config.I2C_BUS, address=config.OLED_ADDR)
            self._device = sh1106(serial)
            logger.info("OLED initialized")
        except Exception as e:
            logger.warning("OLED init failed (display disabled): %s", e)
            self._device = None

    def _draw_screen_1(self, draw, data: dict) -> None:
        co2 = data.get("co2_ppm")
        aqi = data.get("aqi")
        tvoc = data.get("tvoc")

        label = _co2_label(co2) if co2 is not None else "--"
        co2_str = f"CO2: {co2:.0f} ppm" if co2 is not None else "CO2: --"
        aqi_str = f"AQI: {_aqi_label(aqi)}" if aqi is not None else "AQI: --"
        tvoc_str = f"VOC:{tvoc}" if tvoc is not None else "VOC:--"

        label_w = draw.textlength(label, font=self._font_status)
        draw.text(((128 - label_w) // 2, 0), label, fill="white", font=self._font_status)
        draw.text((0, 24), co2_str, fill="white", font=self._font_large)
        draw.text((0, 42), aqi_str, fill="white", font=self._font_small)
        draw.text((66, 42), tvoc_str, fill="white", font=self._font_small)

    def _draw_screen_2(self, draw, data: dict) -> None:
        temp_c = data.get("temp_c")
        temp = temp_c * 9 / 5 + 32 if temp_c is not None else None
        humidity = data.get("humidity_pct")

        temp_str = f"Temp:  {temp:.1f} F" if temp is not None else "Temp:  --"
        hum_str = f"RH:    {humidity:.1f} %" if humidity is not None else "RH:    --"

        draw.text((0, 0), temp_str, fill="white", font=self._font_large)
        draw.text((0, 18), hum_str, fill="white", font=self._font_large)
        draw.text((0, 50), "bancroft-air", fill="white", font=self._font_small)

    def run(self) -> None:
        self._init_device()

        if self._device is None:
            logger.info("Display thread exiting — no device")
            return

        from luma.core.render import canvas

        while True:
            with self._lock:
                data = dict(self._state)

            try:
                with canvas(self._device) as draw:
                    if self._screen_index == 0:
                        self._draw_screen_1(draw, data)
                    else:
                        self._draw_screen_2(draw, data)
            except Exception as e:
                logger.error("Display render error: %s", e)

            self._screen_index = 1 - self._screen_index
            time.sleep(config.DISPLAY_CYCLE_SEC)
