from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import subprocess
import os
from datetime import datetime

from core.config import settings
from core.logging import get_logger
from database.session import get_db
from models import Patch, PatchStatus, Finding, FindingStatus, Scan, ScanStatus, Repository, TestResult, TestStatus
from tasks.verification_tasks import run_tests, run_security_re_scan
from tasks.retry_tasks import retry_patch_with_analysis_task, analyze_patch_failure_task, generate_alternative_patch_task

logger = get_logger("verification.service")


class VerificationService:
    def __init__(self):
        pass
    
    async def start_verification(self, patch_id: UUID) -> Dict[str, Any]:
        from tasks.verification_tasks import verify_patch_task
        verify_patch_task.delay(str(patch_id))
        return {"message": "Verification started", "patch_id": str(patch_id)}
    
    async def run_tests(self, repo: Repository) -> Dict[str, Any]:
        return await run_tests(repo)
    
    async def run_security_re_scan(self, repo: Repository, scan: Scan) -> bool:
        return await run_security_re_scan(repo, scan)
    
    async def apply_patch(self, repo_path: str, patch_content: str) -> Dict[str, Any]:
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
            f.write(patch_content)
            patch_file = f.name
        
        try:
            result = subprocess.run(
                ["git", "apply", "--check", patch_file],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Patch check failed: {result.stderr}",
                    "check_output": result.stderr,
                }
            
            result = subprocess.run(
                ["git", "apply", patch_file],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Patch apply failed: {result.stderr}",
                    "apply_output": result.stderr,
                }
            
            return {
                "success": True,
                "message": "Patch applied successfully",
            }
        finally:
            os.unlink(patch_file)
    
    async def verify_patch(
        self,
        repo: Repository,
        original_findings_count: int,
        scan: Scan = None
    ) -> Dict[str, Any]:
        test_results = await self.run_tests(repo)

        scan_passed = await run_security_re_scan(repo, scan)
        
        return {
            "test_passed": test_results["passed"],
            "test_details": test_results["commands"],
            "scan_passed": scan_passed,
            "findings_before": original_findings_count,
            "findings_after": test_results.get("findings_after", 0),
            "findings_reduced": original_findings_count - test_results.get("findings_after", 0),
            "new_findings": [],
        }
    
    async def trigger_retry_with_analysis(self, patch_id: UUID) -> Dict[str, Any]:
        retry_patch_with_analysis_task.delay(str(patch_id))
        return {"message": "Retry with AI analysis started", "patch_id": str(patch_id)}
    
    async def analyze_failure(self, patch_id: UUID) -> Dict[str, Any]:
        analyze_patch_failure_task.delay(str(patch_id))
        return {"message": "Failure analysis started", "patch_id": str(patch_id)}
    
    async def generate_alternative_patch(
        self,
        patch_id: UUID,
        strategy: str = "minimal"
    ) -> Dict[str, Any]:
        generate_alternative_patch_task.delay(str(patch_id), strategy)
        return {"message": f"Alternative patch generation started with {strategy} strategy", "patch_id": str(patch_id)}


class PatchVerificationPipeline:
    def __init__(self):
        self.service = VerificationService()
    
    async def run_full_pipeline(
        self,
        patch_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        patch = await db.get(Patch, patch_id)
        if not patch:
            raise ValueError("Patch not found")
        
        finding = await db.get(Finding, patch.finding_id)
        scan = await db.get(Scan, patch.scan_id)
        repo = await db.get(Repository, scan.repository_id)
        
        results = {
            "patch_id": str(patch_id),
            "steps": [],
            "final_status": patch.status.value,
            "success": False,
        }
        
        results["steps"].append({"step": "apply_patch", "status": "started"})
        
        apply_result = await self.service.apply_patch(repo.local_path, patch.diff)
        results["steps"].append({"step": "apply_patch", "status": "completed" if apply_result["success"] else "failed", "result": apply_result})
        
        if not apply_result["success"]:
            patch.status = PatchStatus.FAILED
            patch.error_message = apply_result["error"]
            await db.commit()
            results["final_status"] = "failed"
            return results
        
        patch.status = PatchStatus.APPLIED
        await db.commit()
        
        results["steps"].append({"step": "run_tests", "status": "started"})
        
        test_results = await self.service.run_tests(repo)
        results["steps"].append({"step": "run_tests", "status": "completed", "passed": test_results["passed"]})
        
        if not test_results["passed"]:
            results["steps"].append({"step": "test_failure", "status": "detected"})
            await self.service.trigger_retry_with_analysis(patch.id)
            results["final_status"] = "retrying"
            return results
        
        results["steps"].append({"step": "security_rescan", "status": "started"})
        
        scan_passed = await self.service.run_security_re_scan(repo, scan)
        results["steps"].append({"step": "security_rescan", "status": "completed", "passed": scan_passed})
        
        if not scan_passed:
            results["steps"].append({"step": "security_regression", "status": "detected"})
            await self.service.trigger_retry_with_analysis(patch.id)
            results["final_status"] = "retrying"
            return results
        
        patch.status = PatchStatus.APPLIED
        patch.verification_result = {
            "test_passed": test_results["passed"],
            "scan_passed": scan_passed,
            "verified_at": datetime.utcnow().isoformat(),
            "test_details": test_results["commands"],
        }
        finding.status = FindingStatus.FIXED
        await db.commit()
        
        results["final_status"] = "verified"
        results["success"] = True
        
        return results


verification_service = VerificationService()
pipeline = PatchVerificationPipeline()