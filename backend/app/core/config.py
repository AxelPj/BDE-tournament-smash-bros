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

    # OAuth 42 (Settings > API sur l'intra 42)
    ft_client_id: str = ""
    ft_client_secret: str = ""
    ft_authorize_url: str = "https://api.intra.42.fr/oauth/authorize"
    ft_token_url: str = "https://api.intra.42.fr/oauth/token"
    ft_userinfo_url: str = "https://api.intra.42.fr/v2/me"
    # Hôtes autorisés pour redirect_uri (séparés par des virgules).
    oauth_allowed_redirect_hosts: str = "localhost,127.0.0.1"
    oauth_state_cookie_name: str = "smash_oauth_state"
    oauth_state_ttl_seconds: int = 600


@lru_cache
def get_settings() -> Settings:
    return Settings()
