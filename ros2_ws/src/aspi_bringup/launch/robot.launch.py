import os
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from launch.substitutions import LaunchConfiguration


def generate_launch_description():

    use_sim_time = LaunchConfiguration('use_sim_time')
    port = LaunchConfiguration('port')
    description_file = os.path.join(
        get_package_share_directory('aspi_bringup'),
        'launch',
        'description.launch.py')
    rsp_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(description_file),
        launch_arguments={'use_sim_time': use_sim_time}.items()
        )

    return LaunchDescription([
            DeclareLaunchArgument(
                'port',
                default_value='/dev/serial0',
                description='Serial port of the ESP32'),
            DeclareLaunchArgument(
                'use_sim_time',
                default_value='false',
                description='Use simulation clock if true'),
            rsp_node,
            Node(
                package='aspi_imu_bridge',
                executable='imu_bridge',
                parameters=[{'port': port}]),
            Node(
                package='aspi_odometry',
                executable='odom_maker'
            )
        ])