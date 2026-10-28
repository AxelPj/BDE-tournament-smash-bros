"""Importe tous les modèles pour qu'Alembic les voie.
Ajouter ici chaque nouveau module de modèles."""

from app.auth.models import AuthSession  # noqa: F401
from app.bets.models import Bet  # noqa: F401
from app.duels.models import Duel  # noqa: F401
from app.economy.models import TiltTransaction  # noqa: F401
from app.gages.models import GageUse  # noqa: F401
from app.game_settings.models import GameSettingsRow  # noqa: F401
from app.shop.models import Gage, InventoryItem  # noqa: F401
from app.tournaments.models import Participant, Tournament, TournamentMatch  # noqa: F401
from app.users.models import User  # noqa: F401
