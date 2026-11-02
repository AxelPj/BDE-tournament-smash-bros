.PHONY: dev up down build restart logs admin test

dev: backend/.env
	docker compose up -d --build
	@echo "Site accessible sur : http://localhost:3000 (ou http://localhost)"

backend/.env:
	cp backend/.env.example backend/.env
	@echo "backend/.env créé : pense à renseigner FT_CLIENT_ID et FT_CLIENT_SECRET !"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

restart:
	docker compose down
	docker compose up -d --build

logs:
	docker compose logs -f

test:
	docker compose exec backend pytest
