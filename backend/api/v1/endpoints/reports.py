from typing import List, Optional
from uuid import UUID
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.security import get_current_active_user, require_role
from database.session import get_db
from models import User, SecurityReport, ReportFormat, Scan, Repository, UserRole
from schemas import (
    SecurityReportResponse,
    SecurityReportCreate,
    PaginatedResponse,
)
from reports.generator import report_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    scan_id: Optional[UUID] = Query(None),
    format: Optional[ReportFormat] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await report_service.list_reports(db, scan_id, page, page_size)
    
    items = []
    for report in result["items"]:
        repo = await db.get(Repository, report.scan_id)
        items.append(SecurityReportResponse.model_validate(report))
    
    return PaginatedResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


@router.post("", response_model=SecurityReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    report_data: SecurityReportCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER, UserRole.DEVELOPER)),
    db: AsyncSession = Depends(get_db)
):
    query = select(Scan).join(Repository).where(Scan.id == report_data.scan_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER]:
        query = query.where(Repository.owner_id == current_user.id)
    
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )
    
    if scan.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scan must be completed before generating report"
        )
    
    result = await report_service.create_report(
        db=db,
        scan_id=report_data.scan_id,
        format=report_data.format.value,
        title=report_data.title
    )
    
    return {"report_id": result["report_id"], "status": result["status"]}


@router.get("/{report_id}", response_model=SecurityReportResponse)
async def get_report(
    report_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    report = await report_service.get_report(db, report_id)
    
    scan = await db.get(Scan, report.scan_id)
    repo = await db.get(Repository, scan.repository_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER] and repo.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this report"
        )
    
    return SecurityReportResponse.model_validate(report)


@router.get("/{report_id}/download")
async def download_report(
    report_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    report = await report_service.get_report(db, report_id)
    
    scan = await db.get(Scan, report.scan_id)
    repo = await db.get(Repository, scan.repository_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER] and repo.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to download this report"
        )
    
    content, media_type, filename = await report_service.download_report(db, report_id)
    
    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER)),
    db: AsyncSession = Depends(get_db)
):
    report = await report_service.get_report(db, report_id)
    
    scan = await db.get(Scan, report.scan_id)
    repo = await db.get(Repository, scan.repository_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER] and repo.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this report"
        )
    
    await db.delete(report)
    await db.commit()