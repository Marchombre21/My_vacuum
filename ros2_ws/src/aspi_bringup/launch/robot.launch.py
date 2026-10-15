import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node


def generate_launch_description():

    use_sim_time = LaunchConfiguration('use_sim_time')
    esp_port = LaunchConfiguration('esp_port')
    description_file = os.path.join(
        get_package_share_directory('aspi_bringup'),
        'launch',
        'description.launch.py',
    )
    rsp_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(description_file),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
    )

    slam_launch_file = os.path.join(
        get_package_share_directory('slam_toolbox'),
        'launch',
        'online_async_launch.py'
    )

    slam_yaml = os.path.join(
        get_package_share_directory('aspi_bringup'),
        'config',
        'slam_toolbox.yaml'
    )

    slam_node = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(slam_launch_file),
            launch_arguments={
                'slam_params_file': slam_yaml,
                'use_sim_time': use_sim_time,
            }.items(),
        )

    lidar_port = LaunchConfiguration('lidar_port')

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'lidar_port',
                default_value='/dev/ttyUSB0',
                description='Specifying usb port to connected lidar',
            ),
            DeclareLaunchArgument(
                'esp_port',
                default_value='/dev/serial0',
                description='Serial port of the ESP32',
            ),
            DeclareLaunchArgument(
                'use_sim_time',
                default_value='false',
                description='Use simulation clock if true',
            ),
            slam_node,
            rsp_node,
            Node(
                package='aspi_imu_bridge',
                executable='imu_bridge',
                parameters=[{'port': esp_port}],
            ),
            Node(package='aspi_odometry', executable='odom_maker'),
            Node(
                package='rplidar_ros',
                executable='rplidar_node',
                name='rplidar_node',
                parameters=[
                    {
                        'serial_port': lidar_port,
                        'serial_baudrate': 460800,
                        'frame_id': 'laser',
                        'angle_compensate': True,
                        'scan_mode': 'Standard',
                    }
                ],
                output='screen',
            ),
        ]
    )
