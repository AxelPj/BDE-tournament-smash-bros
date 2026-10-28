from enum import StrEnum

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.game_settings.models import GameSettingsRow


class Mode(StrEnum):
    """Modes de jeu activables. Un mode désactivé bloque les actions des joueurs
    (pas celles des admins, ni la consultation, ni le règlement des gains)."""

    TOURNAMENTS = "tournaments"
    DUELS = "duels"
    SHOP = "shop"
    BETS = "bets"
    GAGES = "gages"


MODE_LABELS = {
    Mode.TOURNAMENTS: "Les inscriptions aux tournois sont désactivées",
    Mode.DUELS: "Les duels sont désactivés",
    Mode.SHOP: "La boutique est fermée",
    Mode.BETS: "Les paris sont désactivés",
    Mode.GAGES: "Les gages sont désactivés",
}


class GameSettings(BaseModel):
    """Réglages globaux. Une valeur absente de la base prend sa valeur par défaut."""

    tournaments_enabled: bool = Field(default=True, description="Inscription libre aux tournois")
    duels_enabled: bool = Field(default=True, description="Création et acceptation de duels")
    shop_enabled: bool = Field(default=True, description="Achats en boutique")
    bets_enabled: bool = Field(default=True, description="Prise de paris")
    gages_enabled: bool = Field(default=True, description="Gages imposés dans les matchs")

    max_gages_per_player: int = Field(
        default=3, ge=0, le=20, description="Gages qu'un joueur peut imposer par match"
    )
    duel_gage_win_reward: int = Field(
        default=50, ge=0, le=100_000, description="Tilt par gage validé quand sa cible gagne le duel"
    )


def get_game_settings(db: Session) -> GameSettings:
    row = db.get(GameSettingsRow, 1)
    return GameSettings(**(row.data if row else {}))


def is_enabled(db: Session, mode: Mode) -> bool:
    return getattr(get_game_settings(db), f"{mode}_enabled")


def update_game_settings(db: Session, settings: GameSettings) -> GameSettings:
    row = db.get(GameSettingsRow, 1) or GameSettingsRow(id=1)
    row.data = settings.model_dump()
    db.add(row)
    db.commit()
    return settings
