from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from core.security import get_current_active_user, require_role
from database.session import get_db
from models import User, Repository, RepositoryStatus, UserRole
from schemas import (
    RepositoryCreate,
    RepositoryUpdate,
    RepositoryResponse,
    RepositoryListResponse,
    PaginatedResponse,
)
from tasks.repository_tasks import clone_repository_task, detect_language_task
from github.oauth import github_app_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def list_repositories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[RepositoryStatus] = Query(None),
    language: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Repository).where(Repository.owner_id == current_user.id)
    
    if current_user.role in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = select(Repository)
    
    if status:
        query = query.where(Repository.status == status)
    if language:
        query = query.where(Repository.language == language)
    if search:
        query = query.where(
            or_(
                Repository.name.ilike(f"%{search}%"),
                Repository.full_name.ilike(f"%{search}%"),
                Repository.description.ilike(f"%{search}%"),
            )
        )
    
    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)
    
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Repository.created_at.desc())
    result = await db.execute(query)
    repositories = result.scalars().all()
    
    return PaginatedResponse(
        items=[RepositoryResponse.model_validate(r) for r in repositories],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    repo_data: RepositoryCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from github import Github
    from urllib.parse import urlparse
    
    parsed_url = urlparse(str(repo_data.github_url))
    path_parts = parsed_url.path.strip("/").split("/")
    if len(path_parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GitHub repository URL format"
        )
    
    owner, repo_name = path_parts
    full_name = f"{owner}/{repo_name}"
    
    result = await db.execute(
        select(Repository).where(
            Repository.owner_id == current_user.id,
            Repository.full_name == full_name
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository already added"
        )
    
    github_token = repo_data.github_token or current_user.github_access_token
    if not github_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub token required for private repositories"
        )
    
    g = Github(github_token)
    try:
        github_repo = g.get_repo(full_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository not found or access denied: {str(e)}"
        )
    
    repository = Repository(
        owner_id=current_user.id,
        github_id=github_repo.id,
        name=github_repo.name,
        full_name=github_repo.full_name,
        description=github_repo.description,
        url=github_repo.html_url,
        clone_url=github_repo.clone_url,
        ssh_url=github_repo.ssh_url,
        default_branch=github_repo.default_branch,
        language=github_repo.language,
        is_private=github_repo.private,
        status=RepositoryStatus.PENDING,
    )
    db.add(repository)
    await db.commit()
    await db.refresh(repository)
    
    clone_repository_task.delay(str(repository.id))
    
    return RepositoryResponse.model_validate(repository)


@router.post("/from-installation", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository_from_installation(
    github_repo_id: int,
    installation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.github_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub access token required"
        )
    
    g = Github(current_user.github_access_token)
    try:
        github_repo = g.get_repo(github_repo_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository not found: {str(e)}"
        )
    
    result = await db.execute(
        select(Repository).where(
            Repository.owner_id == current_user.id,
            Repository.github_id == github_repo.id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository already added"
        )
    
    repository = Repository(
        owner_id=current_user.id,
        github_id=github_repo.id,
        name=github_repo.name,
        full_name=github_repo.full_name,
        description=github_repo.description,
        url=github_repo.html_url,
        clone_url=github_repo.clone_url,
        ssh_url=github_repo.ssh_url,
        default_branch=github_repo.default_branch,
        language=github_repo.language,
        is_private=github_repo.private,
        status=RepositoryStatus.PENDING,
        github_installation_id=installation_id,
    )
    db.add(repository)
    await db.commit()
    await db.refresh(repository)
    
    clone_repository_task.delay(str(repository.id))
    
    return RepositoryResponse.model_validate(repository)


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Repository).where(Repository.id == repo_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    repository = result.scalar_one_or_none()
    
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    return RepositoryResponse.model_validate(repository)


@router.put("/{repo_id}", response_model=RepositoryResponse)
async def update_repository(
    repo_id: UUID,
    repo_update: RepositoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Repository).where(Repository.id == repo_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    repository = result.scalar_one_or_none()
    
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    update_data = repo_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(repository, field, value)
    
    await db.commit()
    await db.refresh(repository)
    
    return RepositoryResponse.model_validate(repository)


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repo_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Repository).where(Repository.id == repo_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    repository = result.scalar_one_or_none()
    
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    await db.delete(repository)
    await db.commit()


@router.post("/{repo_id}/clone", status_code=status.HTTP_202_ACCEPTED)
async def trigger_clone(
    repo_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Repository).where(Repository.id == repo_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    repository = result.scalar_one_or_none()
    
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    if repository.status in [RepositoryStatus.CLONING, RepositoryStatus.CLONED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository is already {repository.status.value}"
        )
    
    clone_repository_task.delay(str(repo_id))
    
    return {"message": "Clone task started", "repository_id": str(repo_id)}


@router.post("/{repo_id}/detect-language", status_code=status.HTTP_202_ACCEPTED)
async def trigger_language_detection(
    repo_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Repository).where(Repository.id == repo_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    repository = result.scalar_one_or_none()
    
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    if repository.status != RepositoryStatus.CLONED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository must be cloned first"
        )
    
    detect_language_task.delay(str(repo_id))
    
    return {"message": "Language detection task started", "repository_id": str(repo_id)}