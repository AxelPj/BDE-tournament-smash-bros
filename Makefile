.PHONY: dev up down build restart logs admin test prod prod-down prod-logs

DC_DEV  = docker compose
DC_PROD = docker compose -f docker-compose.prod.yml

# PROD=1 : cible les conteneurs de production (ex : make admin LOGIN=... PROD=1)
ifeq ($(PROD),1)
DC = $(DC_PROD)
else
DC = $(DC_DEV)
endif

dev: backend/.env
	docker compose up -d --build
	@echo "Site accessible sur : http://localhost:3000 (ou http://localhost)"

backend/.env:
	cp backend/.env.example backend/.env
	@echo "backend/.env créé : pense à renseigner FT_CLIENT_ID et FT_CLIENT_SECRET !"

.env:
	cp .env.example .env
	@echo ".env créé : renseigne DOMAIN (nom de domaine du VPS) avant make prod !"

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

# Passer un compte administrateur (créé s'il n'existe pas encore)
#   make admin LOGIN=<login_42> [NAME="Nom affiché"] [PROD=1]
admin:
	@if [ -z "$(LOGIN)" ]; then \
		echo "Usage : make admin LOGIN=<login_42> [NAME=\"Nom affiché\"] [PROD=1]"; \
		exit 1; \
	fi
	$(DC) exec backend python -m app.cli create-admin "$(LOGIN)" $(if $(NAME),--display-name "$(NAME)")

# --- Production (VPS) ---
prod: backend/.env .env
	$(DC_PROD) up -d --build --remove-orphans --wait

prod-down:
	$(DC_PROD) down

prod-logs:
	$(DC_PROD) logs -f
