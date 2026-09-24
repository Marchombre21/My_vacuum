# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace layout

This is a ROS 2 colcon workspace (`~/ros2_ws`), not itself a git repository. The only package,
`src/sam_bot_description/`, is its own git repo (remote: `git@github.com:Marchombre21/Aspirateur.git`) — commit
from inside that directory, not the workspace root.

ROS 2 distro: **lyrical** (installed at `/opt/ros/lyrical`).

## Common commands

Build (run from `~/ros2_ws`, not from inside the package):
```bash
colcon build
```
Always build from the workspace root — a `colcon build` run from inside `src/sam_bot_description/` creates a
stray nested `build/`/`install`/`log` there instead of at the workspace root, which the launch files won't use.

Source the workspace overlay before running anything:
```bash
source install/setup.zsh
```

Launch the full simulation (Gazebo + robot_state_publisher + rviz2 + robot_localization EKF):
```bash
ros2 launch sam_bot_description display.launch.py
```
**Gazebo starts paused.** `/clock` stays at 0 until you press ▶ Play in the Gazebo GUI, and `robot_localization`'s
`ekf_filter_node` (which uses `use_sim_time`) will sit on "Waiting for clock to start..." and never publish
`odometry/filtered` / `accel/filtered` until the sim is running.

Lint (ament):
```bash
colcon test --packages-select sam_bot_description
colcon test-result --verbose
```

## Architecture

Single-package robot description/simulation stack, structured around `launch/display.launch.py`:

- **Robot model**: `src/description/sam_bot_description.sdf` is an SDF file authored with embedded `xacro:`
  properties/macros (`xacro:property`, `xacro:macro` for inertia calculations) and is expanded by `xacro` at
  launch time via `Command(['xacro ', LaunchConfiguration('model')])` — there is no separate `.xacro` file.
- **Simulation**: `world/my_world.sdf` defines the Gazebo (`gz sim`) world/physics. The launch file starts the
  server as a composable node (`GzServer` from `ros_gz_sim.actions`) inside a shared `ros_gz_container`
  component container, plus a separate `gz sim -g` process for the GUI-only client.
- **ROS ↔ Gazebo bridge**: `config/bridge_config.yaml` maps Gazebo topics to ROS 2 topics (loaded into the same
  `ros_gz_container` via `RosGzBridge`). Sensor/actuator topic names must match across three places that have to
  stay in sync: the SDF plugins (`<topic>` tags on the IMU sensor and `<odom_topic>` on the DiffDrive plugin),
  `bridge_config.yaml`, and `config/ekf.yaml`'s `odom0`/`imu0` fields (currently `demo/odom`, `demo/imu`).
- **State estimation**: `config/ekf.yaml` configures `robot_localization`'s `ekf_filter_node`. It fuses wheel
  odometry (`demo/odom`, position+yaw only) and IMU (`demo/imu`, yaw-rate + linear acceleration) into
  `odometry/filtered` and (since `publish_acceleration: true`) `accel/filtered`, and broadcasts `odom -> base_link`
  over `/tf`.
- **Visualization**: `rviz/config.rviz` is the default RViz layout, loaded via the `rvizconfig` launch argument.

All launch arguments (`use_sim_time`, `model`, `rvizconfig`) are declared with defaults at the bottom of
`generate_launch_description()` in `display.launch.py` — override them with `ros2 launch sam_bot_description
display.launch.py <arg>:=<value>`.

## Rules

Don't modify anything in my code without my permission.
Remember that I've never studied math beyond fractions, so feel free to explain things to me if you need to talk about advanced concepts.