from aspi_odometry.aspiodom import Odom
import rclpy


def main():
    rclpy.init()
    node = Odom()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown() 