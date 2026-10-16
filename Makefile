ifeq ($(OS),Windows_NT)
PYTHON ?= python
else
PYTHON ?= python3
endif

.PHONY: verify
verify:
	$(PYTHON) -m pip install -r backend/requirements.txt -r requirements-dev.txt
	$(PYTHON) -m tools.verify
