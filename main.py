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

BUTTON_PIN = 16
BUTTON_DEBOUNCE_MS = 15
button1 = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
button_pressed = False
button_press_ms = ticks_ms()

BUTTON2_PIN = 27
button2 = Pin(BUTTON2_PIN, Pin.IN, Pin.PULL_UP)
button2_pressed = False
button2_press_ms = ticks_ms()

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
# mqtt.connect()
# mqtt.publish_test("test from haus01")
commandHandler.set_state_publisher(mqtt.publish_state)

udp = UdpMessenger(timeout_s=0.02)  # non-blocking
commandHandler.set_udp_state_publisher(udp.publish_state)
commandHandler.set_udp_mode_getter(udp.get_udp_mode)

last_heartbeat = ticks_ms()
last_alive = ticks_ms()
loops = 0
last_mqtt_try = 0
mqtt_down_since = None
last_state_emit = ticks_ms()
button_press_count = 0
last_tcp_check = ticks_ms()
tcp_fail_count = 0

while True:
    now = ticks_ms()
    print("loop")

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
        if not commandHandler.display_override_active(now):
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
    udp.update_udp_mode(use_udp)
    
    if use_udp:
        if not commandHandler.display_override_active(now):
            displayWriter.write_lines("house" + config.HOUSEID + " " + "Mode:","UDP local")
        udp.recv_once(commandHandler.handle_messages)

    btn_val = button1.value()
    if not button_pressed and btn_val == 0:
        button_pressed = True
        button_press_ms = now
    elif button_pressed and btn_val == 1:
        if ticks_diff(now, button_press_ms) > BUTTON_DEBOUNCE_MS and (button_press_count % 2):
            commandHandler.button_toggle_led()
        else:
            commandHandler.button_toggle_rgb()
        button_pressed = False
        button_press_count += 1

    btn2_val = button2.value()
    if not button2_pressed and btn2_val == 0:
        button2_pressed = True
        button2_press_ms = now
    elif button2_pressed and btn2_val == 1:
        if ticks_diff(now, button2_press_ms) > BUTTON_DEBOUNCE_MS:
            commandHandler.button_toggle_fan()
        button2_pressed = False

    hb_age = ticks_diff(now, last_heartbeat)
    state_age = ticks_diff(now, last_state_emit)
    if hb_age > 2000:

        if not use_udp:
            # print("[HB][MQTT] after", hb_age, "ms ->", topic, payload)
            if ticks_diff(now, last_tcp_check) > 3000:
                last_tcp_check = now
                if wifiTest.test_internet(config.MQTT_HOST, config.MQTT_PORT, display=False):
                    tcp_fail_count = 0
                else:
                    tcp_fail_count += 1
                    if tcp_fail_count >= 3:
                        print("[MQTT] TCP check failed 3 times, switching to UDP")
                        mqtt.disconnect()
                        if mqtt_down_since is None:
                            mqtt_down_since = now

        if state_age > 10000:
            commandHandler._emit_state()
            last_state_emit = now

        last_heartbeat = now

    sleep_ms(10)
