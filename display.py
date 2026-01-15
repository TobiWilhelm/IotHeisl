from machine import SoftI2C, Pin
from i2c_lcd import I2cLcd

DEFAULT_I2C_ADDR = 0x27
DEFAULT_SCL_PIN = 22
DEFAULT_SDA_PIN = 21
DEFAULT_FREQ = 100000
DEFAULT_ROWS = 2
DEFAULT_COLS = 16


class Display:
    def __init__(
        self,
        i2c_addr=DEFAULT_I2C_ADDR,
        scl_pin=DEFAULT_SCL_PIN,
        sda_pin=DEFAULT_SDA_PIN,
        freq=DEFAULT_FREQ,
        rows=DEFAULT_ROWS,
        columns=DEFAULT_COLS,
        scan=True,
    ):
        self._rows = rows
        self._cols = columns

        Pin(scl_pin, Pin.OUT, pull=Pin.PULL_UP)
        Pin(sda_pin, Pin.OUT, pull=Pin.PULL_UP)

        self._i2c = SoftI2C(scl=Pin(scl_pin), sda=Pin(sda_pin), freq=freq)

        if scan:
            devices = self._i2c.scan()
            if not devices:
                print(
                    "No I2C device was detected! Check the wiring / power supply / pull-up resistor."
                )
            else:
                print("Detected device address:", [hex(addr) for addr in devices])

        self._lcd = I2cLcd(self._i2c, i2c_addr, rows, columns)

    def clear(self):
        self._lcd.clear()

    def write_line(self, row, text):
        if row < 0 or row >= self._rows:
            return
        if text is None:
            text = ""
        text = str(text)
        if len(text) > self._cols:
            text = text[: self._cols]
        elif len(text) < self._cols:
            text = text + (" " * (self._cols - len(text)))

        self._lcd.move_to(0, row)
        self._lcd.putstr(text)

    def write_lines(self, line1="", line2=""):
        self.write_line(0, line1)
        if self._rows > 1:
            self.write_line(1, line2)

    def write_wrapped(self, text):
        if text is None:
            text = ""
        text = str(text)
        for row in range(self._rows):
            start = row * self._cols
            segment = text[start : start + self._cols]
            self.write_line(row, segment)
