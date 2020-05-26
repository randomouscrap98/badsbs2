# A simple makefile for setup and run

.PHONY: setup
setup: .venv
	. .venv/bin/activate; \
	python3 -m pip install -Ur requirements.txt; \
	deactivate

.PHONY: run
run: .venv
	. .venv/bin/activate; \
	python3 badsbs2.py; \
	deactivate

.PHONY: clean
	rm -rf .venv

.venv:
	python3 -m venv .venv
