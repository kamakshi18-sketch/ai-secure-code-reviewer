from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import asyncio
import os
from datetime import datetime

from core.celery_app import celery_app
from core.logging import get_logger, log_task_event, log_scan_event
from database.session import async_session_maker
from models import Scan, ScanStatus, Finding, Severity, Repository, FindingStatus
from security.scanners import scanner_registry
from security.aggregator import finding_aggregator, finding_deduplicator, finding_correlator
from core.config import settings

logger = get_logger("scan_tasks")


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def run_security_scan_task(self, scan_id: str):
    log_task_event("run_security_scan", "started", task_id=self.request.id, scan_id=scan_id)
    
    async def _scan():
        async with async_session_maker() as db:
            scan = await db.get(Scan, scan_id)
            if not scan:
                logger.error("Scan not found", scan_id=scan_id)
                return
            
            repo = await db.get(Repository, scan.repository_id)
            if not repo or not repo.local_path:
                scan.status = ScanStatus.FAILED
                scan.error_message = "Repository not cloned"
                await db.commit()
                return
            
            scan.status = ScanStatus.RUNNING
            scan.started_at = datetime.utcnow()
            await db.commit()
            
            start_time = datetime.utcnow()
            all_findings = []
            
            try:
                scanners_to_use = scan.scanners_used or scanner_registry.get_available_scanners(repo.language)
                
                if not scanners_to_use:
                    scan.status = ScanStatus.FAILED
                    scan.error_message = "No scanners available for this language"
                    await db.commit()
                    return
                
                scan.scanners_used = scanners_to_use
                await db.commit()
                
                logger.info("Starting security scan", scan_id=scan_id, scanners=scanners_to_use, repo=repo.full_name)
                
                findings = await scanner_registry.run_scanners(
                    repo.local_path,
                    repo.language,
                    scanners_to_use
                )
                
                all_findings.extend(findings)
                
                logger.info("Raw findings collected", count=len(all_findings))
                
                aggregated = finding_aggregator.aggregate(all_findings)
                logger.info("After aggregation", count=len(aggregated))
                
                unique_findings = [a.to_finding() for a in aggregated if not a.is_duplicate]
                duplicate_findings = [a.to_finding() for a in aggregated if a.is_duplicate]
                
                for finding in duplicate_findings:
                    finding.status = "false_positive"
                    finding.metadata = {**finding.metadata, "is_duplicate": True}
                
                all_processed = unique_findings + duplicate_findings
                
                deduplicated, duplicates = finding_deduplicator.deduplicate(all_processed)
                
                for dup in duplicates:
                    dup.status = "false_positive"
                    dup.metadata = {**dup.metadata, "is_duplicate": True, "deduplication_method": "exact"}
                
                final_findings = deduplicated
                
                logger.info("After deduplication", unique=len(deduplicated), duplicates=len(duplicates))
                
                saved_findings = []
                for f in final_findings:
                    sev_val = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
                    try:
                        sev = Severity(sev_val)
                    except (ValueError, KeyError):
                        sev = Severity.MEDIUM

                    f_status = getattr(f, "status", "open")
                    status_enum = FindingStatus.FALSE_POSITIVE if f_status == "false_positive" else FindingStatus.OPEN

                    db_finding = Finding(
                        scan_id=scan.id,
                        scanner=f.scanner,
                        rule_id=f.rule_id,
                        rule_name=f.rule_name,
                        severity=sev,
                        status=status_enum,
                        cwe_id=f.cwe_id,
                        owasp_category=f.owasp_category,
                        file_path=f.file_path,
                        line_start=f.line_start,
                        line_end=f.line_end,
                        column_start=f.column_start,
                        column_end=f.column_end,
                        code_snippet=f.code_snippet,
                        message=f.message,
                        confidence=f.confidence,
                        metadata=f.metadata if isinstance(f.metadata, dict) else {},
                    )
                    db.add(db_finding)
                    saved_findings.append(db_finding)
                
                await db.flush()
                
                scan.total_findings = len(saved_findings)
                scan.critical_count = sum(1 for f in saved_findings if f.severity == Severity.CRITICAL)
                scan.high_count = sum(1 for f in saved_findings if f.severity == Severity.HIGH)
                scan.medium_count = sum(1 for f in saved_findings if f.severity == Severity.MEDIUM)
                scan.low_count = sum(1 for f in saved_findings if f.severity == Severity.LOW)
                scan.info_count = sum(1 for f in saved_findings if f.severity == Severity.INFO)
                
                scan.status = ScanStatus.COMPLETED
                scan.completed_at = datetime.utcnow()
                scan.duration_seconds = (scan.completed_at - start_time).total_seconds()
                
                await db.commit()
                
                correlated = finding_correlator.correlate(final_findings)
                if correlated:
                    logger.info("Found correlated findings", groups=len(correlated))
                
                log_scan_event(
                    scan_id=scan_id,
                    event="completed",
                    repository_id=str(repo.id),
                    findings_count=len(final_findings),
                    duration_ms=scan.duration_seconds * 1000
                )
                
                from tasks.patch_tasks import generate_patches_for_scan_task
                generate_patches_for_scan_task.delay(scan_id)
                
            except Exception as e:
                scan.status = ScanStatus.FAILED
                scan.error_message = str(e)
                scan.completed_at = datetime.utcnow()
                await db.commit()
                
                logger.error("Scan failed", scan_id=scan_id, error=str(e))
                log_scan_event(scan_id=scan_id, event="failed", error=str(e))
                raise self.retry(exc=e)
    
    asyncio.run(_scan())


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
            
            from tasks.patch_tasks import generate_patch_task
            
            for finding in findings:
                existing = await db.execute(
                    select(Patch).where(
                        Patch.finding_id == finding.id,
                        Patch.status.in_(["pending", "generating", "generated"])
                    )
                )
                if not existing.scalar_one_or_none():
                    from models import Patch, PatchStatus
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
def deduplicate_findings_task(scan_id: str):
    log_task_event("deduplicate_findings", "started", scan_id=scan_id)
    
    async def _deduplicate():
        async with async_session_maker() as db:
            result = await db.execute(
                select(Finding).where(Finding.scan_id == scan_id)
            )
            findings = result.scalars().all()
            
            deduplicated, duplicates = finding_deduplicator.deduplicate(findings)
            
            for dup in duplicates:
                dup.status = "false_positive"
                dup.metadata = {**dup.metadata, "deduplicated_from": str(deduplicated[0].id) if deduplicated else "unknown"}
            
            await db.commit()
            
            logger.info("Deduplication completed", scan_id=scan_id, unique=len(deduplicated), duplicates=len(duplicates))
            log_task_event("deduplicate_findings", "completed", scan_id=scan_id, unique=len(deduplicated), duplicates=len(duplicates))
    
    asyncio.run(_deduplicate())