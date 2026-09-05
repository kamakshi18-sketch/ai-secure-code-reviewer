from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.security import get_current_active_user, require_role
from database.session import get_db
from models import User, Finding, Patch, PatchStatus, Scan, ScanStatus, Repository, UserRole
from schemas import (
    FindingResponse,
    PatchResponse,
    SecurityReportResponse,
    PullRequestResponse,
)
from agents.service import agent_service

router = APIRouter()


@router.post("/analyze-finding/{finding_id}")
async def analyze_finding(
    finding_id: UUID,
    question: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await agent_service.analyze_finding(finding_id, db, question)
    return result


@router.post("/generate-patch/{finding_id}")
async def generate_patch_for_finding(
    finding_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER, UserRole.DEVELOPER)),
    db: AsyncSession = Depends(get_db)
):
    finding = await db.get(Finding, finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    scan = await db.get(Scan, finding.scan_id)
    repo = await db.get(Repository, scan.repository_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER] and repo.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    existing = await db.execute(
        select(Patch).where(
            Patch.finding_id == finding_id,
            Patch.status.in_([PatchStatus.PENDING, PatchStatus.GENERATING, PatchStatus.GENERATED])
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Patch generation already in progress")
    
    patch = Patch(
        scan_id=finding.scan_id,
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
    
    from tasks.patch_tasks import generate_patch_task
    generate_patch_task.delay(str(patch.id))
    
    return {"message": "Patch generation started", "patch_id": str(patch.id)}


@router.post("/verify-patch/{patch_id}")
async def verify_patch(
    patch_id: UUID,
    test_results: dict,
    scan_results: dict,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER)),
    db: AsyncSession = Depends(get_db)
):
    patch = await db.get(Patch, patch_id)
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")
    
    finding = await db.get(Finding, patch.finding_id)
    scan = await db.get(Scan, patch.scan_id)
    repo = await db.get(Repository, scan.repository_id)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER] and repo.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = await agent_service.verify_patch(patch_id, db)
    return result


@router.post("/generate-report/{scan_id}")
async def generate_report(
    scan_id: UUID,
    format: str = Query("markdown", pattern="^(markdown|json|pdf|html)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    repo = await db.get(Repository, scan.repository_id)
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER] and repo.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if scan.status != ScanStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Scan must be completed")
    
    result = await agent_service.generate_report(scan_id, db, format)
    return result


@router.post("/create-pr/{scan_id}")
async def create_pull_request(
    scan_id: UUID,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str = "main",
    patch_ids: List[UUID] = [],
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SECURITY_ENGINEER, UserRole.DEVELOPER)),
    db: AsyncSession = Depends(get_db)
):
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    repo = await db.get(Repository, scan.repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SECURITY_ENGINEER] and repo.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if not current_user.github_access_token:
        raise HTTPException(status_code=400, detail="GitHub access token required")
    
    try:
        result = await agent_service.create_pull_request(
            scan_id=scan_id,
            db=db,
            patch_ids=patch_ids,
            title=title,
            body=body,
            head_branch=head_branch,
            base_branch=base_branch
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))