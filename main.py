from time import sleep_ms, ticks_ms 
from machine import SoftI2C, Pin 
from i2c_lcd import I2cLcd 
import config
from net import WiFiManager, Tester, UdpMessenger
import time
from time import sleep_ms, ticks_ms, ticks_diff
from mqtt_client import MqttLink

DEFAULT_I2C_ADDR = 0x27

def on_cmd(topic, payload):
    # Example: payload might be JSON: {"relay":1,"on":true}
    print("MQTT CMD", topic, payload)
    handle_messages(topic, payload, None)  # if you adapt handler signature

def handle_messages(topic, payload, addr):
    print("in handle message")
    if topic == "haus1/Status":
        if payload == "OK":
            lcd.move_to(0, 0)
            lcd.putstr('Status Haus 1: OK')
        if payload == "ERROR":
            lcd.move_to(0, 0)
            lcd.putstr('Status Haus 1: ERROR')
        if payload == "WARNING":
            lcd.move_to(0, 0)
            lcd.putstr('Status Haus 1: WARNING')

    # if topic == "haus1/load":
    #     load = int(payload)
    #     if load > 80:
    #         print("High load, reacting...")
    # elif topic == "haus2/alerts":
    #     print("Alert from house2:", payload)

# Initialize the SCL/SDA pins and enable the internal pull-up.
scl_pin = Pin(22, Pin.OUT, pull=Pin.PULL_UP)  # Enable the internal pull-up for GPIO22.
sda_pin = Pin(21, Pin.OUT, pull=Pin.PULL_UP)  # Enable the internal pull-up for GPIO21.

i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)

devices = i2c.scan()
if not devices:
    print("No I2C device was detected! Check the wiring / power supply / pull-up resistor.")
else:
    print("Detected device address:", [hex(addr) for addr in devices])  # Output hexadecimal address‌:ml-citation{ref="3,8" data="citationList"}

lcd = I2cLcd(i2c, DEFAULT_I2C_ADDR, 2, 16)


wifi = WiFiManager(config.WIFI_SSID, config.WIFI_PASSWORD)
wifi.connect()
if not wifi.is_connected():
    print("Wifi not Connected. Abort.")
    raise SystemExit(1)

time.sleep(2)

wifiTest = Tester()
wifiTest.test_internet()
wifiTest.test_dns()

device_id = config.HOUSE  # or a unique ID per ESP32
mqtt = MqttLink(device_id)
mqtt.set_cmd_handler(on_cmd)
mqtt.connect()
mqtt.publish_test("test from haus01")

udp = UdpMessenger(timeout_s=0.02)  # non-blocking

last_heartbeat = ticks_ms()
last_alive = ticks_ms()
loops = 0
last_mqtt_try = 0
mqtt_down_since = None

while True:
    now = ticks_ms()

    if not mqtt.connected and ticks_diff(now, last_mqtt_try) > config.MQTT_RETRY_MS:
            last_mqtt_try = now
            try:
                mqtt.connect()
                mqtt_down_since = None
                print("[MQTT] connected")
            except Exception as e:
                print("[MQTT] connect failed:", e)
                if mqtt_down_since is None:
                    mqtt_down_since = now

    if mqtt.connected:
        try:
            mqtt.loop_once() #get messages
        except Exception as e:
            print("[MQTT] lost connection:", e)
            mqtt.disconnect()
            if mqtt_down_since is None:
                mqtt_down_since = now

    use_udp = False
    if mqtt_down_since is not None and ticks_diff(now, mqtt_down_since) > config.UDP_FALLBACK_AFTER_MS:
        use_udp = True
    
    if use_udp:
        topic, payload, addr = udp.recv_once(handle_messages)

    hb_age = ticks_diff(now, last_heartbeat)
    if hb_age > 2000:
        topic = config.HOUSE + "/Status"
        payload = "OK"

        if use_udp:
            print("[HB][UDP] after", hb_age, "ms ->", topic, payload)
            udp.publish(topic, payload)
        else:
            print("[HB][MQTT] after", hb_age, "ms ->", topic, payload)
            try:
                mqtt.publish_test("this is a test")   # or mqtt.publish_telemetry(...)
            except Exception as e:
                print("[MQTT] publish failed:", e)
                mqtt.disconnect()
                if mqtt_down_since is None:
                    mqtt_down_since = now

        last_heartbeat = now

    sleep_ms(10)
