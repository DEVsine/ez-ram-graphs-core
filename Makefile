.PHONY: help build up down restart logs shell migrate test clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View logs (all services)"
	@echo "  make logs-web       - View web service logs"
	@echo "  make logs-db        - View database logs"
	@echo "  make shell          - Open Django shell"
	@echo "  make bash           - Open bash in web container"
	@echo "  make migrate        - Run database migrations"
	@echo "  make makemigrations - Create new migrations"
	@echo "  make superuser      - Create Django superuser"
	@echo "  make collectstatic  - Collect static files"
	@echo "  make test           - Run tests"
	@echo "  make clean          - Remove containers and volumes"

# Development commands
build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services started. Access at http://localhost:8001"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

logs-web:
	docker-compose logs -f web

logs-db:
	docker-compose logs -f postgres

logs-neo4j:
	docker-compose logs -f neo4j

shell:
	docker-compose exec web python manage.py shell

bash:
	docker-compose exec web bash

migrate:
	docker-compose exec web python manage.py migrate

makemigrations:
	docker-compose exec web python manage.py makemigrations

superuser:
	docker-compose exec web python manage.py createsuperuser

collectstatic:
	docker-compose exec web python manage.py collectstatic --noinput

test:
	docker-compose exec web python manage.py test

clean:
	docker-compose down -v
	docker system prune -f

# Database backup and restore
backup-db:
	docker-compose exec postgres pg_dump -U postgres ez_ram > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Database backup created"

restore-db:
	@read -p "Enter backup file name: " backup_file; \
	docker-compose exec -T postgres psql -U postgres ez_ram < $$backup_file

# Quick setup for new developers
setup:
	@echo "Setting up ez_ram development environment..."
	cp .env.docker .env
	@echo "Please edit .env file with your configuration"
	@echo "Then run: make build && make up"

