from time import sleep_ms
from machine import SoftI2C, Pin, PWM
from i2c_lcd import I2cLcd
import neopixel, config, ujson, network, time, dht

DEFAULT_I2C_ADDR = 0x27

LED_PIN = 12

FAN_DUTY_LOW = 600
FAN_DUTY_MED = 700
FAN_DUTY_HIGH = 850
FAN_PULSE_MS = 500
INA = PWM(Pin(19, Pin.OUT), 10000) #INA corresponds to IN+
INB = PWM(Pin(18, Pin.OUT), 10000) #INB corresponds to IN- 

RGB_PIN = 26

DHT = dht.DHT11(Pin(17))

class Handler:
    def __init__(self):

        self.state = {                                                                                                                                                                                                                                                                                               
            "house": config.HOUSEID,                                                                                                                                                                                                                                                                                 
            "led": {"state": "off"},
            "fan": {"rpm": 0},
            "rgb": {"state": "off"},
            "temp": None,
            "rssi": None,
        }
        self._publish_state = None

        scl_pin = Pin(22, Pin.OUT, pull=Pin.PULL_UP)  # Enable the internal pull-up for GPIO22.
        sda_pin = Pin(21, Pin.OUT, pull=Pin.PULL_UP)  # Enable the internal pull-up for GPIO21.

        i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)

        devices = i2c.scan()
        if not devices:
            print("No I2C device was detected! Check the wiring / power supply / pull-up resistor.")
        else:
            print("Detected device address:", [hex(addr) for addr in devices])  # Output hexadecimal address‌:ml-citation{ref="3,8" data="citationList"}

        self.neo_pixel = neopixel.NeoPixel(Pin(RGB_PIN, Pin.OUT), 4) 
        self.lcd = I2cLcd(i2c, DEFAULT_I2C_ADDR, 2, 16)
        self.led = Pin(LED_PIN, Pin.OUT)
        self.fan_duty = FAN_DUTY_MED
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

            if peripheral == "rgb":
                state = "off"
                skip_state = False
                if task == "on":
                    colors = [[100,100,100]]
                    self.neo_pixel[0] = colors[0]
                    self.neo_pixel.write()
                    state = "on"
                elif task == "off":
                    colors = [[0,0,0]]
                    self.neo_pixel[0] = colors[0]
                    self.neo_pixel.write()
                    state = "off"
                else:
                    print("Unknown task:", task)
                    skip_state = True
                
                if not skip_state:
                    self.state["rgb"]["state"] = state 
                    self._emit_state()
                return

            if peripheral == "fan":
                skip_state = False
                if task == "low":
                    self.fan_duty = FAN_DUTY_LOW
                    INA.duty(self.fan_duty)
                    INB.duty(0)
                elif task == "med":
                    self.fan_duty = FAN_DUTY_MED
                    INA.duty(self.fan_duty)
                    INB.duty(0)
                elif task == "high":
                    self.fan_duty = FAN_DUTY_HIGH
                    INA.duty(self.fan_duty)
                    INB.duty(0)
                elif task == "on":
                    duty = self.fan_duty or FAN_DUTY_MED
                    INA.duty(duty)
                    INB.duty(0)
                    self.fan_duty = duty
                elif task == "off":
                    self.fan_duty = 0
                    INA.duty(0)
                    INB.duty(0)
                elif task == "pulse":
                    count = 0
                    pulses = int(value)
                    while count < pulses:
                        INA.duty(FAN_DUTY_HIGH)
                        INB.duty(0)
                        sleep_ms(FAN_PULSE_MS)
                        INA.duty(0)
                        INB.duty(0)
                        sleep_ms(FAN_PULSE_MS)
                        count+=1
                else:
                    print("Unknown task:", task)
                    skip_state = True

                if not skip_state:
                    self.state["fan"]["rpm"] = self.fan_duty
                    self._emit_state()
                return
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

                self.state["led"]["state"] = "on" if self.led.value() else "off"
                self._emit_state()
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

    def set_state_publisher(self, fn):
        self._publish_state = fn

    def _emit_state(self):
        self.state["ts"] = int(time.time())
        wlan = network.WLAN(network.STA_IF)
        self.state["rssi"] = wlan.status("rssi") if wlan.isconnected() else None
        DHT.measure()
        self.state["temp"] = DHT.temperature()

        if self._publish_state:
            self._publish_state(ujson.dumps(self.state))
