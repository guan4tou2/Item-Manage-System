from __future__ import annotations

import pytest

from app.clock import today_taipei
from app.repositories import job_runs_repository as repo
from app.services import jobs_service
from app.services.jobs_service import JobResult, JobSpec, UnknownJobError


async def test_run_job_records_succeeded(db_session, monkeypatch):
    seen = {}

    async def fake_run(session, today):
        seen["today"] = today
        return JobResult(processed=2, emitted=1)

    monkeypatch.setitem(jobs_service.JOBS, "test-ok", JobSpec("test-ok", fake_run))

    row = await jobs_service.run_job(db_session, "test-ok")

    assert row.status == "succeeded"
    assert row.finished_at is not None
    assert row.result == {"processed": 2, "emitted": 1, "errors": []}
    assert seen["today"] == today_taipei()
    latest = await repo.latest(db_session, "test-ok")
    assert latest.id == row.id


async def test_run_job_exception_marks_failed(db_session, monkeypatch):
    async def boom(session, today):
        raise RuntimeError("boom")

    monkeypatch.setitem(jobs_service.JOBS, "test-boom", JobSpec("test-boom", boom))

    row = await jobs_service.run_job(db_session, "test-boom")

    assert row.status == "failed"
    assert row.finished_at is not None
    assert len(row.result["errors"]) == 1
    assert "boom" in row.result["errors"][0]


async def test_run_job_partial_errors_mark_failed(db_session, monkeypatch):
    async def partial(session, today):
        return JobResult(processed=3, emitted=1, errors=["u1: insert failed"])

    monkeypatch.setitem(
        jobs_service.JOBS, "test-partial", JobSpec("test-partial", partial)
    )

    row = await jobs_service.run_job(db_session, "test-partial")

    assert row.status == "failed"
    assert row.result == {
        "processed": 3,
        "emitted": 1,
        "errors": ["u1: insert failed"],
    }


async def test_run_job_unknown_raises_and_records_nothing(db_session):
    with pytest.raises(UnknownJobError):
        await jobs_service.run_job(db_session, "nope")

    assert await repo.latest(db_session, "nope") is None


async def test_job_runs_latest_returns_most_recent(db_session):
    await repo.create_running(db_session, "k")
    await db_session.commit()
    second = await repo.create_running(db_session, "k")
    await db_session.commit()

    latest = await repo.latest(db_session, "k")

    assert latest is not None
    assert latest.id == second.id
