from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Identifiant de connexion, stocké en minuscules (normalisé à l'inscription).
    username: Mapped[str] = mapped_column(String(32), unique=True)
    display_name: Mapped[str] = mapped_column(String(64))
    # None pour un compte qui ne se connecte que via l'API 42.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    # Rempli quand le compte est lié à l'intra 42.
    intra_id: Mapped[int | None] = mapped_column(unique=True)
    is_admin: Mapped[bool] = mapped_column(default=False, server_default="0")
    # Solde de Tilt. Ne jamais le modifier directement : passer par
    # app.economy.service.record_transaction, qui l'inscrit dans le journal.
    balance: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (CheckConstraint("balance >= 0", name="balance_non_negative"),)
