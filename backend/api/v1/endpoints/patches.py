from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from core.security import get_current_active_user, require_role
from database.session import get_db
from models import User, Patch, PatchStatus, Finding, Scan, Repository, UserRole
from schemas import (
    PatchResponse,
    PatchDetailResponse,
    PatchUpdate,
    PaginatedResponse,
)
from tasks.patch_tasks import generate_patch_task, apply_patch_task
from tasks.verification_tasks import verify_patch_task
from tasks.retry_tasks import retry_patch_with_analysis_task, analyze_patch_failure_task, generate_alternative_patch_task

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def list_patches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    scan_id: Optional[UUID] = Query(None),
    finding_id: Optional[UUID] = Query(None),
    status: Optional[PatchStatus] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Patch).join(Scan).join(Repository).where(Repository.owner_id == current_user.id)
    
    if current_user.role in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = select(Patch).join(Scan)
    
    if scan_id:
        query = query.where(Patch.scan_id == scan_id)
    if finding_id:
        query = query.where(Patch.finding_id == finding_id)
    if status:
        query = query.where(Patch.status == status)
    
    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)
    
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Patch.created_at.desc())
    result = await db.execute(query)
    patches = result.scalars().all()
    
    return PaginatedResponse(
        items=[PatchResponse.model_validate(p) for p in patches],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=PatchResponse, status_code=status.HTTP_201_CREATED)
async def create_patch(
    scan_id: UUID,
    finding_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER, UserRole.DEVELOPER)),
    db: AsyncSession = Depends(get_db)
):
    query = select(Finding).join(Scan).join(Repository).where(
        Finding.id == finding_id,
        Finding.scan_id == scan_id
    )
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    finding = result.scalar_one_or_none()
    
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found"
        )
    
    existing_patch = await db.execute(
        select(Patch).where(
            Patch.finding_id == finding_id,
            Patch.status.in_([PatchStatus.PENDING, PatchStatus.GENERATING, PatchStatus.GENERATED])
        )
    )
    if existing_patch.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patch generation already in progress for this finding"
        )
    
    patch = Patch(
        scan_id=scan_id,
        finding_id=finding_id,
        status=PatchStatus.PENDING,
        diff="",
        file_path=finding.file_path,
        language="",
        llm_provider="",
        llm_model="",
    )
    db.add(patch)
    await db.commit()
    await db.refresh(patch)
    
    generate_patch_task.delay(str(patch.id))
    
    return PatchResponse.model_validate(patch)


@router.get("/{patch_id}", response_model=PatchDetailResponse)
async def get_patch(
    patch_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Patch).options(
        selectinload(Patch.patch_attempts)
    ).join(Scan).join(Repository).where(Patch.id == patch_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    patch = result.scalar_one_or_none()
    
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patch not found"
        )
    
    return PatchDetailResponse.model_validate(patch)


@router.post("/{patch_id}/apply", status_code=status.HTTP_202_ACCEPTED)
async def apply_patch(
    patch_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER)),
    db: AsyncSession = Depends(get_db)
):
    query = select(Patch).join(Scan).join(Repository).where(Patch.id == patch_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    patch = result.scalar_one_or_none()
    
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patch not found"
        )
    
    if patch.status != PatchStatus.GENERATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patch must be in GENERATED status, current: {patch.status.value}"
        )
    
    apply_patch_task.delay(str(patch_id))
    
    return {"message": "Patch application started", "patch_id": str(patch_id)}


@router.post("/{patch_id}/verify", status_code=status.HTTP_202_ACCEPTED)
async def verify_patch(
    patch_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER)),
    db: AsyncSession = Depends(get_db)
):
    query = select(Patch).join(Scan).join(Repository).where(Patch.id == patch_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    patch = result.scalar_one_or_none()
    
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patch not found"
        )
    
    if patch.status != PatchStatus.APPLIED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patch must be applied first, current status: {patch.status.value}"
        )
    
    verify_patch_task.delay(str(patch_id))
    
    return {"message": "Patch verification started", "patch_id": str(patch_id)}


@router.post("/{patch_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_patch(
    patch_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER)),
    db: AsyncSession = Depends(get_db)
):
    query = select(Patch).join(Scan).join(Repository).where(Patch.id == patch_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    patch = result.scalar_one_or_none()
    
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patch not found"
        )
    
    if patch.retry_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum retry count reached"
        )
    
    patch.status = PatchStatus.PENDING
    patch.retry_count += 1
    await db.commit()
    await db.refresh(patch)
    
    from tasks.patch_tasks import generate_patch_task
    generate_patch_task.delay(str(patch_id))
    
    return {"message": "Patch regeneration started", "patch_id": str(patch_id)}


@router.post("/{patch_id}/retry-with-analysis", status_code=status.HTTP_202_ACCEPTED)
async def retry_patch_with_analysis(
    patch_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER)),
    db: AsyncSession = Depends(get_db)
):
    query = select(Patch).join(Scan).join(Repository).where(Patch.id == patch_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    patch = result.scalar_one_or_none()
    
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patch not found"
        )
    
    if patch.retry_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum retry count reached"
        )
    
    retry_patch_with_analysis_task.delay(str(patch_id))
    
    return {"message": "Retry with AI analysis started", "patch_id": str(patch_id)}


@router.post("/{patch_id}/analyze-failure", status_code=status.HTTP_202_ACCEPTED)
async def analyze_failure(
    patch_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER)),
    db: AsyncSession = Depends(get_db)
):
    query = select(Patch).join(Scan).join(Repository).where(Patch.id == patch_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    patch = result.scalar_one_or_none()
    
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patch not found"
        )
    
    analyze_patch_failure_task.delay(str(patch_id))
    
    return {"message": "Failure analysis started", "patch_id": str(patch_id)}


@router.post("/{patch_id}/alternative", status_code=status.HTTP_202_ACCEPTED)
async def generate_alternative_patch(
    patch_id: UUID,
    strategy: str = Query("minimal", pattern="^(minimal|defensive|refactor|library)$"),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER)),
    db: AsyncSession = Depends(get_db)
):
    query = select(Patch).join(Scan).join(Repository).where(Patch.id == patch_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    patch = result.scalar_one_or_none()
    
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patch not found"
        )
    
    generate_alternative_patch_task.delay(str(patch_id), strategy)
    
    return {"message": f"Alternative patch generation started with {strategy} strategy", "patch_id": str(patch_id)}


@router.put("/{patch_id}", response_model=PatchResponse)
async def update_patch(
    patch_id: UUID,
    patch_update: PatchUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER)),
    db: AsyncSession = Depends(get_db)
):
    query = select(Patch).join(Scan).join(Repository).where(Patch.id == patch_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    patch = result.scalar_one_or_none()
    
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patch not found"
        )
    
    update_data = patch_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patch, field, value)
    
    await db.commit()
    await db.refresh(patch)
    
    return PatchResponse.model_validate(patch)