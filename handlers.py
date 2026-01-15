from time import sleep_ms
from machine import Pin, PWM
from display import Display
import neopixel, config, ujson, network, time, dht, ntptime

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
            "led_state": "off",
            "fan_rpm": 0,
            "rgb_state": "off",
            "temp": None,
            "rssi": None,
        }
        self._publish_state = None

        self.neo_pixel = neopixel.NeoPixel(Pin(RGB_PIN, Pin.OUT), 4)
        self.display = Display()
        self.led = Pin(LED_PIN, Pin.OUT)
        self.fan_duty = FAN_DUTY_MED
        self.status_topic = "haus1/Status"
        self.set_safe_state()
        
    def set_safe_state(self):
        self.led.value(0)
        self.neo_pixel[0] = [0, 0, 0]
        self.neo_pixel.write()
        INA.duty(0)
        INB.duty(0)
        self.fan_duty = 0
        self.state["led_state"] = "off"
        self.state["rgb_state"] = "off"
        self.state["fan_rpm"] = 0

    def set_rgb_state(self, state):
        if state == "on":
            self.neo_pixel[0] = [100, 100, 100]
            self.neo_pixel.write()
        elif state == "off":
            self.neo_pixel[0] = [0, 0, 0]
            self.neo_pixel.write()
        else:
            print("Unknown rgb state:", state)
            return

        self.state["rgb_state"] = state
        self._emit_state()

    def set_led_state(self, state):
        if state == "on":
            self.led.value(1)
        elif state == "off":
            self.led.value(0)
        elif state == "toggle":
            self.led.value(0 if self.led.value() else 1)
        else:
            print("Unknown led state:", state)
            return
    
        self.state["led_state"] = "on" if self.led.value() else "off"
        self._emit_state()
        

    def button_toggle_rgb(self):
        current = self.state.get("rgb_state", "off")
        new_state = "off" if current == "on" else "on"
        self.set_rgb_state(new_state)
    
    def button_toggle_led(self):
        current = self.state.get("led_state", "off")
        new_state = "off" if current == "on" else "on"
        self.set_led_state(new_state)

    def handle_messages(self, topic, payload, addr):
        if self.display is None or self.led is None or self.status_topic is None:
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
                if task == "on":
                    self.set_rgb_state("on")
                elif task == "off":
                    self.set_rgb_state("off")
                else:
                    print("Unknown task:", task)
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
                    self.state["fan_rpm"] = self.fan_duty
                    self._emit_state()
                return
            
            if peripheral == "led":
                if task == "on":
                    self.set_led_state("on")
                elif task == "off":
                    self.set_led_state("off")
                elif task == "toggle":
                    self.set_led_state("toggle")
                else:
                    print("Unknown task:", task)
                return


            print("Unknown peripheral:", peripheral)
            return

        if topic == self.status_topic:
            if payload in ("OK", "ERROR", "WARNING"):
                self.display.write_wrapped("Status Haus 1: " + payload)

    def set_state_publisher(self, fn):
        self._publish_state = fn

    def _emit_state(self):
        try:
            ntptime.settime()
        except OSError as e:
            print("NTP sync failed:", e)
        self.state["ts"] = int((time.time() + 946684800) * 1000)
        wlan = network.WLAN(network.STA_IF)
        self.state["rssi"] = wlan.status("rssi") if wlan.isconnected() else None
        DHT.measure()
        self.state["temp"] = DHT.temperature()

        if self._publish_state:
            self._publish_state(ujson.dumps(self.state))
