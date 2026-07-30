from typing import Optional

from fastapi import FastAPI

from app.api import routes_candles, routes_health, routes_symbols


def create_app(lifespan: Optional[object] = None) -> FastAPI:
    app = FastAPI(title="historical-data-service", lifespan=lifespan)
    app.include_router(routes_health.router)
    app.include_router(routes_candles.router)
    app.include_router(routes_symbols.router)
    return app
