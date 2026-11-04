"""Commandes d'administration à lancer sur le serveur.

    uv run python -m app.cli create-admin <username> [--display-name NOM]

Crée un compte administrateur (qui sera lié au compte 42 correspondant lors
de sa première connexion OAuth), ou promeut administrateur un compte existant.
"""

import argparse

import app.models  # noqa: F401
from app.core.db import SessionLocal
from app.shop.service import create_gage, list_gages
from app.users.service import create_user, get_user_by_username

DEFAULT_GAGES = [
    {"name": "Marteau doré", "description": "Jouer tout le match sans utiliser le bouclier", "price": 500},
    {"name": "Bob-omb", "description": "Jouer un personnage imposé au hasard", "price": 350},
    {"name": "Étoile", "description": "Jouer avec la manette à l'envers pendant 1 vie", "price": 800},
    {"name": "Champignon", "description": "Interdiction d'utiliser le coup spécial B", "price": 200},
    {"name": "Fleur de feu", "description": "Jouer uniquement avec les attaques Smash", "price": 450},
    {"name": "Poké Ball", "description": "Laisser l'adversaire choisir le stage", "price": 600},
]


def seed_shop() -> None:
    with SessionLocal() as db:
        existing = list_gages(db, shop_only=False, include_archived=True)
        if existing:
            return
        for item in DEFAULT_GAGES:
            create_gage(db, **item)
        print(f"{len(DEFAULT_GAGES)} objets ajoutés dans la boutique en base de données.")


def create_admin(username: str, display_name: str | None) -> None:
    with SessionLocal() as db:
        user = get_user_by_username(db, username)
        if user is not None:
            user.is_admin = True
            db.commit()
            print(f"{user.username} est maintenant administrateur.")
            return

        user = create_user(
            db,
            username=username,
            display_name=display_name or username,
            is_admin=True,
        )
        print(f"Administrateur {user.username} créé.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    admin = commands.add_parser("create-admin", help="créer ou promouvoir un administrateur")
    admin.add_argument("username")
    admin.add_argument("--display-name")
    commands.add_parser("seed-shop", help="initialiser les objets de la boutique si vide")

    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.username, args.display_name)
    elif args.command == "seed-shop":
        seed_shop()


if __name__ == "__main__":
    main()
