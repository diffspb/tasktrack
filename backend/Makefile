.PHONY: install db-start db-create reset dev test test-cov

install:
	pip install -e ".[dev]"

# Запустить локальный PostgreSQL (WSL)
db-start:
	sudo service postgresql start

# Создать БД и пользователя (один раз после установки PostgreSQL)
db-create:
	sudo -u postgres psql -c "CREATE USER tasktrack WITH PASSWORD 'tasktrack';" || true
	sudo -u postgres psql -c "CREATE DATABASE tasktrack OWNER tasktrack;" || true

reset:
	python scripts/reset_db.py

dev:
	uvicorn app.main:app --reload --port 8000

# Тесты используют SQLite in-memory — не нужен PostgreSQL
test:
	pytest tests/ -x -v

test-cov:
	pytest tests/ --cov=app --cov-report=term-missing
