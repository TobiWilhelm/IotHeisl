# Haus1 IoT Node

MicroPython firmware for an ESP32 that connects to Wi-Fi, talks to an MQTT broker (with UDP fallback).

## What you need
- ESP32 dev board with MicroPython flashed
- 16x2 I2C LCD backpack (default address 0x27; change in code if yours is different)
- Wi-Fi network and MQTT broker reachable (defaults: 192.168.0.113:1883, user tobias; see config.py)
- USB cable and a serial console to see logs at 115200 baud

## Wiring
- LCD SCL -> GPIO22, SDA -> GPIO21, VCC -> 3.3V, GND -> GND
- Leave the backpack pull-ups in place; the code also enables internal pull-ups

## Files
- main.py: boots the device, connects Wi-Fi, runs heartbeat, switches between MQTT and UDP, updates the LCD
- config.py: Wi-Fi, MQTT, UDP, and timing settings
- device_config.py: per-device house name (keeps secrets out of the shared config)
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
- MQTT topics: base is haus/<HOUSE>. Commands arrive on haus/<HOUSE>/cmd. State goes to haus/<HOUSE>/state. Telemetry goes to haus/<HOUSE>/telemetry. A test heartbeat currently publishes to haus/99 from main.py.
- Display updates: handle_messages now looks for topic "<house>/Status" with payloads OK / ERROR / WARNING and writes them to the LCD. Adjust the handler if you want more messages.
- Fallback: if MQTT stays down for ~10s, messages fall back to UDP broadcast "<topic>;<payload>" on port 5005. When MQTT returns, it switches back automatically.
- Heartbeat: every ~2s the loop sends a test message so you can see that the board is alive.
