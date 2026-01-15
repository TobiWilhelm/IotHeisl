from time import sleep_ms, ticks_ms
from machine import SoftI2C, Pin
from i2c_lcd import I2cLcd
import config
from handlers import Handler
from net import WiFiManager, Tester, UdpMessenger
import time
from time import sleep_ms, ticks_ms, ticks_diff
from mqtt_client import MqttLink
from display import Display

# Testd
displayWriter = Display()
displayWriter.write_line(0,"Booting...")

commandHandler = Handler()

def on_cmd(topic, payload):
    print("MQTT CMD", topic, payload)
    commandHandler.handle_messages(topic, payload, None)

wifi = WiFiManager(config.WIFI_SSID, config.WIFI_PASSWORD)
wifi.connect()
if not wifi.is_connected():
    print("Wifi not Connected. Abort.")
    raise SystemExit(1)

time.sleep(2)

wifiTest = Tester()
wifiTest.test_internet()
wifiTest.test_dns()

device_id = config.HOUSEID  # or a unique ID per ESP32
mqtt = MqttLink(device_id)
mqtt.set_cmd_handler(on_cmd)
mqtt.connect()
mqtt.publish_test("test from haus01")
commandHandler.set_state_publisher(mqtt.publish_state)

udp = UdpMessenger(timeout_s=0.02)  # non-blocking

last_heartbeat = ticks_ms()
last_alive = ticks_ms()
loops = 0
last_mqtt_try = 0
mqtt_down_since = None
last_state_emit = ticks_ms()

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
        # displayWriter.clear()
        displayWriter.write_lines("house" + config.HOUSEID + " " + "Mode:","MQTT Cloud")
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
        displayWriter.write_lines("house" + config.HOUSEID + " " + "Mode:","UDP local")
        topic, payload, addr = udp.recv_once(commandHandler.handle_messages)

    hb_age = ticks_diff(now, last_heartbeat)
    if hb_age > 2000:
        topic = config.TOPIC_BASE + config.HOUSEID + "/Status"
        payload = "OK"

        if use_udp:
            print("[HB][UDP] after", hb_age, "ms ->", topic, payload)
            udp.publish(topic, payload)
        else:
            # print("[HB][MQTT] after", hb_age, "ms ->", topic, payload)
            try:
                # mqtt.publish_test("this is a test")   # or mqtt.publish_telemetry(...)
                pass
            except Exception as e:
                print("[MQTT] publish failed:", e)
                mqtt.disconnect()
                if mqtt_down_since is None:
                    mqtt_down_since = now

        last_heartbeat = now

    state_age = ticks_diff(now, last_state_emit)
    if state_age > 10000:
        commandHandler._emit_state()
        last_state_emit = now

    sleep_ms(10)
