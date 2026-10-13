#!/bin/bash

socat pty,raw,echo=0,link=/tmp/esp_fake pty,raw,echo=0,link=/tmp/esp_bridge &
trap "kill $!" EXIT
sleep 0.5
python3 "$(dirname "$0")/fake_esp32.py" /tmp/esp_fake