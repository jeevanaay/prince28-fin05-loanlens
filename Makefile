
.PHONY: help install dev up down logs ps test test-integration cov lint format migrate seed

help:
	@echo "LoanLens - Available Commands"
	@echo "make install          Install dependencies"
	@echo "make dev              Run development server"
	@echo "make up               Build and start Docker services"
	@echo "make down             Stop Docker services"
	@echo "make logs             Follow API logs"
	@echo "make ps               Show service status"
	@echo "make test             Run unit tests"
	@echo "make test-integration Run integration tests"
	@echo "make cov              Generate coverage report"
	@echo "make lint             Run Ruff lint checks"
	@echo "make format           Check Ruff formatting"
	@echo "make migrate          Apply database migrations"
	@echo "make seed             Load sample data"

install:
	uv sync

dev:
	uv run poe dev

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api

ps:
	docker compose ps

test:
	uv run poe test

test-integration:
	uv run poe test-integration

cov:
	uv run poe cov

lint:
	uv run ruff check .

format:
	uv run ruff format --check .

migrate:
	uv run poe migrate

seed:
	uv run poe seed
