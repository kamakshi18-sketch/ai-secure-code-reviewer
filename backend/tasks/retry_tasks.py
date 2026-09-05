from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import asyncio
import json
from datetime import datetime

from core.celery_app import celery_app
from core.logging import get_logger, log_task_event
from database.session import async_session_maker
from models import Patch, PatchStatus, Finding, FindingStatus, Scan, Repository, PatchAttempt
from core.config import settings
from agents.service import agent_service

logger = get_logger("retry_tasks")


@celery_app.task(bind=True, max_retries=1)
def retry_patch_with_analysis_task(self, patch_id: str):
    log_task_event("retry_patch_with_analysis", "started", patch_id=patch_id)
    
    async def _retry():
        async with async_session_maker() as db:
            patch = await db.get(Patch, patch_id)
            if not patch:
                logger.error("Patch not found", patch_id=patch_id)
                return
            
            finding = await db.get(Finding, patch.finding_id)
            scan = await db.get(Scan, patch.scan_id)
            repo = await db.get(Repository, scan.repository_id)
            
            if patch.retry_count >= settings.MAX_PATCH_RETRIES:
                logger.warning("Max retries reached, skipping AI analysis", patch_id=patch_id)
                return
            
            try:
                test_results = {}
                scan_results = {}
                
                latest_attempt = await db.execute(
                    select(PatchAttempt).where(
                        PatchAttempt.patch_id == patch_id
                    ).order_by(PatchAttempt.attempt_number.desc())
                )
                latest_attempt = latest_attempt.scalar_one_or_none()
                
                if latest_attempt and latest_attempt.error_message:
                    test_results = {
                        "commands": [{"command": "unknown", "stderr": latest_attempt.error_message}],
                        "passed": False,
                    }
                
                if latest_attempt and latest_attempt.scan_passed is False:
                    scan_results = {
                        "scan_passed": False,
                        "new_findings": [],
                        "findings_before": latest_attempt.findings_before,
                        "findings_after": latest_attempt.findings_after,
                    }
                
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
                
                patch_dict = {
                    "id": str(patch.id),
                    "diff": patch.diff,
                    "file_path": patch.file_path,
                    "status": patch.status.value,
                }
                
                analysis = await agent_service.verify_patch(patch_id, db)
                
                if analysis.get("suggested_fix"):
                    suggested_diff = analysis["suggested_fix"]
                    if suggested_diff and suggested_diff != patch.diff:
                        patch.diff = suggested_diff
                        patch.status = PatchStatus.PENDING
                        patch.retry_count += 1
                        await db.commit()
                        
                        from tasks.patch_tasks import generate_patch_task
                        generate_patch_task.delay(patch_id)
                        
                        logger.info("Applied AI-suggested fix for retry", patch_id=patch_id)
                        return
                
                if analysis.get("analysis"):
                    patch.status = PatchStatus.PENDING
                    patch.retry_count += 1
                    await db.commit()
                    
                    from tasks.patch_tasks import generate_patch_task
                    generate_patch_task.delay(patch_id)
                    
                    logger.info("Retrying patch generation with AI analysis", patch_id=patch_id)
                
            except Exception as e:
                logger.error("Retry with analysis failed", patch_id=patch_id, error=str(e))
                raise self.retry(exc=e)
    
    asyncio.run(_retry())


