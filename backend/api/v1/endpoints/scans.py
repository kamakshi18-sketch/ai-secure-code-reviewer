from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.security import get_current_active_user, require_role
from database.session import get_db
from models import User, Repository, RepositoryStatus, Scan, ScanStatus, ScanType, UserRole
from schemas import (
    ScanCreate,
    ScanResponse,
    ScanListResponse,
    PaginatedResponse,
)
from security.service import scan_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def list_scans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repository_id: Optional[UUID] = Query(None),
    status: Optional[ScanStatus] = Query(None),
    scan_type: Optional[ScanType] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Scan).join(Repository).where(Repository.owner_id == current_user.id)
    
    if current_user.role in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = select(Scan)
    
    if repository_id:
        query = query.where(Scan.repository_id == repository_id)
    if status:
        query = query.where(Scan.status == status)
    if scan_type:
        query = query.where(Scan.scan_type == scan_type)
    
    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)
    
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Scan.created_at.desc())
    result = await db.execute(query)
    scans = result.scalars().all()
    
    return PaginatedResponse(
        items=[ScanResponse.model_validate(s) for s in scans],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(
    scan_data: ScanCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Repository).where(Repository.id == scan_data.repository_id)
    
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
            detail="Repository must be cloned before scanning"
        )
    
    scan = await scan_service.create_scan(
        db=db,
        repository_id=scan_data.repository_id,
        initiated_by_id=current_user.id,
        scan_type=scan_data.scan_type,
        commit_sha=scan_data.commit_sha,
        branch=scan_data.branch,
        scanners=scan_data.scanners,
    )
    
    await scan_service.start_scan(scan.id)
    
    return ScanResponse.model_validate(scan)


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Scan).join(Repository).where(Scan.id == scan_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )
    
    return ScanResponse.model_validate(scan)


@router.post("/{scan_id}/cancel", response_model=ScanResponse)
async def cancel_scan(
    scan_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Scan).join(Repository).where(Scan.id == scan_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )
    
    if scan.status not in [ScanStatus.PENDING, ScanStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel scan with status {scan.status.value}"
        )
    
    scan = await scan_service.cancel_scan(db, scan_id)
    
    return ScanResponse.model_validate(scan)


@router.post("/{scan_id}/retry", response_model=ScanResponse)
async def retry_scan(
    scan_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Scan).join(Repository).where(Scan.id == scan_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )
    
    if scan.status not in [ScanStatus.FAILED, ScanStatus.CANCELLED, ScanStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry scan with status {scan.status.value}"
        )
    
    new_scan = await scan_service.retry_scan(db, scan_id)
    
    return ScanResponse.model_validate(new_scan)


@router.get("/{scan_id}/summary")
async def get_scan_summary(
    scan_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Scan).join(Repository).where(Scan.id == scan_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )
    
    summary = await scan_service.get_scan_summary(db, scan_id)
    
    return summary