import time, config, ujson
from umqtt.simple import MQTTClient

class MqttLink:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.base = "{}/{}".format(config.TOPIC_BASE, device_id)
        self.topic_tele = self.base + "/telemetry"
        self.topic_state = self.base + "/state"
        self.topic_cmd = self.base + "/cmd"
        self.topic_test = "haus/99"

        # Client ID should be unique on the broker
        self.client = MQTTClient(
            client_id=device_id,
            server=config.MQTT_HOST,
            port=config.MQTT_PORT,
            user=config.MQTT_USER,
            password=config.MQTT_PASS,
            keepalive=config.MQTT_KEEPALIVE,
        )

        self._cmd_handler = None
        self.connected = False

    def set_cmd_handler(self, fn):
        """fn(topic_str, payload_str)"""
        self._cmd_handler = fn

    def _on_msg(self, topic, msg):
        # topic/msg come as bytes in MicroPython
        t = topic.decode() if isinstance(topic, (bytes, bytearray)) else str(topic)
        m = msg.decode() if isinstance(msg, (bytes, bytearray)) else str(msg)
        if self._cmd_handler:
            self._cmd_handler(t, m)

    def connect(self):
        self.client.set_callback(self._on_msg)
        self.client.connect()
        self.client.subscribe(self.topic_cmd)
        # Retained "online" state is very handy for dashboards
        self.publish_state('{"online":true}', retain=True)
        self.connected = True

    def disconnect(self):
        try:
            self.publish_state('{"online":false}', retain=True)
        except Exception:
            pass
        try:
            self.client.disconnect()
        except Exception:
            pass
        self.connected = False

    def loop_once(self):
        """
        Non-blocking check for subscribed messages.
        MicroPython recommends check_msg() when you have other foreground work. :contentReference[oaicite:1]{index=1}
        """
        self.client.check_msg()

    def publish_telemetry(self, payload: str, retain=False):
        self.client.publish(self.topic_tele, payload, retain=retain)

    def publish_state(self, payload: str, retain=True):
        self.client.publish(self.topic_state, payload, retain=retain)

    def publish_test(self, payload: str, retain=True):
        print("MQTT MSG: " + payload)
        self.client.publish(self.topic_test, payload, retain=retain)
