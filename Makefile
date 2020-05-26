# A simple makefile for setup and run
venv=.venv
setup=$(venv)/setup
py=python3

# The first rule is the default, and it's the one that ensures things are "setup"
# The dependency on "requirements" means that if that changes after the last
# setup, this will run again. Makefiles are cool.
$(setup): requirements.txt $(venv)
	. $(venv)/bin/activate; \
	$(py) -m pip install -Ur requirements.txt; \
	deactivate
	touch $(setup)

# How to create the base virtual environment
$(venv):
	$(py) -m venv $(venv)

.PHONY: run
run: $(setup)
	. $(venv)/bin/activate; \
	$(py) badsbs2.py; \
	deactivate

.PHONY: clean
	rm -rf $(venv)

