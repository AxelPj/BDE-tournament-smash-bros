"""Commandes d'administration à lancer sur le serveur.

    uv run python -m app.cli create-admin <username> [--display-name NOM]

Crée un compte administrateur (mot de passe demandé de façon masquée),
ou promeut administrateur un compte existant.
"""

import argparse
import getpass
import sys

from app.core.db import SessionLocal
from app.users.service import create_user, get_user_by_username


def create_admin(username: str, display_name: str | None) -> None:
    with SessionLocal() as db:
        user = get_user_by_username(db, username)
        if user is not None:
            user.is_admin = True
            db.commit()
            print(f"{user.username} est maintenant administrateur.")
            return

        password = getpass.getpass("Mot de passe : ")
        if len(password) < 8:
            sys.exit("Le mot de passe doit faire au moins 8 caractères.")
        if password != getpass.getpass("Confirmation : "):
            sys.exit("Les mots de passe ne correspondent pas.")
        user = create_user(db, username, display_name or username, password, is_admin=True)
        print(f"Administrateur {user.username} créé.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    admin = commands.add_parser("create-admin", help="créer ou promouvoir un administrateur")
    admin.add_argument("username")
    admin.add_argument("--display-name")

    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.username, args.display_name)


if __name__ == "__main__":
    main()
