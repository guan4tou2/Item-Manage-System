"""排程 job 端點（Phase 24）：外部 cron ＋ 冪等 job 執行。

觸發權＝帳號管理員（`get_current_admin`，比 `process-retries` 更嚴；
cron 文件範例使用管理員 PAT）；狀態查詢任何登入者可讀（唯讀觀測，
無 payload 外洩）。未知 `job_name` 一律 404。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories import job_runs_repository
from app.schemas.jobs import (
    JobResultPayload,
    JobRunInfo,
    JobRunResult,
    JobStatus,
    JobThresholds,
)
from app.services import expiry_scan, jobs_service, reports_service  # noqa: F401 — import 觸發 job 註冊

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("/{job_name}/run", response_model=JobRunResult)
async def run_job(
    job_name: str,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> JobRunResult:
    try:
        row = await jobs_service.run_job(session, job_name)
    except jobs_service.UnknownJobError:
        raise HTTPException(status_code=404, detail="unknown job") from None

    payload = row.result or {}
    return JobRunResult(
        job=row.job_name,
        status=row.status,
        processed=int(payload.get("processed", 0)),
        emitted=int(payload.get("emitted", 0)),
    )


@router.get("/{job_name}/status", response_model=JobStatus)
async def job_status(
    job_name: str,
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> JobStatus:
    spec = jobs_service.JOBS.get(job_name)
    if spec is None:
        raise HTTPException(status_code=404, detail="unknown job")

    last = await job_runs_repository.latest(session, job_name)
    return JobStatus(
        job=job_name,
        thresholds=JobThresholds(
            stale_after_hours=spec.stale_after_hours, **spec.thresholds
        ),
        last_run=(
            JobRunInfo(
                status=last.status,
                started_at=last.started_at,
                finished_at=last.finished_at,
                result=JobResultPayload(**last.result) if last.result else None,
            )
            if last is not None
            else None
        ),
        stale=jobs_service.is_stale(last, spec.stale_after_hours),
    )
