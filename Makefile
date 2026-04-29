.PHONY: frontend-install frontend frontend-test frontend-build gen-types

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
