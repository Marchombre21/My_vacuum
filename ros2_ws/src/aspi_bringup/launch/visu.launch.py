import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription

from launch.actions import DeclareLaunchArgument

from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node


def generate_launch_description():

    use_sim_time = LaunchConfiguration('use_sim_time')

    rviz_config = os.path.join(
        get_package_share_directory('aspi_bringup'),
        'rviz',
        'aspi.rviz'
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'use_sim_time',
                default_value='false',
                description='Use simulation clock if true',
            ),
            Node(
                package='rviz2',
                executable='rviz2',
                name='rviz2',
                parameters=[
                    {'use_sim_time': use_sim_time}
                ],
                arguments=[
                    '-d',
                    rviz_config
                ]
            ),
        ]
    )
