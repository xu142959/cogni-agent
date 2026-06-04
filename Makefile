.PHONY: install test lint build docker docker-run clean

# ─── Development ────────────────────────────────────────────

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=cogni_agent --cov-report=term-missing

test-integration:
	pytest tests/integration/ -v

lint:
	ruff check src/ --fix

# ─── Build ──────────────────────────────────────────────────

build:
	python -m build --wheel

publish:
	twine upload dist/*

# ─── Docker ─────────────────────────────────────────────────

docker:
	docker build -t cogni-agent:latest .

docker-run:
	docker run -it --rm \
		-e OPENAI_API_KEY=$${OPENAI_API_KEY} \
		cogni-agent:latest

docker-compose-up:
	docker-compose up -d

docker-compose-down:
	docker-compose down

# ─── Web Console ────────────────────────────────────────────

web-console:
	cd web_console && python app.py

# ─── Clean ──────────────────────────────────────────────────

clean:
	rm -rf dist/ build/ *.egg-info .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null