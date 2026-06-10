.PHONY: dev-infra dev-api dev-web lint test fmt

dev-infra:
	docker compose up -d db valkey minio

dev-api:
	cd backend && uvicorn app.main:app --reload

dev-web:
	cd frontend && npm run dev

lint:
	cd backend && ruff check . && ruff format --check .
	cd frontend && npx tsc --noEmit

test:
	cd backend && pytest -q

fmt:
	cd backend && ruff format .
