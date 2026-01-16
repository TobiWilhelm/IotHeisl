import network
import time
import socket
import time
import config
from machine import SoftI2C, Pin 
from i2c_lcd import I2cLcd 
import errno
from display import Display

DEFAULT_I2C_ADDR = 0x27
scl_pin = Pin(22, Pin.OUT, pull=Pin.PULL_UP)  # Enable the internal pull-up for GPIO22.
sda_pin = Pin(21, Pin.OUT, pull=Pin.PULL_UP)  # Enable the internal pull-up for GPIO21.

i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)

devices = i2c.scan()
if not devices:
    print("No I2C device was detected! Check the wiring / power supply / pull-up resistor.")
else:
    print("Detected device address:", [hex(addr) for addr in devices])  # Output hexadecimal address‌:ml-citation{ref="3,8" data="citationList"}

lcd = I2cLcd(i2c, DEFAULT_I2C_ADDR, 2, 16)
displayWriter = Display()


class UdpMessenger:
    def __init__(self, timeout_s=0.02):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print("UDP socket created:", self.s)
        print("  AF_INET =", socket.AF_INET, "SOCK_DGRAM =", socket.SOCK_DGRAM)

        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        print("Broadcast option set: SOL_SOCKET =", socket.SOL_SOCKET,
                "SO_BROADCAST =", socket.SO_BROADCAST, "value =", 1)

        #bind for recieving
        self.s.bind(("", config.UDP_PORT))  # "" = all interfaces
        self.s.settimeout(timeout_s)
        self.is_udp_mode = False

    def update_udp_mode(self, val:bool):
        self.is_udp_mode = val
    
    def get_udp_mode(self):
        return self.is_udp_mode
    
    def publish_state(self, payload):
        topic = config.TOPIC_BASE + "/" +  config.HOUSEID + "/state"
        msg = "{};{}".format(topic, payload)
        self.s.sendto(msg.encode(), (config.BROADCAST_IP, config.UDP_PORT))
        print("Sent:", msg)
    def publish_status(self, payload):
        topic = config.TOPIC_BASE + "/" +  config.HOUSEID + "/Status"
        msg = "{};{}".format(topic, payload)
        self.s.sendto(msg.encode(), (config.BROADCAST_IP, config.UDP_PORT))
        print("Sent:", msg)

    def recv_once(self, handler):
        try:
            data, addr = self.s.recvfrom(1024)
        except OSError as e:
            # Nothing received (non-blocking or timed out)
            # MicroPython often uses errno 11 for EAGAIN.
            if e.args and e.args[0] in (errno.EAGAIN, errno.ETIMEDOUT, 11, 110):
                return None, None, None
            raise

        text = data.decode()
        try:
            topic, payload = text.split(";", 1)
        except ValueError:
            print("Could not decode Message.")
            return False

        handler(topic, payload, addr)
        return True

    def listen_forever(self, handler):
        """
        handler(topic, payload, addr) will be called for each valid message.
        """
        while True:
            topic, payload, addr = self.recv_once()
            if topic is None:
                continue
            handler(topic, payload, addr)

class Tester:
    def __init__(self):
        pass

    def test_internet(self, host="1.1.1.1", port=53, timeout=3, display=True):
        line_two = (host + " " +  str(port))
        if display:
            displayWriter.write_lines("Test Connect:", line_two)
        try:
            addr = socket.getaddrinfo(host, port)[0][-1]
            print("Connecting to", addr, "...")
            s = socket.socket()
            s.settimeout(timeout)
            s.connect(addr)
            s.close()
            print("TCP connect OK")
            return True
        except OSError as e:
            print("Internet test failed:", e)
            return False
        
    def test_dns(self, host="google.com", display=True):
        if display:
            displayWriter.write_lines("Test DNS:", host)
        try:
            print("Resolving", host, "...")
            addr_info = socket.getaddrinfo(host, 80)
            print("DNS OK, got:", addr_info[0][-1])
            return True
        except OSError as e:
            print("DNS lookup failed:", e)
            return False

class WiFiManager:
    def __init__(self, ssid, password, max_retries=10):
        self.ssid = ssid
        self.password = password
        self.max_retries = max_retries
        self._sta = network.WLAN(network.STA_IF)
        self._sta.active(True)

    def _reset_iface(self):
        # fully toggle the interface to clear "sta is connecting" state
        print("Resetting WiFi interface...")
        try:
            self._sta.disconnect()
        except OSError:
            pass  # ignore if not connected
        self._sta.active(False)
        time.sleep(0.5)
        self._sta.active(True)
        time.sleep(0.5)

    def connect(self):
        if self._sta.isconnected():
            print("Already connected to:", config.WIFI_SSID, "-> IfConfig", self._sta.ifconfig())
            return True
        
        # try to start a fresh connection
        attempt = 0
        while attempt < 10:
            attempt += 1
            print("Connecting to WiFi: {} (attempt {})".format(self.ssid, attempt))

            try:
                self._sta.connect(self.ssid, self.password)
            except OSError as e:
                # this is where "Wifi Internal Error" happens
                print("connect() raised OSError:", e)
                self._reset_iface()
                continue  # retry outer while

            retries = self.max_retries
            while not self._sta.isconnected() and retries > 0:
                print("  waiting...", retries)
                time.sleep(1)
                retries -= 1

            if self._sta.isconnected():
                print("Connected:", self._sta.ifconfig())
                return True
            
            print("Connect attempt timed out, resetting iface and retrying...")
            self._reset_iface()

        print("❌ Failed to connect after several attempts.")
        return False

    def disconnect(self):
        if self._sta.isconnected():
            print("Disconnecting WiFi")
            self._sta.disconnect()

    def is_connected(self):
        return self._sta.isconnected()

    def ifconfig(self):
        return self._sta.ifconfig()
