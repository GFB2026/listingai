import re
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.login_protection import (
    check_login_allowed,
    clear_failed_logins,
    record_failed_login,
)
from app.core.security import (
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    set_auth_cookies,
    verify_password,
)
from app.core.token_blacklist import blacklist_token, is_token_blacklisted
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Generate slug from brokerage name if not provided
    slug = request.brokerage_slug or re.sub(
        r"[^a-z0-9]+", "-", request.brokerage_name.lower()
    ).strip("-")

    # Check if tenant slug already exists
    existing = await db.execute(select(Tenant).where(Tenant.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Brokerage slug already taken")

    # Check if email already exists
    existing_user = await db.execute(select(User).where(User.email == request.email))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create tenant
    tenant = Tenant(name=request.brokerage_name, slug=slug)
    db.add(tenant)
    await db.flush()

    # Create admin user
    user = User(
        tenant_id=tenant.id,
        email=request.email,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        role="admin",
    )
    db.add(user)
    await db.flush()

    # Generate tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "tenant_id": str(tenant.id), "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "tenant_id": str(tenant.id)}
    )

    response = JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=TokenResponse(access_token=access_token, refresh_token=refresh_token).model_dump(),
    )
    set_auth_cookies(response, access_token, refresh_token)
    return response


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Check brute force lockout
    await check_login_allowed(request.email)

    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        await record_failed_login(request.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    await clear_failed_logins(request.email)

    access_token = create_access_token(
        data={"sub": str(user.id), "tenant_id": str(user.tenant_id), "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "tenant_id": str(user.tenant_id)}
    )

    response = JSONResponse(
        content=TokenResponse(access_token=access_token, refresh_token=refresh_token).model_dump(),
    )
    set_auth_cookies(response, access_token, refresh_token)
    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    db: AsyncSession = Depends(get_db),
    body: RefreshRequest | None = None,
):
    # Accept refresh token from cookie OR request body
    token = request.cookies.get("refresh_token")
    if not token and body:
        token = body.refresh_token
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Check if this refresh token has been blacklisted (already rotated)
    old_jti = payload.get("jti")
    old_iat = payload.get("iat")
    if old_jti and await is_token_blacklisted(old_jti, iat=old_iat):
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Blacklist the old refresh token so it can't be replayed
    if old_jti:
        old_exp = payload.get("exp", 0)
        old_ttl = max(0, int(old_exp - time.time()))
        if old_ttl > 0:
            await blacklist_token(old_jti, old_ttl)

    access_token = create_access_token(
        data={"sub": str(user.id), "tenant_id": str(user.tenant_id), "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "tenant_id": str(user.tenant_id)}
    )

    response = JSONResponse(
        content=TokenResponse(access_token=access_token, refresh_token=refresh_token).model_dump(),
    )
    set_auth_cookies(response, access_token, refresh_token)
    return response


@router.post("/logout", response_model=MessageResponse)
async def logout(request: Request):
    # Blacklist access token
    access_token = request.cookies.get("access_token")
    if access_token:
        payload = decode_token(access_token)
        if payload and payload.get("jti"):
            exp = payload.get("exp", 0)
            ttl = max(0, int(exp - time.time()))
            if ttl > 0:
                await blacklist_token(payload["jti"], ttl)

    # Blacklist refresh token
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        payload = decode_token(refresh_token)
        if payload and payload.get("jti"):
            exp = payload.get("exp", 0)
            ttl = max(0, int(exp - time.time()))
            if ttl > 0:
                await blacklist_token(payload["jti"], ttl)

    response = JSONResponse(content={"detail": "Logged out"})
    clear_auth_cookies(response)
    return response


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        tenant_id=str(user.tenant_id),
        is_active=user.is_active,
    )
