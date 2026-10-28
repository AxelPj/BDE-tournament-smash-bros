"""Point d'entrée de l'API.

Toutes les routes sont sous /api pour que le frontend Next.js puisse
les proxifier sur la même origine (cookies de session sans CORS).
"""

from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.bets.router import router as bets_router
from app.core.config import get_settings
from app.duels.router import router as duels_router
from app.economy.router import router as economy_router
from app.gages.router import router as gages_router
from app.game_settings.router import router as settings_router
from app.shop.router import router as shop_router
from app.tournaments.router import router as tournaments_router
from app.users.router import router as users_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(tournaments_router)
app.include_router(economy_router)
app.include_router(shop_router)
app.include_router(duels_router)
app.include_router(bets_router)
app.include_router(gages_router)
app.include_router(settings_router)


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    """Permet de vérifier que l'API répond."""
    return {"status": "ok", "environment": settings.environment}
