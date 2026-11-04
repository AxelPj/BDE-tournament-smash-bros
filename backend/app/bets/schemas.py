from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BetCreate(BaseModel):
    picked_player_id: int = Field(description="Joueur sur lequel on parie")
    amount: int = Field(ge=1, le=100_000, description="Mise en Tilt")


class PlayerOdds(BaseModel):
    user_id: int
    staked: int = Field(description="Total misé sur ce joueur")
    bettors: int = Field(description="Nombre de parieurs sur ce joueur")
    odds: float | None = Field(
        description="Gain pour 1 Tilt misé si ce joueur gagne : parieurs du match / parieurs "
        "sur ce joueur, avec la cote minimale (None tant que personne n'a parié dessus)"
    )


class MarketRead(BaseModel):
    betting_open: bool
    total: int = Field(description="Total misé sur le match")
    total_bettors: int = Field(description="Nombre de parieurs sur le match")
    players: list[PlayerOdds]


class BetRead(BaseModel):
    id: int
    duel_id: int | None
    tournament_id: int | None
    match_code: str | None
    picked_player_id: int
    opponent_id: int
    amount: int
    created_at: datetime
    status: Literal["open", "closed", "won", "lost", "refunded"] = Field(
        description="open : paris ouverts ; closed : match lancé, en attente du résultat"
    )
    payout: int | None = Field(description="Montant reçu (gain ou remboursement)")
