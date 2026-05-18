from __future__ import annotations

from fastapi import FastAPI

from urban_lens.api.routers import catalog, health, internal, metadata, query, system


def register_routers(app: FastAPI) -> None:
    app.include_router(health.router)
    app.include_router(system.router)
    app.include_router(query.router)
    app.include_router(catalog.router)
    app.include_router(metadata.router)
    app.include_router(internal.router)
