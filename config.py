HOUSEID = "unknown"
try:
    import device_config
    HOUSEID = device_config.HOUSEID
except ImportError:
    print("No device_config.py found, using default HOUSE:", HOUSEID)

WIFI_SSID = "ZTE_AF5722"
WIFI_PASSWORD = "59657247"
BROADCAST_IP = "192.168.0.255"
UDP_PORT = 5005

# MQTT (local broker on Pi)
MQTT_HOST = "192.168.0.113"
MQTT_PORT = 1883
MQTT_USER = "tobias"
MQTT_PASS = "abc.123"
MQTT_KEEPALIVE = 30  # seconds

TOPIC_BASE = "house"

MQTT_RETRY_MS = 3000
UDP_FALLBACK_AFTER_MS = 10000