from time import sleep_ms, ticks_ms 
from machine import SoftI2C, Pin 
from i2c_lcd import I2cLcd 
import config
from net import WiFiManager, Tester, UdpMessenger
import time
from time import sleep_ms, ticks_ms, ticks_diff

DEFAULT_I2C_ADDR = 0x27

def handle_messages(topic, payload, addr):
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

m = UdpMessenger(timeout_s=0.02)  # non-blocking

while True:
    topic = config.HOUSE + "/Status"
    payload = "OK"
    print("[HB] send after", hb_age, "ms ->", topic, payload)
    m.publish(topic, payload)
    time.sleep(5)    

last_heartbeat = ticks_ms()
last_alive = ticks_ms()
loops = 0

while True:
    now = ticks_ms()
    loops += 1
    # 1) Poll incoming messages (fast, doesn’t block)
    topic, payload, addr = m.recv_once(handle_messages)
    # if got:
    #     print("[UDP] rx handled at", now)

    hb_age = ticks_diff(now, last_heartbeat)
    if hb_age > 2000:
        topic = config.HOUSE + "/Status"
        payload = "OK"
        print("[HB] send after", hb_age, "ms ->", topic, payload)
        m.publish(topic, payload)
        last_heartbeat = ticks_ms()  # reset using fresh time

    alive_age = ticks_diff(now, last_alive)
    if alive_age > 1000:
        print("[LOOP] alive. loops/s≈", loops, "ms_since_hb=", ticks_diff(now, last_heartbeat))
        loops = 0
        last_alive = now

    # 2) Do your normal work (LCD, sensors, logic, etc.)
    #    Example: heartbeat send every 2 seconds
    # if ticks_diff(ticks_ms(), last_heartbeat) > 2000:
    #     m.publish(config.HOUSE + "/Status", "OK")
    #     last_heartbeat = ticks_ms()

    # 3) Small sleep to yield CPU / WiFi stack
    sleep_ms(10)








# The following line of code should be tested
# using the REPL:

# 1. To print a string to the LCD:
#    lcd.putstr('Hello world')
# 2. To clear the display:
#lcd.clear()
# 3. To control the cursor position:
# lcd.move_to(2, 1)
# 4. To show the cursor:
# lcd.show_cursor()
# 5. To hide the cursor:
#lcd.hide_cursor()
# 6. To set the cursor to blink:
#lcd.blink_cursor_on()
# 7. To stop the cursor on blinking:
#lcd.blink_cursor_off()
# 8. To hide the currently displayed character:
#lcd.display_off()
# 9. To show the currently hidden character:
#lcd.display_on()
# 10. To turn off the backlight:
#lcd.backlight_off()
# 11. To turn ON the backlight:
#lcd.backlight_on()
# 12. To print a single character:
#lcd.putchar('x')
# 13. To print a custom character:
#happy_face = bytearray([0x00, 0x0A, 0x00, 0x04, 0x00, 0x11, 0x0E, 0x00])
#lcd.custom_char(0, happy_face)
#lcd.putchar(chr(0))
