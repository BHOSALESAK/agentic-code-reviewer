PYTHON ?= .venv/bin/python
PNPM ?= corepack pnpm

.PHONY: bootstrap dev test lint build

bootstrap:
	$(PYTHON) -m pip install -e 'backend[dev]'
	cd frontend && $(PNPM) install

dev:
	trap 'kill 0' INT TERM EXIT; \
	(cd backend && ../$(PYTHON) -m uvicorn app.main:app --host 127.0.0.1 --port 8000) & \
	(cd frontend && $(PNPM) run dev --host 127.0.0.1 --port 5173) & \
	wait

test:
	cd backend && ../$(PYTHON) -m pytest
	cd frontend && $(PNPM) run typecheck

lint:
	cd backend && ../$(PYTHON) -m ruff check app tests

build:
	cd frontend && $(PNPM) run build
