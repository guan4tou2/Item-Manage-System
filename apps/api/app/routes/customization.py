from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.customization import (
    CustomFieldCreate,
    CustomFieldRead,
    ItemCustomValueRead,
    ItemCustomValueSet,
    ItemTemplateCreate,
    ItemTemplateRead,
    ItemTypeCreate,
    ItemTypeRead,
)
from app.services import customization_service as svc

router = APIRouter(prefix="/api", tags=["customization"])


# --- item types ---
@router.get("/item-types", response_model=list[ItemTypeRead])
async def list_item_types(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.list_item_types(session, user.id)


@router.post("/item-types", response_model=ItemTypeRead, status_code=status.HTTP_201_CREATED)
async def create_item_type(
    body: ItemTypeCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.create_item_type(session, user.id, body)


@router.delete("/item-types/{type_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_item_type(
    type_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await svc.delete_item_type(session, user.id, type_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- custom fields ---
@router.get("/custom-fields", response_model=list[CustomFieldRead])
async def list_custom_fields(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.list_custom_fields(session, user.id)


@router.post("/custom-fields", response_model=CustomFieldRead, status_code=status.HTTP_201_CREATED)
async def create_custom_field(
    body: CustomFieldCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.create_custom_field(session, user.id, body)


@router.delete("/custom-fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_custom_field(
    field_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await svc.delete_custom_field(session, user.id, field_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- custom values on items ---
@router.get("/items/{item_id}/custom-values", response_model=list[ItemCustomValueRead])
async def get_item_custom_values(
    item_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.get_item_custom_values(session, user.id, item_id)


@router.post("/items/{item_id}/custom-values", response_model=ItemCustomValueRead)
async def set_item_custom_value(
    item_id: UUID,
    body: ItemCustomValueSet,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.set_item_custom_value(session, user.id, item_id, body)


@router.delete(
    "/items/{item_id}/custom-values/{field_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_item_custom_value(
    item_id: UUID,
    field_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await svc.delete_item_custom_value(session, user.id, item_id, field_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- templates ---
@router.get("/item-templates", response_model=list[ItemTemplateRead])
async def list_templates(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.list_templates(session, user.id)


@router.post("/item-templates", response_model=ItemTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
    body: ItemTemplateCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.create_template(session, user.id, body)


@router.delete("/item-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_template(
    template_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await svc.delete_template(session, user.id, template_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
