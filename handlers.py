from time import sleep_ms, ticks_ms, ticks_diff
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

MAX_ACTIVE_PERIPHERALS = 3
PEER_STATE_TTL_MS = 25000
REJECT_DISPLAY_MS = 2000

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
        self._publish_udp_state = None
        self._udp_mode_getter = None
        self._peer_state = {}
        self._peer_last_seen = {}
        self._display_override_until = 0
        self._display_override_lines = ("", "")

        self.neo_pixel = neopixel.NeoPixel(Pin(RGB_PIN, Pin.OUT), 4)
        self.display = Display()
        self.led = Pin(LED_PIN, Pin.OUT)
        self.fan_duty = FAN_DUTY_MED
        self.status_topic = "haus1/Status"
        self.set_safe_state()

    def get_payload_string(self):
        return ujson.dumps(self.state)
        
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

    def display_override_active(self, now=None):
        if now is None:
            now = ticks_ms()
        return ticks_diff(self._display_override_until, now) > 0

    def _set_display_override(self, line1, line2, duration_ms=REJECT_DISPLAY_MS):
        self._display_override_lines = (line1, line2)
        self._display_override_until = ticks_ms() + duration_ms
        self.display.write_lines(line1, line2)

    def _reject_peripheral(self, label):
        self._set_display_override("Reject " + label, "LIMIT REACHED")
        print("Reject", label, "limit reached")

    def _active_total(self, now=None):
        if now is None:
            now = ticks_ms()
        total = 0
        total += 1 if self.state.get("led_state") == "on" else 0
        total += 1 if self._is_rgb_on() else 0
        total += 1 if (self.state.get("fan_rpm") or 0) > 0 else 0
        for house_id, peer in self._peer_state.items():
            last_seen = self._peer_last_seen.get(house_id)
            if last_seen is None:
                continue
            if ticks_diff(now, last_seen) > PEER_STATE_TTL_MS:
                continue
            total += 1 if peer.get("led_on") else 0
            total += 1 if peer.get("rgb_on") else 0
            total += 1 if peer.get("fan_on") else 0
        return total

    def _can_turn_on(self, label, already_on):
        print("in can turn on")
        if already_on:
            return True
        if self._active_total() >= MAX_ACTIVE_PERIPHERALS:
            self._reject_peripheral(label)
            return False
        return True

    def _update_peer_state(self, house_id, payload):
        self._peer_state[house_id] = {
            "led_on": payload.get("led_state") == "on",
            "rgb_on": payload.get("rgb_state") != "off",
            "fan_on": (payload.get("fan_rpm") or 0) > 0,
        }
        self._peer_last_seen[house_id] = ticks_ms()

    def _is_rgb_on(self):
        return self.state.get("rgb_state", "off") != "off"

    def set_rgb_state(self, state):
        print("in rgb state")
        if state == "on":
            already_on = self._is_rgb_on()
            if not self._can_turn_on("RGB", already_on):
                return False
            self.neo_pixel[0] = [100, 100, 100]
            self.neo_pixel.write()
        elif state == "off":
            self.neo_pixel[0] = [0, 0, 0]
            self.neo_pixel.write()
        else:
            print("Unknown rgb state:", state)
            return False

        self.state["rgb_state"] = state
        self._emit_state()
        return True

    def set_rgb_color(self, color):
        print("in rgb color")
        if color == "red":
            rgb = [100, 0, 0]
        elif color == "green":
            rgb = [0, 100, 0]
        elif color == "blue":
            rgb = [0, 0, 100]
        else:
            print("Unknown rgb color:", color)
            return False

        already_on = self._is_rgb_on()
        if not self._can_turn_on("RGB", already_on):
            return False

        self.neo_pixel[0] = rgb
        self.neo_pixel.write()
        self.state["rgb_state"] = color
        self._emit_state()
        return True

    def set_led_state(self, state):
        print("in led state")
        if state == "toggle":
            target_state = "off" if self.led.value() else "on"
        elif state in ("on", "off"):
            target_state = state
        else:
            print("Unknown led state:", state)
            return False

        already_on = self.state.get("led_state") == "on"
        if target_state == "on" and not self._can_turn_on("LED", already_on):
            return False

        self.led.value(1 if target_state == "on" else 0)
        self.state["led_state"] = "on" if self.led.value() else "off"
        self._emit_state()
        return True

    def set_fan_state(self, state):
        print("in fan state")
        if state == "toggle":
            target_state = "off" if (self.state.get("fan_rpm") or 0) > 0 else "on"
        elif state in ("on", "off"):
            target_state = state
        else:
            print("Unknown fan state:", state)
            return

        fan_was_on = (self.state.get("fan_rpm") or 0) > 0
        if target_state == "on" and not self._can_turn_on("FAN", fan_was_on):
            return

        if target_state == "on":
            duty = self.fan_duty or FAN_DUTY_MED
            INA.duty(duty)
            INB.duty(0)
            self.fan_duty = duty
        else:
            self.fan_duty = 0
            INA.duty(0)
            INB.duty(0)

        self.state["fan_rpm"] = self.fan_duty
        self._emit_state()

    def button_toggle_rgb(self):
        current = self.state.get("rgb_state", "off")
        new_state = "off" if current == "on" else "on"
        self.set_rgb_state(new_state)
    
    def button_toggle_led(self):
        current = self.state.get("led_state", "off")
        new_state = "off" if current == "on" else "on"
        self.set_led_state(new_state)

    def button_toggle_fan(self):
        current_on = (self.state.get("fan_rpm") or 0) > 0
        self.set_fan_state("off" if current_on else "on")

    def handle_messages(self, topic, payload, addr):
        if self.display is None or self.led is None or self.status_topic is None:
            print("Handlers not initialized")
            return

        if topic.endswith("/state"):
            try:
                state = ujson.loads(payload)
            except ValueError:
                print("Bad JSON:", payload)
                return
            parts = topic.split("/")
            if len(parts) >= 3:
                house_id = parts[1]
                if house_id != config.HOUSEID:
                    self._update_peer_state(house_id, state)
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
                    if self.set_rgb_state("on"):
                        self._set_display_override("CMD RGB", "ON")
                elif task == "off":
                    if self.set_rgb_state("off"):
                        self._set_display_override("CMD RGB", "OFF")
                elif task in ("red", "green", "blue"):
                    if self.set_rgb_color(task):
                        self._set_display_override("CMD RGB", task.upper())
                else:
                    print("Unknown task:", task)
                return

            if peripheral == "fan":
                fan_was_on = (self.state.get("fan_rpm") or 0) > 0
                if task in ("low", "med", "high", "on", "pulse") and not fan_was_on:
                    if not self._can_turn_on("FAN", fan_was_on):
                        return
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
                    if self.set_led_state("on"):
                        self._set_display_override("CMD LED", "ON")
                elif task == "off":
                    if self.set_led_state("off"):
                        self._set_display_override("CMD LED", "OFF")
                elif task == "toggle":
                    if self.set_led_state("toggle"):
                        state_label = "ON" if self.state.get("led_state") == "on" else "OFF"
                        self._set_display_override("CMD LED", state_label)
                else:
                    print("Unknown task:", task)
                return


            print("Unknown peripheral:", peripheral)
            return

        if topic == self.status_topic:
            if self.display_override_active():
                return
            if payload in ("OK", "ERROR", "WARNING"):
                self.display.write_wrapped("Status Haus 1: " + payload)

    def set_state_publisher(self, fn):
        self._publish_state = fn
    
    def set_udp_state_publisher(self, fn):
        self._publish_udp_state = fn

    def set_udp_mode_getter(self, fn):
        self._udp_mode_getter = fn

    def _emit_state(self):
        if not self._udp_mode_getter or not self._udp_mode_getter():
            try:
                ntptime.settime()
            except OSError as e:
                print("NTP sync failed:", e)
        self.state["ts"] = int((time.time() + 946684800) * 1000)
        wlan = network.WLAN(network.STA_IF)
        self.state["rssi"] = wlan.status("rssi") if wlan.isconnected() else None
        DHT.measure()
        self.state["temp"] = DHT.temperature()

        payload = ujson.dumps(self.state)
        if self._publish_state:                                                                                                                                                                                                           
            self._publish_state(payload)                                                                                                                                                                                                  
        if self._publish_udp_state and self._udp_mode_getter and self._udp_mode_getter():                                                                                                                                                 
            self._publish_udp_state(payload)  
