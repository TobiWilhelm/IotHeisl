import ujson
from machine import SoftI2C, Pin
from i2c_lcd import I2cLcd

DEFAULT_I2C_ADDR = 0x27
LED_PIN = 12

class Handler:
    def __init__(self):
        scl_pin = Pin(22, Pin.OUT, pull=Pin.PULL_UP)  # Enable the internal pull-up for GPIO22.
        sda_pin = Pin(21, Pin.OUT, pull=Pin.PULL_UP)  # Enable the internal pull-up for GPIO21.

        i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)

        devices = i2c.scan()
        if not devices:
            print("No I2C device was detected! Check the wiring / power supply / pull-up resistor.")
        else:
            print("Detected device address:", [hex(addr) for addr in devices])  # Output hexadecimal address‌:ml-citation{ref="3,8" data="citationList"}

        self.lcd = I2cLcd(i2c, DEFAULT_I2C_ADDR, 2, 16)
        self.led = Pin(LED_PIN, Pin.OUT)
        self.status_topic = "haus1/Status"

    def handle_messages(self, topic, payload, addr):
        if self.lcd is None or self.led is None or self.status_topic is None:
            print("Handlers not initialized")
            return

        print("in handle message")
        if topic.endswith("/cmd"):
            try:
                cmd = ujson.loads(payload)
            except ValueError:
                print("Bad JSON:", payload)
                return

            peripheral = cmd.get("peripheral")
            task = cmd.get("task")
            value = cmd.get("value")

            if peripheral == "led":
                if task == "on":
                    self.led.value(1)
                elif task == "off":
                    self.led.value(0)
                elif task == "set":
                    self.led.value(1 if value else 0)
                elif task == "toggle":
                    self.led.value(0 if self.led.value() else 1)
                else:
                    print("Unknown task:", task)
                return

            print("Unknown peripheral:", peripheral)
            return

        if topic == self.status_topic:
            if payload == "OK":
                self.lcd.move_to(0, 0)
                self.lcd.putstr("Status Haus 1: OK")
            if payload == "ERROR":
                self.lcd.move_to(0, 0)
                self.lcd.putstr("Status Haus 1: ERROR")
            if payload == "WARNING":
                self.lcd.move_to(0, 0)
                self.lcd.putstr("Status Haus 1: WARNING")

        # if topic == "haus1/load":
        #     load = int(payload)
        #     if load > 80:
        #         print("High load, reacting...")
        # elif topic == "haus2/alerts":
        #     print("Alert from house2:", payload)
