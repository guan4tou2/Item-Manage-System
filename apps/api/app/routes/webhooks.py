from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.webhook import (
    WebhookCreate,
    WebhookDeliveryRead,
    WebhookRead,
    WebhookUpdate,
)
from app.services import webhooks_service as svc

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.get("", response_model=list[WebhookRead])
async def list_webhooks(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.list_webhooks(session, user.id)


@router.post("", response_model=WebhookRead, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    body: WebhookCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.create_webhook(session, user.id, body)


@router.patch("/{webhook_id}", response_model=WebhookRead)
async def update_webhook(
    webhook_id: UUID,
    body: WebhookUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.update_webhook(session, user.id, webhook_id, body)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_webhook(
    webhook_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await svc.delete_webhook(session, user.id, webhook_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryRead])
async def list_deliveries(
    webhook_id: UUID,
    limit: int = Query(default=50, ge=1, le=500),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    rows = await svc.list_deliveries(session, user.id, webhook_id, limit)
    return [WebhookDeliveryRead.model_validate(r) for r in rows]
