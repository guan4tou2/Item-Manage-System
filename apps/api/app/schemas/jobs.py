from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class JobRunResult(BaseModel):
    """`POST /api/jobs/{job_name}/run` 回應（`status`＝succeeded／failed）。"""

    job: str
    status: str
    processed: int
    emitted: int


class JobThresholds(BaseModel):
    """設定頁顯示用；`stale_after_hours` 為通用停跑判定，其餘由 job spec 提供。"""

    stale_after_hours: int
    advance_days: list[int] = Field(default_factory=list)
    expired_stop_days: int | None = None


class JobResultPayload(BaseModel):
    """`job_runs.result` 的固定形狀（所有 job 遵循 `JobResult` 契約）。"""

    processed: int = 0
    emitted: int = 0
    errors: list[str] = Field(default_factory=list)


class JobRunInfo(BaseModel):
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    result: JobResultPayload | None = None


class JobStatus(BaseModel):
    job: str
    thresholds: JobThresholds
    last_run: JobRunInfo | None = None
    stale: bool
