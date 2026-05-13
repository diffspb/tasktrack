.PHONY: install db-start db-stop db-create reset full-reset dev test test-cov mcp-bootstrap

install:
	pip install -e ".[dev]"

# Запустить dev-БД через Docker
db-start:
	docker run -d --name tasktrack-dev \
	  -e POSTGRES_DB=tasktrack \
	  -e POSTGRES_USER=tasktrack \
	  -e POSTGRES_PASSWORD=tasktrack \
	  -p 5432:5432 \
	  postgres:16-alpine

db-stop:
	docker stop tasktrack-dev && docker rm tasktrack-dev

reset:
	python scripts/reset_db.py

# Снести контейнер целиком, поднять заново и засеять
full-reset:
	-docker stop tasktrack-dev && docker rm tasktrack-dev
	docker run -d --name tasktrack-dev \
	  -e POSTGRES_DB=tasktrack \
	  -e POSTGRES_USER=tasktrack \
	  -e POSTGRES_PASSWORD=tasktrack \
	  -p 5432:5432 \
	  postgres:16-alpine
	@echo "Waiting for PostgreSQL to be ready..."
	@until docker exec tasktrack-dev pg_isready -U tasktrack -q; do sleep 1; done
	python scripts/reset_db.py

dev:
	uvicorn app.main:app --reload --port 8000

# Тесты используют SQLite in-memory — не нужен PostgreSQL
test:
	pytest tests/ -x -v

test-cov:
	pytest tests/ --cov=app --cov-report=term-missing

mcp-bootstrap:
	python scripts/bootstrap_agent_user.py
