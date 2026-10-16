from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import _utcnow
from app.models.job_run import JobRun


async def create_running(session: AsyncSession, job_name: str) -> JobRun:
    row = JobRun(job_name=job_name, status="running")
    session.add(row)
    await session.flush()
    return row


async def finish(
    session: AsyncSession, row: JobRun, *, status: str, result: dict[str, Any]
) -> JobRun:
    row.status = status
    row.result = result
    row.finished_at = _utcnow()
    await session.flush()
    return row


async def latest(session: AsyncSession, job_name: str) -> JobRun | None:
    stmt = (
        select(JobRun)
        .where(JobRun.job_name == job_name)
        .order_by(JobRun.started_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()
