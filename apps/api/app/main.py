from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import (
    admin,
    ai,
    auth,
    backup,
    categories,
    customization,
    external_channels,
    groups,
    health,
    images,
    item_history,
    items,
    labels,
    lists,
    loans,
    locations,
    notifications,
    stats,
    stocktake,
    tags,
    transfers,
    users,
    warehouses,
    webhooks,
)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="2.0.0a0",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(categories.router)
    app.include_router(locations.router)
    app.include_router(tags.router)
    app.include_router(items.router)
    app.include_router(stats.router)
    app.include_router(notifications.router)
    app.include_router(lists.router)
    app.include_router(groups.router)
    app.include_router(loans.router)
    app.include_router(transfers.router)
    app.include_router(admin.router)
    app.include_router(images.router)
    app.include_router(ai.router)
    app.include_router(customization.router)
    app.include_router(item_history.router)
    app.include_router(stocktake.router)
    app.include_router(external_channels.router)
    app.include_router(warehouses.router)
    app.include_router(backup.router)
    app.include_router(webhooks.router)
    app.include_router(labels.router)
    return app


app = create_app()
