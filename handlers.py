import ujson


_lcd = None
_led = None
_status_topic = None


def init(lcd, led, status_topic):
    global _lcd, _led, _status_topic
    _lcd = lcd
    _led = led
    _status_topic = status_topic


def handle_messages(topic, payload, addr):
    if _lcd is None or _led is None or _status_topic is None:
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
                _led.value(1)
            elif task == "off":
                _led.value(0)
            elif task == "set":
                _led.value(1 if value else 0)
            elif task == "toggle":
                _led.value(0 if _led.value() else 1)
            else:
                print("Unknown task:", task)
            return

        print("Unknown peripheral:", peripheral)
        return

    if topic == _status_topic:
        if payload == "OK":
            _lcd.move_to(0, 0)
            _lcd.putstr("Status Haus 1: OK")
        if payload == "ERROR":
            _lcd.move_to(0, 0)
            _lcd.putstr("Status Haus 1: ERROR")
        if payload == "WARNING":
            _lcd.move_to(0, 0)
            _lcd.putstr("Status Haus 1: WARNING")

    # if topic == "haus1/load":
    #     load = int(payload)
    #     if load > 80:
    #         print("High load, reacting...")
    # elif topic == "haus2/alerts":
    #     print("Alert from house2:", payload)
