DB_PATH = "/home/skipsuva/bancroft-air-quality/air_quality.db"
SENSOR_READ_INTERVAL_SEC = 10
DISPLAY_CYCLE_SEC = 5

I2C_BUS = 1
SCD40_ADDR = 0x62
ENS160_ADDR = 0x53
OLED_ADDR = 0x3C
OLED_WIDTH = 128
OLED_HEIGHT = 64

RETENTION_1MIN_DAYS = 7
NTFY_TOPIC = "bancroft-air"
NTFY_BASE_URL = "https://ntfy.sh"
ALERT_COOLDOWN_MIN = 30

CO2_WARN_PPM = 1000
CO2_CRITICAL_PPM = 1500

SUMMARY_HOUR = 8

# MQTT
CO2_HIGH_STREAK_MQTT = 5   # 5 readings × 60s ESP32 interval = 5-minute sustained threshold

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_SUBSCRIBE = "bancroft/+/readings"
MQTT_TOPIC_PUBLISH = "bancroft/office/readings"

# Node names (office is this Pi; others are ESP32 nodes)
NODES = ["office", "bedroom", "toddler", "wifesoffice", "basement", "kitchen"]
NODE_LABELS = {
    "office":      "Office",
    "bedroom":     "Bedroom",
    "toddler":     "Mari's Room",
    "wifesoffice": "Wife's Office",
    "basement":    "Basement",
    "kitchen":     "Kitchen",
}

NODE_SENSORS = {
    "office":      {"co2": True,  "temp": True, "humidity": True, "aqi": True,  "tvoc": True,  "pm": False, "eco2": False},
    "bedroom":     {"co2": True,  "temp": True, "humidity": True, "aqi": True,  "tvoc": True,  "pm": False, "eco2": False},
    "toddler":     {"co2": True,  "temp": True, "humidity": True, "aqi": True,  "tvoc": True,  "pm": False, "eco2": False},
    "wifesoffice": {"co2": True,  "temp": True, "humidity": True, "aqi": True,  "tvoc": True,  "pm": False, "eco2": False},
    "basement":    {"co2": True,  "temp": True, "humidity": True, "aqi": False, "tvoc": False, "pm": False, "eco2": False},
    "kitchen":     {"co2": False, "temp": True, "humidity": True, "aqi": True,  "tvoc": True,  "pm": True,  "eco2": True},
}

ENS160_NODES = [n for n, s in NODE_SENSORS.items() if s["aqi"]]
PM_NODES     = [n for n, s in NODE_SENSORS.items() if s["pm"]]
ECO2_NODES   = [n for n, s in NODE_SENSORS.items() if s["eco2"]]

CO2_LABELS = [
    (800, "GOOD"),
    (1000, "OK"),
    (1500, "POOR"),
    (float("inf"), "BAD!"),
]
