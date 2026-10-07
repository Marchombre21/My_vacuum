# 1. Terminal 1 : socat -d -d pty,raw,echo=0 pty,raw,echo=0
# 2. Terminal 2 : python3 tools/fake_esp32.py /dev/pts/X, avec le premier des deux ports affichés
# 3. Terminal 3 : sourcer, puis lancer le bridge avec port:=/dev/pts/Y, le second port
# 4. Terminal 4 : sourcer, puis ros2 topic echo /imu/data_raw

import random
import struct
import sys
import time

from serial import Serial

PORT = sys.argv[1]


def make_packet(values, left_total, right_total):

    data = struct.pack('>7h2i', *values, left_total, right_total)
    checksum = sum(data) % 256
    return b'\xaa\x55' + data + bytes([checksum])


def main():
    rt = 0
    lt = 0
    ser = Serial(PORT, 115200)
    try:
        while True:
            rt -= 5
            lt += 5
            values = [0 + random.randint(-20, 20),
                      0 + random.randint(-20, 20),
                      16384 + random.randint(-20, 20),
                      25,
                      120 + random.randint(-20, 20),
                      50 + random.randint(-20, 20),
                      90 + random.randint(-20, 20)]
            ser.write(make_packet(values, lt, rt))
            time.sleep(0.01)
    finally:
        ser.close()


main()