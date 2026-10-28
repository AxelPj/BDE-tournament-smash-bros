from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class GameSettingsRow(Base):
    """Réglages globaux du site (une seule ligne, id = 1), modifiables par les admins.
    Le contenu est validé par app.game_settings.service.GameSettings."""

    __tablename__ = "game_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
