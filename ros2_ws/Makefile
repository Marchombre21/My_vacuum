SHELL := /bin/bash

build:
	colcon build --symlink-install

run:
# 	ros2 run launch

test:
# 	$(PYTHON) -m pytest -v

clean-all:
	rm -rf {build,install,log}

lint:
# 	python3 -m flake8 .
# 	python3 -m mypy . \
# 	--warn-return-any \
# 	--warn-unused-ignores \
# 	--ignore-missing-imports \
# 	--disallow-untyped-defs \
# 	--check-untyped-defs \

.PHONY: build run test clean-all lint