# IOT Project

MicroPython firmware for an ESP32 that connects to Wi-Fi, talks to an MQTT broker, and shows status messages on a 16x2 I2C LCD. If MQTT is down, it uses a small UDP fallback.

## What you need
- ESP32 dev board with MicroPython flashed
- 16x2 I2C LCD backpack (default address 0x27; change in code if yours is different)
- Wi-Fi network and MQTT broker reachable (defaults: 192.168.0.113:1883, user tobias; see config.py)
- USB cable and a serial console to see logs at 115200 baud

## Files
- main.py: boots the device, connects Wi-Fi, runs heartbeat, switches between MQTT and UDP, updates the LCD
- config.py: Wi-Fi, MQTT, UDP, and timing settings
- device_config.py: per-device house name (keeps the device identity separate from shared config)
- mqtt_client.py: thin wrapper around umqtt.simple with prebuilt topic names
- net.py: Wi-Fi helper, connectivity tests, and UDP messenger
- lcd_api.py / i2c_lcd.py: LCD driver for the 16x2 display

## Quick start
1) Flash MicroPython onto the ESP32 (one-time setup)
2) Copy these files to the board (mpremote, Thonny, or Pymakr all work)
3) Edit config.py to match your Wi-Fi and MQTT broker; set HOUSE in device_config.py (e.g., haus1, haus2)
4) Reset the board and open the serial console at 115200 to watch the boot logs
5) You should see Wi-Fi connect, MQTT connect, and periodic test publishes

## How it talks
- MQTT topics: base is haus/\<HOUSEID\>. Commands arrive on haus/\<HOUSEID\>/cmd. State goes to haus/\<HOUSEID\>/state. Telemetry goes to haus/\<HOUSEID\>/telemetry. A periodic test publish currently goes to haus/99 from main.py.
- Display updates: the LCD updates when the handler receives topic haus1/Status with payload OK / ERROR / WARNING. With the current code this happens via UDP fallback (MQTT subscribes to haus/\<HOUSEID\>/cmd, which does not match haus1/Status).
- Fallback: if MQTT stays down for ~10s, the loop listens for UDP broadcasts and the heartbeat is sent as UDP {topic};{payload} on port 5005. It does not forward all MQTT topics over UDP.
- Heartbeat: every ~2s the loop sends a test message; it is MQTT when connected, or UDP when in fallback.

## UDP vs MQTT message format
- UDP broadcast in this repo is a single text string built like the mqtt standard as {topic};{payload}. Example: haus/01/Status;OK. It is sent to "\<BROADCAST_IP\>:\<UDP_PORT\>" and the receiver splits on the first ; to recover topic and payload.
- MQTT messages carry topic and payload as separate fields in the protocol. You publish to a broker, and subscribers receive the topic and payload without manual formatting.

## Example status message (UDP)
Send a UDP broadcast with the text "haus1/Status;OK" to port 5005.
Example (Linux/macOS): echo -n "haus1/Status;OK" | nc -u -b 192.168.0.255 5005
