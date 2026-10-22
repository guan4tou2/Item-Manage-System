"""AI 每日配額（Phase 32）：per-user、以 Asia/Taipei 換日。

- 計次於**嘗試**：呼叫 LLM 前先扣；上游失敗亦計（保護成本上限）
- `AI_DAILY_QUOTA <= 0` → 不設限（不寫任何列）
- 隔離性：他人耗盡不影響自己
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import today_taipei
from app.config import get_settings
from app.models.ai_usage import AiUsage
from app.services.ai_mode import is_stub


async def consume(
    session: AsyncSession, user_id: UUID, *, today: date | None = None
) -> bool:
    """記一次嘗試並回傳是否仍在配額內；`today` 供測試注入。"""
    if is_stub():
        # Phase 35 D6：stub 無上游成本，不寫入 ai_usage（e2e 連跑不受每日額度限制）
        return True
    quota = get_settings().ai_daily_quota
    if quota <= 0:
        return True
    day = today if today is not None else today_taipei()
    row = (
        await session.execute(
            select(AiUsage).where(AiUsage.user_id == user_id, AiUsage.day == day)
        )
    ).scalar_one_or_none()
    if row is None:
        session.add(AiUsage(user_id=user_id, day=day, calls=1))
        # commit：即使後續 LLM 呼叫失敗、請求以錯誤結束，嘗試仍計次
        await session.commit()
        return True
    row.calls += 1
    await session.commit()
    return row.calls <= quota
