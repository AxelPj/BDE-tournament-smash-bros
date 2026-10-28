# Backend — API FastAPI

## Prérequis

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (gère l'environnement virtuel et les dépendances)

## Installation

```bash
cd backend
uv sync              # crée .venv et installe les dépendances (dont celles de dev)
cp .env.example .env
```

## Base de données

SQLite, emplacement défini par `DATABASE_URL`. Le schéma est géré par Alembic :

```bash
uv run alembic upgrade head                                 # applique les migrations
uv run alembic revision --autogenerate -m "description"     # après modification d'un modèle
```

Toute migration générée doit être relue avant d'être appliquée.
Un nouveau module de modèles doit être importé dans `app/models.py`.

## Lancer l'API

```bash
uv run uvicorn app.main:app --reload
```

- Santé : http://localhost:8000/api/health
- Documentation interactive (contrat de l'API pour le frontend) : http://localhost:8000/api/docs
- Schéma OpenAPI brut : http://localhost:8000/api/openapi.json

## Créer un administrateur

```bash
uv run python -m app.cli create-admin <username> [--display-name "Nom affiché"]
```

Crée le compte (mot de passe demandé de façon masquée) ou promeut un compte existant.
C'est la seule façon d'obtenir des droits admin : aucune route de l'API ne le permet.

## Tests

```bash
uv run pytest
```

## Déploiement (serveur distant)

Aucune valeur propre à une machine n'est dans le code : tout passe par les variables d'environnement.

```bash
uv sync --no-dev
export DATABASE_URL=sqlite:////chemin/absolu/persistant/smash.db
export ENVIRONMENT=prod
uv run alembic upgrade head        # à chaque déploiement, avant de démarrer
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Le fichier SQLite (et ses fichiers `-wal` / `-shm`) doit être sur un disque persistant et sauvegardé.
