HOUSE = "unknown"
try:
    import device_config
    HOUSE = device_config.HOUSE
except ImportError:
    print("No device_config.py found, using default HOUSE:", HOUSE)

WIFI_SSID = "ZTE_AF5722"
WIFI_PASSWORD = "59657247"
BROADCAST_IP = "192.168.0.255"
UDP_PORT = 5005