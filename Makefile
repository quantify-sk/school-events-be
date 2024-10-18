#!/usr/bin/make

include .env

help:
	@echo "Available commands:"
	@echo "  install            Install all packages of the poetry project locally."
	@echo "  run-app            Run app locally without docker."
	@echo "  run-dev-build      Run development docker compose and force build containers."
	@echo "  seed-db            Seed the database."
	@echo "  seed-admin-db      Seed only the admin user."
	@echo "  seed-events-db     Seed the events."
	@echo "  seed-users         Seed users (admin, organizers, and school representatives)."
	@echo "  run-dev            Run development docker compose."
	@echo "  stop-dev           Stop development docker compose."
	@echo "  run-prod           Run production docker compose."
	@echo "  stop-prod          Stop production docker compose."
	@echo "  rm-volumes         Remove volumes."
	@echo "  formatter          Apply black formatting to code."
	@echo "  mypy               Check typing."
	@echo "  lint               Lint code with ruff, and check if black formatter should be applied."
	@echo "  lint-watch         Lint code with ruff in watch mode."
	@echo "  lint-fix           Lint code with ruff and try to fix."
	@echo "  logs-dev           Show logs from development docker compose."
	@echo "  logs-prod          Show logs from production docker compose."
	@echo "  reload             Remove volumes, reset git state, rebuild and seed the database."
	@echo "  seed_demo_db       Seed the database with demo data."
	@echo "  seed_reservations_db Seed the reservations."
	

install:
	@echo "Installing all packages with poetry..."
	cd backend/app && poetry install && cd ../..

run-app:
	@echo "Running the app locally without docker..."
	cd backend/app && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 && cd ..

run-dev-build:
	@echo "Running development docker compose with build..."
	docker compose -f docker-compose-dev.yml up --build -d

seed-db:
	@echo "Seeding the database..."
	docker compose -f docker-compose-dev.yml exec fastapi_server poetry run python -m app.db seed

seed-admin-db:
	@echo "Seeding only the admin user..."
	docker compose -f docker-compose-dev.yml exec fastapi_server poetry run python -m app.db admin

seed-events-db:
	@echo "Seeding the events..."
	docker compose -f docker-compose-dev.yml exec fastapi_server poetry run python -m app.db events

seed-users:
	@echo "Seeding users (admin, organizers, and school representatives)..."
	docker compose -f docker-compose-dev.yml exec -T fastapi_server poetry run python -m app.db users

seed-db:
	@echo "Seeding the database..."
	docker compose -f docker-compose-dev.yml exec fastapi_server poetry run python -m app.db seed all

run-dev:
	@echo "Running development docker compose..."
	docker compose -f docker-compose-dev.yml up -d

stop-dev:
	@echo "Stopping development docker compose..."
	docker compose -f docker-compose-dev.yml down

seed-demo-db:
	@echo "Seeding the database with demo data..."
	docker compose -f docker-compose-dev.yml exec fastapi_server poetry run python -m app.db demo

seed-reservations-db:
	@echo "Seeding the reservations..."
	docker compose -f docker-compose-dev.yml exec fastapi_server poetry run python -m app.db reservations

run-prod:
	@echo "Running production docker compose..."
	docker compose up --build -d

stop-prod:
	@echo "Stopping production docker compose..."
	docker compose down

rm-volumes:
	@echo "Removing volumes..."
	docker compose down -v

formatter:
	@echo "Applying black formatting to code..."
	cd backend/app && poetry run black app

mypy:
	@echo "Checking typing with mypy..."
	cd backend/app && poetry run mypy .

lint:
	@echo "Linting code with ruff and checking black formatting..."
	cd backend/app && poetry run ruff app && poetry run black --check app

lint-watch:
	@echo "Linting code with ruff in watch mode..."
	cd backend/app && poetry run ruff app --watch

lint-fix:
	@echo "Linting code with ruff and trying to fix..."
	cd backend/app && poetry run ruff app --fix

logs-dev:
	@echo "Showing logs from development docker compose..."
	docker compose -f docker-compose-dev.yml logs -f

logs-prod:
	@echo "Showing logs from production docker compose..."
	docker compose -f docker-compose.yml logs -f

reload:
	@echo "Reloading: removing volumes, resetting git state, rebuilding, and seeding the database..."
	make rm-volumes && git reset --hard origin/main && make run-dev-build && make seed-demo-db
