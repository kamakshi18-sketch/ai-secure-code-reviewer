from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import asyncio
from uuid import UUID

from core.celery_app import celery_app
from core.logging import get_logger, log_task_event
from database.session import async_session_maker
from models import SecurityReport, ReportFormat, Scan, Finding, Patch, Repository, PatchStatus
from reports.generator import report_service

logger = get_logger("report_tasks")


@celery_app.task(bind=True, max_retries=2)
def generate_report_task(self, report_id: str):
    log_task_event("generate_report", "started", report_id=report_id)
    
    async def _generate():
        async with async_session_maker() as db:
            report = await db.get(SecurityReport, report_id)
            if not report:
                logger.error("Report not found", report_id=report_id)
                return
            
            scan = await db.get(Scan, report.scan_id)
            repo = await db.get(Repository, scan.repository_id)
            
            findings_result = await db.execute(
                select(Finding).where(Finding.scan_id == scan.id)
            )
            findings = findings_result.scalars().all()
            
            patches_result = await db.execute(
                select(Patch).where(Patch.scan_id == scan.id)
            )
            patches = patches_result.scalars().all()
            
            severity_dist = {}
            for sev in ["critical", "high", "medium", "low", "info"]:
                severity_dist[sev] = sum(1 for f in findings if f.severity.value == sev)
            
            owasp_mapping = {}
            for f in findings:
                if f.owasp_category:
                    owasp_mapping[f.owasp_category] = owasp_mapping.get(f.owasp_category, 0) + 1
            
            cwe_mapping = {}
            for f in findings:
                if f.cwe_id:
                    cwe_mapping[f.cwe_id] = cwe_mapping.get(f.cwe_id, 0) + 1
            
            fixed_issues = sum(1 for f in findings if f.status.value == "fixed")
            remaining_issues = sum(1 for f in findings if f.status.value == "open")
            
            applied_patches = [p for p in patches if p.status == PatchStatus.APPLIED]
            patch_summary = {
                "total_generated": len(patches),
                "applied": len(applied_patches),
                "failed": sum(1 for p in patches if p.status == PatchStatus.FAILED),
                "rejected": sum(1 for p in patches if p.status == PatchStatus.REJECTED),
            }
            
            security_score = calculate_security_score(findings)
            risk_score = calculate_risk_score(findings)
            
            report.severity_distribution = severity_dist
            report.owasp_mapping = owasp_mapping
            report.cwe_mapping = cwe_mapping
            report.fixed_issues = fixed_issues
            report.remaining_issues = remaining_issues
            report.patch_summary = patch_summary
            report.security_score = security_score
            report.risk_score = risk_score
            
            report_data = {
                "scan": {
                    "id": str(scan.id),
                    "created_at": scan.created_at.isoformat() if scan.created_at else None,
                    "branch": scan.branch,
                    "commit_sha": scan.commit_sha,
                },
                "repository": {
                    "full_name": repo.full_name,
                    "language": repo.language,
                    "url": repo.url,
                },
                "findings": [
                    {
                        "id": str(f.id),
                        "scanner": f.scanner,
                        "rule_id": f.rule_id,
                        "rule_name": f.rule_name,
                        "severity": f.severity.value,
                        "file_path": f.file_path,
                        "line_start": f.line_start,
                        "message": f.message,
                        "cwe_id": f.cwe_id,
                        "owasp_category": f.owasp_category,
                        "status": f.status.value,
                        "ai_explanation": f.ai_explanation,
                        "code_snippet": f.code_snippet,
                    }
                    for f in findings
                ],
                "patches": [
                    {
                        "id": str(p.id),
                        "finding_id": str(p.finding_id),
                        "status": p.status.value,
                        "file_path": p.file_path,
                    }
                    for p in patches
                ],
                "format": report.format.value,
                "title": report.title,
            }
            
            from agents.documentation import DocumentationAgent
            from rag.engine import RAGEngine
            
            rag_engine = RAGEngine()
            await rag_engine.initialize()
            doc_agent = DocumentationAgent(rag_engine)
            
            result = await doc_agent.generate_report(report_data)
            
            report.content = result.get("content", "")
            
            if report.format != ReportFormat.MARKDOWN:
                from reports.generator import ReportGenerator
                generator = ReportGenerator(rag_engine)
                filepath = await generator.save_report(scan.id, result.get("content", ""), report.format.value)
                report.file_path = filepath
            
            await db.commit()
            
            log_task_event("generate_report", "completed", report_id=report_id)
    
    asyncio.run(_generate())


def calculate_security_score(findings: list) -> float:
    if not findings:
        return 100.0
    
    weights = {
        "critical": 20,
        "high": 10,
        "medium": 5,
        "low": 2,
        "info": 1,
    }
    
    total_penalty = sum(weights.get(f.severity.value, 0) for f in findings)
    score = max(0, 100 - total_penalty)
    return round(score, 1)


def calculate_risk_score(findings: list) -> float:
    if not findings:
        return 0.0
    
    weights = {
        "critical": 10,
        "high": 7,
        "medium": 4,
        "low": 2,
        "info": 1,
    }
    
    total_risk = sum(weights.get(f.severity.value, 0) for f in findings)
    max_possible = len(findings) * 10
    score = min(100, (total_risk / max_possible) * 100) if max_possible > 0 else 0
    return round(score, 1)