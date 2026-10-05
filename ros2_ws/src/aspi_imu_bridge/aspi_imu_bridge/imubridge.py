import math
import statistics
import struct

from rclpy.node import Node
from sensor_msgs.msg import Imu
from serial import Serial

PACKET_SIZE = 17
ACC_SENSI = 16384
GYRO_SENSI = 131
ACC_CONV_M_PER_S = 9.80665
GYRO_CONV_RAD = math.pi / 180
CALIB_SIZE = 200


class ImuBridge(Node):

    def __init__(self):
        super().__init__('imu_bridge')
        self.declare_parameter('port', '/dev/serial0')
        self.declare_parameter('frame_id', 'imu_link')
        port = self.get_parameter('port').value
        self.ser = Serial(port, 115200, timeout=0)
        self.buffer = bytearray()
        self.publisher = self.create_publisher(Imu, '/imu/data_raw', 10)
        self.timer = self.create_timer(0.005, self.read_serial)
        self.calib_samples = []
        self.gyro_bias = None

    def read_serial(self):
        self.buffer += self.ser.read(self.ser.in_waiting)
        while True:
            i = self.buffer.find(b'\xaa\x55')
            if (i == -1):
                del self.buffer[:-1]
                break
            else:
                del self.buffer[:i]

            if len(self.buffer) < PACKET_SIZE:
                break

            if (sum(self.buffer[2:PACKET_SIZE - 1]) % 256) != self.buffer[PACKET_SIZE - 1]:
                del self.buffer[0]
                continue

            # Voir notes
            values = struct.unpack('>7h', self.buffer[2:16])
            accel_x, accel_y, accel_z, temp_raw, gyro_x, gyro_y, gyro_z = values
            del self.buffer[:PACKET_SIZE]

            ax = accel_x / ACC_SENSI * ACC_CONV_M_PER_S
            ay = accel_y / ACC_SENSI * ACC_CONV_M_PER_S
            az = accel_z / ACC_SENSI * ACC_CONV_M_PER_S
            temp_raw = (temp_raw / 340.0) + 36.53
            gx = gyro_x / GYRO_SENSI * GYRO_CONV_RAD
            gy = gyro_y / GYRO_SENSI * GYRO_CONV_RAD
            gz = gyro_z / GYRO_SENSI * GYRO_CONV_RAD

            if self.gyro_bias is None:
                self.calib_samples.append((ax, ay, az, gx, gy, gz))
                if len(self.calib_samples) == CALIB_SIZE:
                    self.finish_calibration()
                continue

            imu = Imu()
            imu.header.stamp = self.get_clock().now().to_msg()
            imu.header.frame_id = self.get_parameter('frame_id').value
            imu.orientation_covariance[0] = -1.0
            imu.angular_velocity_covariance[0] = self.gyro_var[0]
            imu.angular_velocity_covariance[4] = self.gyro_var[1]
            imu.angular_velocity_covariance[8] = self.gyro_var[2]
            imu.linear_acceleration_covariance[0] = self.accel_var[0]
            imu.linear_acceleration_covariance[4] = self.accel_var[1]
            imu.linear_acceleration_covariance[8] = self.accel_var[2]
            imu.angular_velocity.x = gx - self.gyro_bias[0]
            imu.angular_velocity.y = gy - self.gyro_bias[1]
            imu.angular_velocity.z = gz - self.gyro_bias[2]
            imu.linear_acceleration.x = ax
            imu.linear_acceleration.y = ay
            imu.linear_acceleration.z = az
            self.publisher.publish(imu)

    def finish_calibration(self):
        columns = list(zip(*self.calib_samples))
        self.accel_var = [statistics.pvariance(c) for c in columns[:3]]
        self.gyro_var = [statistics.pvariance(c) for c in columns[3:]]
        self.gyro_bias = [statistics.fmean(c) for c in columns[3:]]
        self.calib_samples = []
        self.get_logger().info('Calibration Complete')
