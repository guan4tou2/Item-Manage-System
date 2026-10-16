"""排程 job registry 與 runner。

外部 cron（管理員 PAT）呼叫 `POST /api/jobs/{job_name}/run`；本模組負責：
開列 `job_runs`（`running` 立即落地，部分成功可觀測）→ 執行 job spec
（`today`＝Asia/Taipei 今天）→ 收尾 `succeeded`／`failed` ＋ result。
Phase 31 `report.monthly` 以 `register(JobSpec(...))` 掛載即可。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import today_taipei
from app.models.job_run import JobRun
from app.repositories import job_runs_repository as repo

logger = logging.getLogger(__name__)


class UnknownJobError(Exception):
    def __init__(self, name: str):
        super().__init__(f"unknown job: {name}")
        self.name = name


@dataclass
class JobResult:
    """`processed`＝處理列數；`emitted`＝摘要 dispatch 數；`errors` 非空 → failed。"""

    processed: int = 0
    emitted: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "processed": self.processed,
            "emitted": self.emitted,
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class JobSpec:
    name: str
    run: Callable[[AsyncSession, date], Awaitable[JobResult]]


JOBS: dict[str, JobSpec] = {}


def register(spec: JobSpec) -> None:
    JOBS[spec.name] = spec


async def run_job(session: AsyncSession, name: str) -> JobRun:
    """執行 job 並記錄 `job_runs`；未知 job → `UnknownJobError`（route 轉 404）。"""
    spec = JOBS.get(name)
    if spec is None:
        raise UnknownJobError(name)

    row = await repo.create_running(session, name)
    await session.commit()

    try:
        result = await spec.run(session, today_taipei())
    except Exception as exc:  # noqa: BLE001 — job 失敗不外拋，記入 run
        logger.exception("job %s 執行失敗", name)
        status = "failed"
        payload: dict[str, object] = {
            "processed": 0,
            "emitted": 0,
            "errors": [f"{type(exc).__name__}: {exc}"],
        }
    else:
        status = "failed" if result.errors else "succeeded"
        payload = result.as_dict()

    await repo.finish(session, row, status=status, result=payload)
    await session.commit()
    return row
