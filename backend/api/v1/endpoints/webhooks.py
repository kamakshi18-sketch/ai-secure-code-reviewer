import hmac
import hashlib
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import settings
from core.security import get_current_active_user
from database.session import get_db
from models import User, Repository, Scan, ScanType, ScanStatus, UserRole
from schemas import WebhookEvent
from tasks.scan_tasks import run_security_scan_task
from github.oauth import github_app_service

router = APIRouter()


def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not signature.startswith("sha256="):
        return False
    
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected}", signature)


@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    payload = await request.body()
    
    if settings.GITHUB_WEBHOOK_SECRET:
        if not x_hub_signature_256 or not verify_github_signature(payload, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing signature"
            )
    
    import json
    try:
        event_data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    event_type = x_github_event or "unknown"
    
    if event_type == "push":
        await handle_push_event(event_data, db)
    elif event_type == "pull_request":
        await handle_pull_request_event(event_data, db)
    elif event_type == "repository":
        await handle_repository_event(event_data, db)
    elif event_type == "installation":
        await handle_installation_event(event_data, db)
    elif event_type == "installation_repositories":
        await handle_installation_repositories_event(event_data, db)
    
    return {"status": "ok", "event": event_type}


async def handle_push_event(event_data: dict, db: AsyncSession):
    repo_data = event_data.get("repository", {})
    full_name = repo_data.get("full_name")
    
    if not full_name:
        return
    
    result = await db.execute(
        select(Repository).where(Repository.full_name == full_name)
    )
    repository = result.scalar_one_or_none()
    
    if not repository:
        return
    
    commit_sha = event_data.get("after")
    branch = event_data.get("ref", "").replace("refs/heads/", "")
    
    if commit_sha and commit_sha != "0" * 40:
        scan = Scan(
            repository_id=repository.id,
            scan_type=ScanType.INCREMENTAL,
            commit_sha=commit_sha,
            branch=branch or repository.default_branch,
            status=ScanStatus.PENDING,
        )
        db.add(scan)
        await db.commit()
        await db.refresh(scan)
        
        run_security_scan_task.delay(str(scan.id))


async def handle_pull_request_event(event_data: dict, db: AsyncSession):
    action = event_data.get("action")
    pr_data = event_data.get("pull_request", {})
    repo_data = event_data.get("repository", {})
    full_name = repo_data.get("full_name")
    
    if not full_name:
        return
    
    result = await db.execute(
        select(Repository).where(Repository.full_name == full_name)
    )
    repository = result.scalar_one_or_none()
    
    if not repository:
        return
    
    if action in ["opened", "synchronize", "reopened"]:
        commit_sha = pr_data.get("head", {}).get("sha")
        branch = pr_data.get("head", {}).get("ref")
        
        if commit_sha:
            scan = Scan(
                repository_id=repository.id,
                scan_type=ScanType.PR_CHECK,
                commit_sha=commit_sha,
                branch=branch or repository.default_branch,
                status=ScanStatus.PENDING,
            )
            db.add(scan)
            await db.commit()
            await db.refresh(scan)
            
            run_security_scan_task.delay(str(scan.id))


async def handle_repository_event(event_data: dict, db: AsyncSession):
    action = event_data.get("action")
    repo_data = event_data.get("repository", {})
    
    if action == "deleted":
        full_name = repo_data.get("full_name")
        if full_name:
            result = await db.execute(
                select(Repository).where(Repository.full_name == full_name)
            )
            repository = result.scalar_one_or_none()
            if repository:
                repository.status = "deleted"
                await db.commit()


async def handle_installation_event(event_data: dict, db: AsyncSession):
    action = event_data.get("action")
    installation = event_data.get("installation", {})
    installation_id = installation.get("id")
    
    if action == "created":
        pass
    elif action == "deleted":
        result = await db.execute(
            select(Repository).where(Repository.github_installation_id == installation_id)
        )
        repositories = result.scalars().all()
        for repo in repositories:
            repo.github_installation_id = None
        await db.commit()


async def handle_installation_repositories_event(event_data: dict, db: AsyncSession):
    action = event_data.get("action")
    installation = event_data.get("installation", {})
    installation_id = installation.get("id")
    repositories_added = event_data.get("repositories_added", [])
    repositories_removed = event_data.get("repositories_removed", [])
    
    if action == "added":
        for repo_data in repositories_added:
            result = await db.execute(
                select(Repository).where(Repository.github_id == repo_data["id"])
            )
            repo = result.scalar_one_or_none()
            if repo:
                repo.github_installation_id = installation_id
        await db.commit()
    elif action == "removed":
        for repo_data in repositories_removed:
            result = await db.execute(
                select(Repository).where(Repository.github_id == repo_data["id"])
            )
            repo = result.scalar_one_or_none()
            if repo:
                repo.github_installation_id = None
        await db.commit()


@router.post("/github/app")
async def github_app_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    return await github_webhook(request, x_github_event, x_hub_signature_256, db)