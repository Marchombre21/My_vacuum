# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Rules

Don't modify anything in my code without my permission.
Remember that I've never studied math beyond fractions, so feel free to explain things to me if you need to talk about advanced concepts.

## Project overview

Aspi is a home-built robot vacuum. Planned architecture:
- **Raspberry Pi** running ROS 2 (distro `lyrical`): SLAM mapping and path planning.
- **ESP32** (Rust, `no_std`): real-time sensors and actuators (IMU, wheel encoders, motors), sending data to the Pi.
- **Lidar**: Slamtec RPLIDAR **C1M1**, planned to plug **directly into the Pi over USB** (not through the ESP32).
- Development happens on WSL2; the Pi is the deployment target.

## Layout

- `esp32/main.rs` — ESP32 firmware (esp-hal + embassy async). Currently reads an MPU-6500 IMU over I2C (SCL=GPIO18, SDA=GPIO23, address 0x68) and shows the values on an SSD1306 OLED that shares the same bus (`I2cDevice` + `NoopRawMutex`). There is no `Cargo.toml` in the repo yet, so the build command is unknown. Code comments are in French.
- `ros2_ws/` — colcon workspace. Each package has its own folder directly under `src/` (colcon stops descending once it finds a `package.xml`, so packages must never be nested).
  - `src/aspi_bringup/` — the user's own ament_cmake package (still an empty skeleton). Meant to hold the launch files and `.yaml` configs that start the whole robot (rplidar, slam_toolbox, Nav2, ESP32 bridge).
  - `src/rplidar/` — Slamtec's `rplidar_ros` (branch `ros2`), package name `rplidar_ros`. Its files are tracked directly by the main git repo (no nested repo, no submodule). Its root `CMakeLists.txt` has local changes (`ament_target_dependencies` → `target_link_libraries`).
- Nav2 and slam_toolbox are meant to be installed with `apt`, not added as source to the workspace.

## Build & run (ROS 2)

- Build everything from `ros2_ws/`:
  ```bash
  cd ros2_ws
  source /opt/ros/lyrical/setup.zsh
  colcon build --symlink-install
  source install/setup.zsh
  ros2 launch rplidar_ros view_rplidar_c1_launch.py   # C1: 460800 baud, /dev/ttyUSB0 by default
  ```
- `src/rplidar/` still contains old `build/`, `install/` and `log/` folders from when it was built on its own. They are git-ignored and no longer used.
- On WSL2, RViz needs `export QT_QPA_PLATFORM=xcb`. Otherwise Qt picks Wayland while Ogre uses GLX, and you get "Invalid parentWindowHandle". If the 3D view stays black: `export LIBGL_ALWAYS_SOFTWARE=1`.
- `ament_target_dependencies` is deprecated in this distro. Use `target_link_libraries` with the target names: `rclcpp::rclcpp`, `${<msg_pkg>_TARGETS}`.
- No tests exist yet. `aspi_bringup` only has the default `ament_lint_auto` setup (`colcon test`).