@celery_app.task
def analyze_patch_failure_task(patch_id: str):
    log_task_event("analyze_patch_failure", "started", patch_id=patch_id)
    
    async def _analyze():
        async with async_session_maker() as db:
            patch = await db.get(Patch, patch_id)
            if not patch:
                return
            
            finding = await db.get(Finding, patch.finding_id)
            scan = await db.get(Scan, patch.scan_id)
            repo = await db.get(Repository, scan.repository_id)
            
            test_results = {
                "commands": [],
                "passed": False,
            }
            
            scan_results = {
                "scan_passed": False,
                "new_findings": [],
            }
            
            latest_attempt = await db.execute(
                select(PatchAttempt).where(
                    PatchAttempt.patch_id == patch_id
                ).order_by(PatchAttempt.attempt_number.desc())
            )
            latest_attempt = latest_attempt.scalar_one_or_none()
            
            if latest_attempt:
                test_results = {
                    "commands": [{"command": "unknown", "stderr": latest_attempt.error_message or "Unknown error"}],
                    "passed": latest_attempt.test_passed or False,
                }
                scan_results = {
                    "scan_passed": latest_attempt.scan_passed or False,
                    "findings_before": latest_attempt.findings_before,
                    "findings_after": latest_attempt.findings_after,
                }
            
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
            
            patch_dict = {
                "id": str(patch.id),
                "diff": patch.diff,
                "file_path": patch.file_path,
                "status": patch.status.value,
            }
            
            analysis = await agent_service.verify_patch(patch_id, db)
            
            patch.metadata = {
                **(patch.metadata or {}),
                "failure_analysis": {
                    "analysis": analysis.get("analysis"),
                    "recommendations": analysis.get("recommendations", []),
                    "suggested_fix": analysis.get("suggested_fix"),
                    "confidence": analysis.get("confidence", 0.8),
                    "analyzed_at": datetime.utcnow().isoformat(),
                }
            }
            
            await db.commit()
            
            logger.info("Patch failure analysis completed", patch_id=patch_id)
            log_task_event("analyze_patch_failure", "completed", patch_id=patch_id)
    
    asyncio.run(_analyze())


@celery_app.task
def generate_alternative_patch_task(patch_id: str, strategy: str = "minimal"):
    log_task_event("generate_alternative_patch", "started", patch_id=patch_id, strategy=strategy)
    
    async def _generate():
        async with async_session_maker() as db:
            patch = await db.get(Patch, patch_id)
            if not patch:
                return
            
            finding = await db.get(Finding, patch.finding_id)
            scan = await db.get(Scan, patch.scan_id)
            repo = await db.get(Repository, scan.repository_id)
            
            file_path = os.path.join(repo.local_path, finding.file_path)
            if not os.path.exists(file_path):
                return
            
            with open(file_path, 'r') as f:
                source_code = f.read()
            
            strategies = {
                "minimal": "Generate the absolute minimal patch to fix only the vulnerability",
                "defensive": "Add defensive checks and validation around the vulnerable code",
                "refactor": "Refactor the vulnerable function to use a safer pattern",
                "library": "Replace vulnerable code with a secure library function",
            }
            
            strategy_prompt = strategies.get(strategy, strategies["minimal"])
            
            from agents.patch_generator import PatchGeneratorAgent
            from rag.engine import rag_engine
            
            agent = PatchGeneratorAgent(rag_engine)
            
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
            
            rag_results = await rag_engine.query(
                f"{finding_dict['rule_name']} {strategy} fix {repo.language} alternative approach",
                top_k=3
            )
            
            context = f"""
Vulnerability to Fix (using {strategy} strategy):
- Rule: {finding_dict['rule_name']} ({finding_dict['rule_id']})
- Severity: {finding_dict['severity']}
- File: {finding_dict['file_path']}
- Line: {finding_dict['line_start']}
- Message: {finding_dict['message']}

Source Code Context:
```{repo.language}
{source_code[:3000]}
```

Strategy: {strategy_prompt}

Alternative Approaches:
{chr(10).join([r['content'][:300] for r in rag_results])}
"""
            
            from langchain.schema import HumanMessage, SystemMessage
            
            messages = [
                SystemMessage(content=agent.system_prompt),
                SystemMessage(content=context),
                HumanMessage(content=f"Generate a minimal unified diff patch using the {strategy} strategy.")
            ]
            
            response = await agent._call_llm(messages, temperature=0.0)
            
            diff = agent._extract_diff(response)
            
            if diff:
                patch.diff = diff
                patch.status = PatchStatus.PENDING
                patch.retry_count += 1
                patch.metadata = {
                    **(patch.metadata or {}),
                    "alternative_strategy": strategy,
                    "generated_at": datetime.utcnow().isoformat(),
                }
                await db.commit()
                
                from tasks.patch_tasks import apply_patch_task
                apply_patch_task.delay(str(patch.id))
                
                logger.info("Alternative patch generated", patch_id=patch_id, strategy=strategy)
    
    asyncio.run(_generate())