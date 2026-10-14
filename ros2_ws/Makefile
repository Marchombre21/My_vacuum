SHELL := /bin/bash

build:
	colcon build --symlink-install

run:
# 	ros2 run launch

test:
	colcon test $(if $(PKG),--packages-select $(PKG))
	colcon test-result $(if $(PKG),--test-result-base build/$(PKG)) --verbose

clean-packages:
	rm -rf {build,install,log}

clean-pycache:
	find src -name __pycache__ -type d -prune -exec rm -rf {} +

clean-all: clean-packages clean-pycache

.PHONY: build run test clean-all clean-packages clean-pycache
