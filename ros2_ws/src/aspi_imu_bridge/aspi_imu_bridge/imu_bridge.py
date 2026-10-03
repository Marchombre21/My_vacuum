import rclpy
from aspi_imu_bridge.imubridge import ImuBridge


def main():
    rclpy.init()
    node = ImuBridge()
    rclpy.spin(node)
    node.ser.close()
    node.destroy_node()
    rclpy.shutdown()
