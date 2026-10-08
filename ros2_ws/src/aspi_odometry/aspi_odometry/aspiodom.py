import math
from builtin_interfaces.msg import Time
from rclpy.node import Node
from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry

RADIUS = 0.0325
WEELS_DISTANCE = 0.2

class Odom(Node):
    def __init__(self):
        super().__init__('odom_maker')
        self.subscriber = self.create_subscription(JointState, '/joint_states', self.odom_maker, 10)
        self.publisher = self.create_publisher(Odometry, '/odom', 10)
        self.previous_left_angle: float = 0.0
        self.previous_right_angle: float = 0.0
        self.prev_time: Time
        self.x = 0
        self.y = 0
        self.delta = 0
        self.first_turn = True
        self.speed = 0
        self.rot_speed = 0


    def odom_maker(self, states: JointState):

        positions: list[float] = states.position
        if self.first_turn or self.prev_time == states.header.stamp:
            self.previous_left_angle = positions[0]
            self.previous_right_angle = positions[1]
            self.prev_time = states.header.stamp
            self.first_turn = False
        else:
            left_distance, right_distance = self.calculate_distance(positions[0], positions[1])
            global_distance = (left_distance + right_distance) / 2
            rotation = (right_distance - left_distance) / WEELS_DISTANCE
            delta_x = global_distance * math.cos(self.delta + (rotation / 2))
            delta_y = global_distance * math.sin(self.delta + (rotation / 2))
            self.x += delta_x
            self.y += delta_y
            self.delta += rotation
            self.speed, self.rot_speed = self.calculate_speed(states.header.stamp, global_distance=global_distance, rotation=rotation)
            self.prev_time = states.header.stamp
            self.publisher.publish(self.create_msg(states.header.stamp))
            

    def calculate_distance(self, js_left: float, js_right: float) -> tuple[float, float]:
        right_angle = js_right - self.previous_right_angle
        left_angle = js_left - self.previous_left_angle
        self.previous_right_angle = js_right
        self.previous_left_angle = js_left
        return (left_angle * RADIUS, right_angle * RADIUS)

    def calculate_speed(self, time: Time, global_distance, rotation) -> tuple:
        delta_time = time - self.prev_time
        return (global_distance / delta_time, rotation / delta_time)

    def create_msg(self, time: Time) -> Odometry:
        msg = Odometry()
        msg.header.stamp = time
        msg.header.frame_id = 'odom'
        msg.child_frame_id = 'base_link'
        msg.pose.pose.position.x = self.x
        msg.pose.pose.position.y = self.y
        msg.pose.pose.position.z = 0.0
        msg.pose.pose.orientation = self.delta
        msg.pose.covariance = 
        msg.twist.twist = 
        msg.twist.covariance = 