"""Configuration lue depuis les variables d'environnement et le .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Smash BDE API"
    environment: str = "dev"
    # En production, pointer vers un chemin absolu sur un disque persistant,
    # ex : sqlite:////var/lib/smash/smash.db
    database_url: str = "sqlite:///./smash.db"

    session_cookie_name: str = "smash_session"
    session_lifetime_days: int = 30
    # True en production (HTTPS) : le cookie n'est alors jamais envoyé en clair.
    cookie_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
