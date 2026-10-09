import math

from builtin_interfaces.msg import Time

from geometry_msgs.msg import TransformStamped

from nav_msgs.msg import Odometry

from rclpy.node import Node

from sensor_msgs.msg import JointState

from tf2_ros import TransformBroadcaster


class Odom(Node):

    def __init__(self):

        super().__init__('odom_maker')
        self.subscriber = self.create_subscription(
            JointState, '/joint_states', self.odom_maker, 10
        )
        self.publisher = self.create_publisher(Odometry, '/odom', 10)
        self.declare_parameter('radius', 0.0325)
        self.declare_parameter('wheels_distance', 0.2)
        self.declare_parameter('publish_tf', True)
        self.previous_left_angle: float = 0.0
        self.previous_right_angle: float = 0.0
        self.prev_time: Time
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.first_turn = True
        self.speed = 0.0
        self.rot_speed = 0.0
        self.twist_cov = [0.0] * 36
        self.pose_cov = [0.0] * 36
        self.fill_cov_pose(self.pose_cov)
        self.fill_cov_twist(self.twist_cov)
        self.broadcaster = TransformBroadcaster(self)

    def odom_maker(self, states: JointState):
        try:
            left_i = states.name.index('left_wheel_joint')
            right_i = states.name.index('right_wheel_joint')
        except ValueError:
            return

        left_pos = states.position[left_i]
        right_pos = states.position[right_i]
        if self.first_turn:
            self.previous_left_angle = left_pos
            self.previous_right_angle = right_pos
            self.prev_time = states.header.stamp
            self.first_turn = False
        else:
            if self.prev_time == states.header.stamp:
                return
            left_distance, right_distance = self.calculate_distance(
                left_pos, right_pos
            )
            global_distance = (left_distance + right_distance) / 2
            wheels_d = self.get_parameter('wheels_distance').value
            rotation = (right_distance - left_distance) / wheels_d
            delta_x = global_distance * math.cos(self.theta + (rotation / 2))
            delta_y = global_distance * math.sin(self.theta + (rotation / 2))
            self.x += delta_x
            self.y += delta_y
            self.theta += rotation
            self.speed, self.rot_speed = self.calculate_speed(
                states.header.stamp,
                global_distance=global_distance,
                rotation=rotation,
            )
            self.prev_time = states.header.stamp
            self.publisher.publish(self.create_msg(states.header.stamp))
            self.publish_tf(states.header.stamp)

    def calculate_distance(
        self, js_left: float, js_right: float
    ) -> tuple[float, float]:
        right_angle = js_right - self.previous_right_angle
        left_angle = js_left - self.previous_left_angle
        self.previous_right_angle = js_right
        self.previous_left_angle = js_left
        radius = self.get_parameter('radius').value
        return (left_angle * radius, right_angle * radius)

    def calculate_speed(self, time: Time, global_distance, rotation) -> tuple:

        # Nous convertissons en secondes pour pouvoir les soustraire.
        time_sec = time.sec + time.nanosec / 1e9
        prev_time_sec = self.prev_time.sec + self.prev_time.nanosec / 1e9
        delta_time = time_sec - prev_time_sec
        return (global_distance / delta_time, rotation / delta_time)

    def create_msg(self, time: Time) -> Odometry:
        msg = Odometry()
        msg.header.stamp = time
        msg.header.frame_id = 'odom'
        msg.child_frame_id = 'base_link'
        msg.pose.pose.position.x = self.x
        msg.pose.pose.position.y = self.y
        msg.pose.pose.position.z = 0.0
        msg.pose.pose.orientation.z = math.sin(self.theta / 2)
        msg.pose.pose.orientation.w = math.cos(self.theta / 2)
        msg.twist.twist.linear.x = self.speed
        msg.twist.twist.angular.z = self.rot_speed
        msg.pose.covariance = self.pose_cov
        msg.twist.covariance = self.twist_cov
        return msg

    @staticmethod
    def fill_cov_twist(cov_array: list[float]):
        cov_array[0] = 0.0001
        cov_array[7] = 0.0001
        cov_array[14] = 1e6
        cov_array[21] = 1e6
        cov_array[28] = 1e6
        cov_array[35] = 0.001

    @staticmethod
    def fill_cov_pose(cov_array: list[float]):
        cov_array[0] = 0.001
        cov_array[7] = 0.001
        cov_array[14] = 1e6
        cov_array[21] = 1e6
        cov_array[28] = 1e6
        cov_array[35] = 0.03

    def publish_tf(self, time: Time):
        if self.get_parameter('publish_tf').value:
            tf_msg = TransformStamped()
            tf_msg.header.stamp = time
            tf_msg.header.frame_id = 'odom'
            tf_msg.child_frame_id = 'base_link'
            tf_msg.transform.translation.x = self.x
            tf_msg.transform.translation.y = self.y
            tf_msg.transform.translation.z = 0.0
            tf_msg.transform.rotation.z = math.sin(self.theta / 2)
            tf_msg.transform.rotation.w = math.cos(self.theta / 2)
            self.broadcaster.sendTransform(tf_msg)
