from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from core.security import get_current_active_user, require_role
from database.session import get_db
from models import User, PullRequest, PullRequestStatus, Patch, Scan, Repository, UserRole
from schemas import (
    PullRequestResponse,
    PullRequestCreate,
    PullRequestUpdate,
    PaginatedResponse,
)
from tasks.github_tasks import create_pull_request_task

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def list_pull_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repository_id: Optional[UUID] = Query(None),
    scan_id: Optional[UUID] = Query(None),
    status: Optional[PullRequestStatus] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(PullRequest).join(Repository).where(Repository.owner_id == current_user.id)
    
    if current_user.role in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = select(PullRequest).join(Repository)
    
    if repository_id:
        query = query.where(PullRequest.repository_id == repository_id)
    if scan_id:
        query = query.where(PullRequest.scan_id == scan_id)
    if status:
        query = query.where(PullRequest.status == status)
    
    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)
    
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(PullRequest.created_at.desc())
    result = await db.execute(query)
    prs = result.scalars().all()
    
    return PaginatedResponse(
        items=[PullRequestResponse.model_validate(p) for p in prs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=PullRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_pull_request(
    pr_data: PullRequestCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER, UserRole.DEVELOPER)),
    db: AsyncSession = Depends(get_db)
):
    query = select(Repository).where(Repository.id == pr_data.repository_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    repository = result.scalar_one_or_none()
    
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    if not current_user.github_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub access token required"
        )
    
    patches = []
    if pr_data.patch_ids:
        patch_query = select(Patch).where(
            Patch.id.in_(pr_data.patch_ids),
            Patch.status == "generated"
        )
        patch_result = await db.execute(patch_query)
        patches = patch_result.scalars().all()
        
        if len(patches) != len(pr_data.patch_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some patches not found or not ready"
            )
    
    pr = PullRequest(
        repository_id=pr_data.repository_id,
        scan_id=pr_data.scan_id,
        title=pr_data.title,
        body=pr_data.body,
        head_branch=pr_data.head_branch,
        base_branch=pr_data.base_branch,
        status=PullRequestStatus.DRAFT,
        patches_included=pr_data.patch_ids,
    )
    db.add(pr)
    await db.commit()
    await db.refresh(pr)
    
    create_pull_request_task.delay(str(pr.id))
    
    return PullRequestResponse.model_validate(pr)


@router.get("/{pr_id}", response_model=PullRequestResponse)
async def get_pull_request(
    pr_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(PullRequest).join(Repository).where(PullRequest.id == pr_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    pr = result.scalar_one_or_none()
    
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull request not found"
        )
    
    return PullRequestResponse.model_validate(pr)


@router.post("/{pr_id}/update", response_model=PullRequestResponse)
async def update_pull_request(
    pr_id: UUID,
    pr_update: PullRequestUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER)),
    db: AsyncSession = Depends(get_db)
):
    query = select(PullRequest).join(Repository).where(PullRequest.id == pr_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    pr = result.scalar_one_or_none()
    
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull request not found"
        )
    
    update_data = pr_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pr, field, value)
    
    await db.commit()
    await db.refresh(pr)
    
    return PullRequestResponse.model_validate(pr)


@router.post("/{pr_id}/sync")
async def sync_pull_request(
    pr_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER)),
    db: AsyncSession = Depends(get_db)
):
    query = select(PullRequest).join(Repository).where(PullRequest.id == pr_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    pr = result.scalar_one_or_none()
    
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull request not found"
        )
    
    if not pr.github_pr_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pull request not yet created on GitHub"
        )
    
    from tasks.github_tasks import sync_pull_request_task
    sync_pull_request_task.delay(str(pr_id))
    
    return {"message": "Sync task started", "pull_request_id": str(pr_id)}