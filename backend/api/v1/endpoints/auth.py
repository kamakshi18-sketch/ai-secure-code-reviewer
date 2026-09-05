from datetime import datetime, timedelta
from typing import Optional, List
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import HttpUrl

from core.config import settings
from core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    get_current_active_user,
)
from database.session import get_db
from models import User, UserRole
from schemas import (
    UserCreate,
    UserResponse,
    UserWithToken,
    LoginRequest,
    RefreshTokenRequest,
    Token,
    TokenPayload,
    GitHubAuthUrlResponse,
    GitHubCallbackRequest,
)
from github.oauth import github_oauth_service, github_token_manager

router = APIRouter()


@router.post("/register", response_model=UserWithToken, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=user_data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    
    return UserWithToken(
        **UserResponse.model_validate(user).model_dump(),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=UserWithToken)
async def login(
    form_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    user.last_login = datetime.utcnow()
    await db.commit()
    
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    
    return UserWithToken(
        **UserResponse.model_validate(user).model_dump(),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    from uuid import UUID
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    for field, value in user_update.items():
        if field in ["email", "full_name"] and value is not None:
            setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse.model_validate(current_user)


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters"
        )
    
    current_user.hashed_password = get_password_hash(new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"}


# GitHub OAuth endpoints
@router.get("/github/url", response_model=GitHubAuthUrlResponse)
async def get_github_auth_url(
    state: Optional[str] = Query(None, description="State parameter for CSRF protection")
):
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth not configured"
        )
    
    auth_url = github_oauth_service.get_authorization_url(state)
    return GitHubAuthUrlResponse(auth_url=auth_url)


@router.get("/github/callback")
async def github_callback(
    code: str = Query(..., description="Authorization code from GitHub"),
    state: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth not configured"
        )
    
    token_data = await github_oauth_service.exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange code for token"
        )
    
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 28800)
    
    user_info = await github_oauth_service.get_user_info(access_token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user info from GitHub"
        )
    
    emails = await github_oauth_service.get_user_emails(access_token)
    primary_email = next((e["email"] for e in emails if e.get("primary")), user_info.get("email"))
    
    result = await db.execute(select(User).where(User.github_id == user_info["id"]))
    user = result.scalar_one_or_none()
    
    if not user:
        result = await db.execute(select(User).where(User.email == primary_email))
        user = result.scalar_one_or_none()
        
        if user:
            user.github_id = user_info["id"]
            user.github_login = user_info.get("login")
        else:
            user = User(
                email=primary_email,
                full_name=user_info.get("name") or user_info.get("login"),
                hashed_password=f"!oauth_{secrets.token_urlsafe(32)}",  # Unusable password for OAuth users
                github_id=user_info["id"],
                github_login=user_info.get("login"),
                role=UserRole.DEVELOPER,
            )
            db.add(user)
    
    user.github_access_token = access_token
    user.github_refresh_token = refresh_token
    user.github_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    user.last_login = datetime.utcnow()
    
    await db.commit()
    await db.refresh(user)
    
    jwt_access_token = create_access_token(subject=user.id)
    jwt_refresh_token = create_refresh_token(subject=user.id)
    
    frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
    redirect_url = f"{frontend_url}/auth/callback?access_token={jwt_access_token}&refresh_token={jwt_refresh_token}"
    
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=redirect_url)


@router.get("/github/installations", response_model=List[GitHubInstallationResponse])
async def get_github_installations(
    current_user: User = Depends(get_current_active_user)
):
    from github.oauth import github_app_service
    
    if not settings.GITHUB_APP_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub App not configured"
        )
    
    installations = github_app_service.get_installations()
    return installations


@router.get("/github/installations/{installation_id}/repositories", response_model=List[GitHubRepositoryResponse])
async def get_installation_repositories(
    installation_id: int,
    current_user: User = Depends(get_current_active_user)
):
    from github.oauth import github_app_service
    
    repos = github_app_service.get_repositories_for_installation(installation_id)
    return repos