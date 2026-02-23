from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_db, require_role
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserListResponse, UserResponse, UserUpdate

router = APIRouter()


@router.get("", response_model=UserListResponse)
async def list_users(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(User).where(User.tenant_id == user.tenant_id).order_by(User.created_at)
    )
    users = result.scalars().all()
    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=len(users),
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreate,
    admin: User = Depends(require_role("admin", "broker")),
    db: AsyncSession = Depends(get_tenant_db),
):
    # Check if email already exists in this tenant
    existing = await db.execute(
        select(User).where(
            User.tenant_id == admin.tenant_id,
            User.email == request.email,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already exists in this brokerage")

    new_user = User(
        tenant_id=admin.tenant_id,
        email=request.email,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        role=request.role,
    )
    db.add(new_user)
    await db.flush()
    return new_user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    update: UserUpdate,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(User).where(User.id == UUID(user_id), User.tenant_id == admin.tenant_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if update.full_name is not None:
        target.full_name = update.full_name
    if update.role is not None:
        target.role = update.role
    if update.is_active is not None:
        target.is_active = update.is_active

    db.add(target)
    return target


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    target_id = UUID(user_id)

    # Prevent admin from deleting themselves
    if target_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    result = await db.execute(
        select(User).where(User.id == target_id, User.tenant_id == admin.tenant_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(target)
