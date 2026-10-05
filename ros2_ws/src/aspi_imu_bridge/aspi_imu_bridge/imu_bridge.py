from aspi_imu_bridge.imubridge import ImuBridge
import rclpy


def main():
    rclpy.init()
    node = ImuBridge()
    try:
        rclpy.spin(node)
    finally:
        node.ser.close()
        node.destroy_node()
        rclpy.shutdown()
