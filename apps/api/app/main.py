from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_config import configure_logging
from app.middleware.observability import ObservabilityMiddleware
from app.routes import (
    admin,
    ai,
    ai_drafts,
    ai_receipts,
    ai_search,
    auth,
    backup,
    barcodes,
    batches,
    categories,
    customization,
    external_channels,
    groups,
    health,
    images,
    item_history,
    items,
    items_bulk,
    jobs,
    labels,
    lists,
    loans,
    locations,
    notifications,
    public_lists,
    reports,
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
    configure_logging(settings.log_format, settings.log_level)
    app = FastAPI(
        title=settings.app_name,
        version="2.0.0a0",
        openapi_url="/api/openapi.json" if settings.api_docs_enabled else None,
        docs_url="/api/docs" if settings.api_docs_enabled else None,
        redoc_url="/api/redoc" if settings.api_docs_enabled else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ObservabilityMiddleware)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(categories.router)
    app.include_router(locations.router)
    app.include_router(tags.router)
    # Phase 41：`/api/items/labels.pdf` 必須早於 items 的 `/{item_id}`（否則會被 UUID 驗證吃掉）
    app.include_router(labels.router)
    app.include_router(items_bulk.router)
    app.include_router(items.router)
    app.include_router(batches.router)
    app.include_router(batches.item_consume_router)
    app.include_router(stats.router)
    app.include_router(notifications.router)
    app.include_router(reports.router)
    app.include_router(public_lists.router)
    app.include_router(lists.router)
    app.include_router(groups.router)
    app.include_router(loans.router)
    app.include_router(transfers.router)
    app.include_router(admin.router)
    app.include_router(images.router)
    app.include_router(ai.router)
    app.include_router(ai_drafts.router)
    app.include_router(ai_receipts.router)
    app.include_router(ai_search.router)
    app.include_router(customization.router)
    app.include_router(item_history.router)
    app.include_router(stocktake.router)
    app.include_router(external_channels.router)
    app.include_router(warehouses.router)
    app.include_router(backup.router)
    app.include_router(webhooks.router)
    app.include_router(jobs.router)
    app.include_router(labels.location_router)
    app.include_router(barcodes.router)
    return app


app = create_app()
