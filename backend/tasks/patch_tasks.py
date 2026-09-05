from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import asyncio
import os
import tempfile
from datetime import datetime
from pathlib import Path

from core.celery_app import celery_app
from core.logging import get_logger, log_task_event, log_patch_event
from database.session import async_session_maker
from models import Patch, PatchStatus, Finding, Scan, Repository, PatchAttempt
from core.config import settings
from agents.service import agent_service

logger = get_logger("patch_tasks")


def resolve_safe_path(repo_root: str, relative_path: str) -> str:
    clean_rel = relative_path.lstrip("/\\")
    real_root = os.path.realpath(repo_root)
    resolved = os.path.realpath(os.path.join(real_root, clean_rel))
    if not resolved.startswith(real_root + os.sep) and resolved != real_root:
        raise ValueError(f"Path traversal detected: {relative_path}")
    return resolved


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def generate_patch_task(self, patch_id: str):
    log_task_event("generate_patch", "started", task_id=self.request.id, patch_id=patch_id)
    
    async def _generate():
        async with async_session_maker() as db:
            patch = await db.get(Patch, patch_id)
            if not patch:
                logger.error("Patch not found", patch_id=patch_id)
                return
            
            finding = await db.get(Finding, patch.finding_id)
            if not finding:
                logger.error("Finding not found", finding_id=patch.finding_id)
                return
            
            scan = await db.get(Scan, patch.scan_id)
            repo = await db.get(Repository, scan.repository_id)
            
            patch.status = PatchStatus.GENERATING
            await db.commit()
            
            try:
                file_path = resolve_safe_path(repo.local_path, finding.file_path)
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                with open(file_path, 'r') as f:
                    source_code = f.read()
                
                finding_dict = {
                    "id": str(finding.id),
                    "scanner": finding.scanner,
                    "rule_id": finding.rule_id,
                    "rule_name": finding.rule_name,
                    "severity": finding.severity.value,
                    "file_path": finding.file_path,
                    "line_start": finding.line_start,
                    "message": finding.message,
                    "cwe_id": finding.cwe_id,
                    "owasp_category": finding.owasp_category,
                }
                
                start_time = datetime.utcnow()
                result = await agent_service.generate_patch_for_finding(
                    finding_id=finding.id,
                    db=db,
                    source_code=source_code
                )
                generation_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                patch.diff = result["diff"]
                patch.file_path = finding.file_path
                patch.language = repo.language or "python"
                patch.llm_provider = result["provider"]
                patch.llm_model = result["model"]
                patch.prompt_tokens = result.get("prompt_tokens")
                patch.completion_tokens = result.get("completion_tokens")
                patch.generation_time_ms = int(generation_time)
                patch.status = PatchStatus.GENERATED
                
                await db.commit()
                
                log_patch_event(patch_id=patch_id, event="generated", finding_id=str(finding.id), success=True)
                
            except Exception as e:
                patch.status = PatchStatus.FAILED
                patch.error_message = str(e)
                await db.commit()
                
                logger.error("Patch generation failed", patch_id=patch_id, error=str(e))
                log_patch_event(patch_id=patch_id, event="failed", finding_id=str(finding.id), success=False, error=str(e))
                raise self.retry(exc=e)
    
    asyncio.run(_generate())


@celery_app.task(bind=True, max_retries=1)
def apply_patch_task(self, patch_id: str):
    log_task_event("apply_patch", "started", task_id=self.request.id, patch_id=patch_id)
    
    async def _apply():
        async with async_session_maker() as db:
            patch = await db.get(Patch, patch_id)
            if not patch:
                logger.error("Patch not found", patch_id=patch_id)
                return
            
            finding = await db.get(Finding, patch.finding_id)
            scan = await db.get(Scan, patch.scan_id)
            repo = await db.get(Repository, scan.repository_id)
            
            patch.status = PatchStatus.APPLYING
            await db.commit()
            
            try:
                file_path = os.path.join(repo.local_path, patch.file_path)
                
                attempt = PatchAttempt(
                    patch_id=patch.id,
                    attempt_number=patch.retry_count + 1,
                    diff=patch.diff,
                )
                db.add(attempt)
                await db.flush()
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
                    f.write(patch.diff)
                    patch_file = f.name
                
                try:
                    import subprocess
                    result = subprocess.run(
                        ["git", "apply", "--check", patch_file],
                        cwd=repo.local_path,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode != 0:
                        raise Exception(f"Patch check failed: {result.stderr}")
                    
                    result = subprocess.run(
                        ["git", "apply", patch_file],
                        cwd=repo.local_path,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode != 0:
                        raise Exception(f"Patch apply failed: {result.stderr}")
                    
                    patch.status = PatchStatus.APPLIED
                    attempt.test_passed = None
                    attempt.scan_passed = None
                    await db.commit()
                    
                    log_patch_event(patch_id=patch_id, event="applied", finding_id=str(finding.id), success=True)
                    
                    from tasks.verification_tasks import verify_patch_task
                    verify_patch_task.delay(patch_id)
                    
                finally:
                    os.unlink(patch_file)
                    
            except Exception as e:
                patch.status = PatchStatus.FAILED
                patch.error_message = str(e)
                attempt.test_passed = False
                attempt.error_message = str(e)
                await db.commit()
                
                logger.error("Patch apply failed", patch_id=patch_id, error=str(e))
                log_patch_event(patch_id=patch_id, event="apply_failed", finding_id=str(finding.id), success=False, error=str(e))
                raise self.retry(exc=e)
    
    asyncio.run(_apply())


@celery_app.task
def generate_patches_for_scan_task(scan_id: str):
    log_task_event("generate_patches_for_scan", "started", scan_id=scan_id)
    
    async def _generate():
        async with async_session_maker() as db:
            scan = await db.get(Scan, scan_id)
            if not scan:
                return
            
            result = await db.execute(
                select(Finding).where(
                    Finding.scan_id == scan_id,
                    Finding.status == "open"
                )
            )
            findings = result.scalars().all()
            
            for finding in findings:
                existing = await db.execute(
                    select(Patch).where(
                        Patch.finding_id == finding.id,
                        Patch.status.in_(["pending", "generating", "generated"])
                    )
                )
                if not existing.scalar_one_or_none():
                    patch = Patch(
                        scan_id=scan_id,
                        finding_id=finding.id,
                        status=PatchStatus.PENDING,
                        diff="",
                        file_path=finding.file_path,
                        language="",
                        llm_provider="",
                        llm_model="",
                    )
                    db.add(patch)
                    await db.flush()
                    generate_patch_task.delay(str(patch.id))
            
            await db.commit()
    
    asyncio.run(_generate())


@celery_app.task
def explain_finding_task(finding_id: str):
    log_task_event("explain_finding", "started", finding_id=finding_id)
    
    async def _explain():
        async with async_session_maker() as db:
            finding = await db.get(Finding, finding_id)
            if not finding:
                return
            
            scan = await db.get(Scan, finding.scan_id)
            repo = await db.get(Repository, scan.repository_id)
            try:
                file_path = resolve_safe_path(repo.local_path, finding.file_path)
            except ValueError:
                file_path = ""
            source_code = ""
            if file_path and os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    source_code = f.read()
            
            result = await agent_service.analyze_finding(finding_id, db)
            
            finding.ai_explanation = result.get("explanation")
            finding.ai_root_cause = result.get("root_cause")
            finding.ai_recommended_fix = result.get("recommended_fix")
            finding.ai_confidence = result.get("confidence")
            
            await db.commit()
            
            log_task_event("explain_finding", "completed", finding_id=finding_id)
    
    asyncio.run(_explain())