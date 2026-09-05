from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from core.security import get_current_active_user, require_role
from database.session import get_db
from models import User, Finding, Scan, Severity, FindingStatus, Repository, UserRole
from schemas import (
    FindingResponse,
    FindingUpdate,
    FindingListResponse,
    PaginatedResponse,
)
from security.service import finding_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def list_findings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    scan_id: Optional[UUID] = Query(None),
    repository_id: Optional[UUID] = Query(None),
    severity: Optional[Severity] = Query(None),
    status: Optional[FindingStatus] = Query(None),
    scanner: Optional[str] = Query(None),
    cwe_id: Optional[str] = Query(None),
    file_path: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Finding).join(Scan).join(Repository).where(Repository.owner_id == current_user.id)
    
    if current_user.role in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = select(Finding).join(Scan)
    
    if scan_id:
        query = query.where(Finding.scan_id == scan_id)
    if repository_id:
        query = query.where(Scan.repository_id == repository_id)
    if severity:
        query = query.where(Finding.severity == severity)
    if status:
        query = query.where(Finding.status == status)
    if scanner:
        query = query.where(Finding.scanner == scanner)
    if cwe_id:
        query = query.where(Finding.cwe_id == cwe_id)
    if file_path:
        query = query.where(Finding.file_path.ilike(f"%{file_path}%"))
    if search:
        query = query.where(
            or_(
                Finding.rule_name.ilike(f"%{search}%"),
                Finding.message.ilike(f"%{search}%"),
                Finding.file_path.ilike(f"%{search}%"),
            )
        )
    
    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)
    
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(
        Finding.severity.desc(),
        Finding.created_at.desc()
    )
    result = await db.execute(query)
    findings = result.scalars().all()
    
    return PaginatedResponse(
        items=[FindingResponse.model_validate(f) for f in findings],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{finding_id}", response_model=FindingResponse)
async def get_finding(
    finding_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Finding).join(Scan).join(Repository).where(Finding.id == finding_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    finding = result.scalar_one_or_none()
    
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found"
        )
    
    return FindingResponse.model_validate(finding)


@router.put("/{finding_id}", response_model=FindingResponse)
async def update_finding(
    finding_id: UUID,
    finding_update: FindingUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER, UserRole.DEVELOPER)),
    db: AsyncSession = Depends(get_db)
):
    query = select(Finding).join(Scan).join(Repository).where(Finding.id == finding_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    finding = result.scalar_one_or_none()
    
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found"
        )
    
    finding = await finding_service.update_finding_status(db, finding_id, finding_update.status)
    
    return FindingResponse.model_validate(finding)


@router.post("/bulk-update")
async def bulk_update_findings(
    finding_ids: List[UUID],
    status: FindingStatus,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER)),
    db: AsyncSession = Depends(get_db)
):
    updated = await finding_service.bulk_update_status(db, finding_ids, status)
    
    return {"updated": updated}


@router.post("/{finding_id}/explain")
async def explain_finding(
    finding_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from tasks.patch_tasks import explain_finding_task
    
    query = select(Finding).join(Scan).join(Repository).where(Finding.id == finding_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    finding = result.scalar_one_or_none()
    
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found"
        )
    
    explain_finding_task.delay(str(finding_id))
    
    return {"message": "AI explanation task started", "finding_id": str(finding_id)}


@router.get("/stats/summary")
async def get_findings_summary(
    repository_id: Optional[UUID] = Query(None),
    scan_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    stats = await finding_service.get_finding_stats(db, repository_id, scan_id)
    
    return stats