from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryTreeNode, CategoryUpdate
from app.services import categories_service

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryTreeNode])
async def list_categories(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CategoryTreeNode]:
    return await categories_service.list_tree(session, user.id)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CategoryRead:
    cat = await categories_service.create(session, user.id, body)
    return CategoryRead.model_validate(cat)


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: int,
    body: CategoryUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CategoryRead:
    cat = await categories_service.update(session, user.id, category_id, body)
    return CategoryRead.model_validate(cat)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_category(
    category_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await categories_service.delete(session, user.id, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
