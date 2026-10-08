from rclpy.node import Node
from sensor_msgs.msg import JointState

RADIUS = 0.0325

class Odom(Node):
    def __init__(self):
        super().__init__('odom_maker')
        self.subscriber = self.create_subscription(JointState, '/joint_states', self.odom_maker)
        self.previous_left_angle: float = 0.0
        self.previous_right_angle: float = 0.0
        self.left_angle: float = 0.0
        self.right_angle: float = 0.0
        self.left_distance_traveled = 0
        self.right_distance_traveled = 0
        self.first_turn = True


    def odom_maker(self, positions: list[float]):

        if self.first_turn:
            self.previous_left_angle = positions[0]
            self.previous_right_angle = positions[1]
            self.first_turn = False
        else:
            self.right_angle = positions[1] - self.previous_right_angle
            self.left_angle = positions[0] - self.previous_left_angle
            self.previous_right_angle = positions[1]
            self.previous_left_angle = positions[0]
            self.left_distance_traveled = self.left_angle * RADIUS