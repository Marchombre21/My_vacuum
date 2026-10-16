SHELL := /bin/bash

build:
	colcon build --symlink-install

run-fake-esp:
	./../tools/fake_esp32.sh

run-launch:
	ros2 launch aspi_bringup robot.launch.py $(if $(USB), esp_port:='$(USB)')
test:
	colcon test $(if $(PKG),--packages-select $(PKG))
	colcon test-result $(if $(PKG),--test-result-base build/$(PKG)) --verbose

clean-packages:
	rm -rf {build,install,log}

clean-pycache:
	find src -name __pycache__ -type d -prune -exec rm -rf {} +

clean-all: clean-packages clean-pycache

.PHONY: build run-fake-esp run-launch test clean-all clean-packages clean-pycache
