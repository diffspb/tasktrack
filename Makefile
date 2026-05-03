IMAGE  = ghcr.io/diffspb/tasktrack
TAG   ?= latest

COMPOSE = docker compose -f docker-compose.yml -f docker-compose.prod.yml

.PHONY: docker frontend-install frontend frontend-test frontend-build gen-types

# --- Docker / деплой ---

# Собрать образ и запушить в GHCR. Требует: docker login ghcr.io
docker:
	docker build -t $(IMAGE):$(TAG) .
	docker push $(IMAGE):$(TAG)

# --- Фронтенд (локальная разработка) ---

frontend-install:
	cd frontend && npm install

frontend:
	cd frontend && npm run dev

frontend-test:
	cd frontend && npm test

frontend-build:
	cd frontend && npm run build

gen-types:
	cd frontend && npx openapi-typescript http://localhost:8000/openapi.json \
		-o src/shared/api/types.ts
