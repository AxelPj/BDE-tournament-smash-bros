from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Identifiant de connexion (login 42), stocké en minuscules.
    username: Mapped[str] = mapped_column(String(32), unique=True)
    display_name: Mapped[str] = mapped_column(String(64))
    # Identifiant numérique unique de l'étudiant sur l'intra 42.
    intra_id: Mapped[int | None] = mapped_column(unique=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_admin: Mapped[bool] = mapped_column(default=False, server_default="0")
    # Solde de Tilt. Ne jamais le modifier directement : passer par
    # app.economy.service.record_transaction, qui l'inscrit dans le journal.
    balance: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (CheckConstraint("balance >= 0", name="balance_non_negative"),)
