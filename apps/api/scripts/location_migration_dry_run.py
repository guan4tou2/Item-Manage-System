"""Phase 26 位置樹遷移 dry-run（唯讀）。

在 Alembic `0020` 之前執行，人工審查遷移將產生的樹與報告；不寫入任何資料。

用法（容器內，舊版堆疊即可）::

    docker compose cp apps/api/app/services/location_tree_migration.py \\
        api:/app/app/services/location_tree_migration.py
    docker compose cp apps/api/scripts/location_migration_dry_run.py \\
        api:/app/scripts/location_migration_dry_run.py
    docker compose exec -T api python scripts/location_migration_dry_run.py
"""
from __future__ import annotations

import asyncio
import json

from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.services.location_tree_migration import analyze_flat, preview_paths


async def main() -> None:
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.connect() as conn:
            report = await conn.run_sync(analyze_flat)
            paths = await conn.run_sync(preview_paths)
    finally:
        await engine.dispose()

    print(
        json.dumps(
            {"report": report.as_dict(), "planned_paths": paths},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
