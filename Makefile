.PHONY: list up down doctor help

PYTHON ?= python3

help:
	@echo "Usage: make <target> [id=<atom-id>]"
	@echo ""
	@echo "Targets:"
	@echo "  list              Show all available atoms."
	@echo "  up   id=<atom-id> Start the vulnerable + fixed pair."
	@echo "  down id=<atom-id> Stop and remove the atom's containers."
	@echo "  doctor            Sanity-check your local setup."

list:
	@$(PYTHON) atom list

up:
	@test -n "$(id)" || (echo "error: pass id=<atom-id>" >&2; exit 1)
	@$(PYTHON) atom up $(id)

down:
	@test -n "$(id)" || (echo "error: pass id=<atom-id>" >&2; exit 1)
	@$(PYTHON) atom down $(id)

doctor:
	@$(PYTHON) atom doctor
