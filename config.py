DB_PATH = "/home/skipsuva/bancroft-air-quality/air_quality.db"
SENSOR_READ_INTERVAL_SEC = 10
DISPLAY_CYCLE_SEC = 5

I2C_BUS = 1
SCD40_ADDR = 0x62
PMS5003_PORT = "/dev/serial0"
PMS5003_BAUD = 9600
OLED_ADDR = 0x3C
OLED_WIDTH = 128
OLED_HEIGHT = 64

RETENTION_1MIN_DAYS = 7
NTFY_TOPIC = "bancroft-air"
NTFY_BASE_URL = "https://ntfy.sh"
ALERT_COOLDOWN_MIN = 30

CO2_WARN_PPM = 1000
CO2_CRITICAL_PPM = 1500
PM25_WARN = 25
PM25_CRITICAL = 55
PM10_WARN = 50
PM10_CRITICAL = 150

SUMMARY_HOUR = 8

# MQTT
CO2_HIGH_STREAK_MQTT = 5   # 5 readings × 60s ESP32 interval = 5-minute sustained threshold

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_SUBSCRIBE = "bancroft/+/readings"
MQTT_TOPIC_PUBLISH = "bancroft/office/readings"

# Node names (office is this Pi; others are ESP32 nodes)
NODES = ["office", "bedroom", "toddler", "wifesoffice"]
NODE_LABELS = {
    "office":      "Office",
    "bedroom":     "Bedroom",
    "toddler":     "Toddler's Room",
    "wifesoffice": "Wife's Office",
}

CO2_LABELS = [
    (800, "GOOD"),
    (1000, "OK"),
    (1500, "POOR"),
    (float("inf"), "BAD!"),
]
