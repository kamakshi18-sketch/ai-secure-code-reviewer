from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import asyncio
import subprocess
import os
import shlex
from datetime import datetime

from core.celery_app import celery_app
from core.logging import get_logger, log_task_event
from database.session import async_session_maker
from models import Patch, PatchStatus, Finding, FindingStatus, Scan, ScanStatus, Repository, TestResult, TestStatus, PatchAttempt
from core.config import settings
from tasks.scan_tasks import run_security_scan_task

logger = get_logger("verification_tasks")

ALLOWED_TEST_BINARIES = {
    "pytest", "python", "python3", "npm", "yarn", "pnpm",
    "mvn", "gradle", "gradlew", "go", "bundle", "phpunit"
}


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def verify_patch_task(self, patch_id: str):
    log_task_event("verify_patch", "started", patch_id=patch_id)
    
    async def _verify():
        async with async_session_maker() as db:
            patch = await db.get(Patch, patch_id)
            if not patch:
                logger.error("Patch not found", patch_id=patch_id)
                return
            
            finding = await db.get(Finding, patch.finding_id)
            scan = await db.get(Scan, patch.scan_id)
            repo = await db.get(Repository, scan.repository_id)
            
            try:
                test_results = await run_tests(repo)
                
                scan_passed = await run_security_re_scan(repo, scan)
                
                attempt = await db.execute(
                    select(PatchAttempt).where(
                        PatchAttempt.patch_id == patch_id
                    ).order_by(PatchAttempt.attempt_number.desc())
                )
                attempt = attempt.scalar_one_or_none()
                
                if attempt:
                    attempt.test_passed = test_results["passed"]
                    attempt.scan_passed = scan_passed
                    attempt.findings_before = test_results.get("findings_before", 0)
                    attempt.findings_after = test_results.get("findings_after", 0)
                    attempt.duration_ms = int(test_results.get("duration_ms", 0))
                
                if test_results["passed"] and scan_passed:
                    patch.status = PatchStatus.APPLIED
                    patch.verification_result = {
                        "test_passed": test_results["passed"],
                        "scan_passed": scan_passed,
                        "verified_at": datetime.utcnow().isoformat(),
                        "test_details": test_results.get("commands", []),
                        "scan_details": test_results.get("scan_details", {}),
                    }
                    finding.status = FindingStatus.FIXED
                    await db.commit()
                    
                    logger.info("Patch verified successfully", patch_id=patch_id)
                else:
                    if patch.retry_count < settings.MAX_PATCH_RETRIES:
                        patch.status = PatchStatus.PENDING
                        patch.retry_count += 1
                        await db.commit()
                        
                        from tasks.patch_tasks import generate_patch_task
                        generate_patch_task.delay(patch_id)
                    else:
                        patch.status = PatchStatus.REJECTED
                        patch.verification_result = {
                            "test_passed": test_results["passed"],
                            "scan_passed": scan_passed,
                            "rejected_at": datetime.utcnow().isoformat(),
                            "reason": "Max retries exceeded or verification failed",
                            "test_details": test_results.get("commands", []),
                            "scan_details": test_results.get("scan_details", {}),
                        }
                        await db.commit()
                
                log_task_event("verify_patch", "completed", patch_id=patch_id, test_passed=test_results["passed"], scan_passed=scan_passed)
                
            except Exception as e:
                logger.error("Patch verification failed", patch_id=patch_id, error=str(e))
                log_task_event("verify_patch", "failed", patch_id=patch_id, error=str(e))
                raise self.retry(exc=e)
    
    asyncio.run(_verify())


async def run_tests(repo: Repository) -> dict:
    test_commands = detect_test_commands(repo.local_path, repo.language)
    
    results = {
        "passed": True,
        "commands": [],
        "overall_exit_code": 0,
        "duration_ms": 0,
        "findings_before": 0,
        "findings_after": 0,
    }
    
    start_time = datetime.utcnow()
    
    for cmd in test_commands:
        cmd_start = datetime.utcnow()
        try:
            cmd_args = shlex.split(cmd) if isinstance(cmd, str) else list(cmd)
            base_bin = os.path.basename(cmd_args[0]).lower() if cmd_args else ""
            if not cmd_args or base_bin not in ALLOWED_TEST_BINARIES:
                logger.warning("Disallowed test command skipped", command=cmd)
                continue

            result = subprocess.run(
                cmd_args,
                cwd=repo.local_path,
                shell=False,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            cmd_duration = (datetime.utcnow() - cmd_start).total_seconds() * 1000
            
            results["commands"].append({
                "command": cmd,
                "exit_code": result.returncode,
                "stdout": result.stdout[-2000:] if result.stdout else None,
                "stderr": result.stderr[-2000:] if result.stderr else None,
                "duration_ms": cmd_duration,
                "framework": detect_test_framework(cmd),
            })
            
            if result.returncode != 0:
                results["passed"] = False
                results["overall_exit_code"] = result.returncode
                
        except subprocess.TimeoutExpired:
            cmd_duration = 300000
            results["passed"] = False
            results["overall_exit_code"] = -1
            results["commands"].append({
                "command": cmd,
                "exit_code": -1,
                "stdout": None,
                "stderr": "Test timeout (300s)",
                "duration_ms": cmd_duration,
                "framework": detect_test_framework(cmd),
            })
        except Exception as e:
            results["passed"] = False
            results["overall_exit_code"] = -1
            results["commands"].append({
                "command": cmd,
                "exit_code": -1,
                "stdout": None,
                "stderr": str(e),
                "duration_ms": 0,
                "framework": detect_test_framework(cmd),
            })
    
    results["duration_ms"] = (datetime.utcnow() - start_time).total_seconds() * 1000
    return results


async def run_security_re_scan(repo: Repository, original_scan: Scan) -> bool:
    try:
        new_scan = Scan(
            repository_id=repo.id,
            scan_type="verification",
            commit_sha=original_scan.commit_sha,
            branch=original_scan.branch,
            scanners_used=original_scan.scanners_used,
            status=ScanStatus.PENDING,
        )
        
        from database.session import async_session_maker
        async with async_session_maker() as db:
            db.add(new_scan)
            await db.commit()
            await db.refresh(new_scan)
        
        run_security_scan_task.delay(str(new_scan.id))
        
        import asyncio
        for _ in range(120):
            await asyncio.sleep(10)
            async with async_session_maker() as db:
                await db.refresh(new_scan)
                if new_scan.status == ScanStatus.COMPLETED:
                    if new_scan.total_findings < original_scan.total_findings:
                        return True
                    return False
                elif new_scan.status == ScanStatus.FAILED:
                    return False
        
        return False
        
    except Exception as e:
        logger.error("Security re-scan failed", repo_id=str(repo.id), error=str(e))
        return False


def detect_test_commands(repo_path: str, language: str) -> list:
    commands = []
    
    if language == "python":
        if os.path.exists(os.path.join(repo_path, "pytest.ini")) or \
           os.path.exists(os.path.join(repo_path, "pyproject.toml")) or \
           any(f.startswith("test_") or f.endswith("_test.py") for f in os.listdir(repo_path) if f.endswith(".py")):
            commands.append("pytest -v")
        elif os.path.exists(os.path.join(repo_path, "setup.py")):
            commands.append("python -m pytest")
    
    elif language in ["javascript", "typescript"]:
        package_json = os.path.join(repo_path, "package.json")
        if os.path.exists(package_json):
            import json
            with open(package_json) as f:
                pkg = json.load(f)
                scripts = pkg.get("scripts", {})
                if "test" in scripts:
                    commands.append("npm test")
                if "test:ci" in scripts:
                    commands.append("npm run test:ci")
    
    elif language == "java":
        if os.path.exists(os.path.join(repo_path, "pom.xml")):
            commands.append("mvn test")
        elif os.path.exists(os.path.join(repo_path, "build.gradle")):
            commands.append("./gradlew test")
    
    elif language == "go":
        commands.append("go test ./...")
    
    elif language == "ruby":
        if os.path.exists(os.path.join(repo_path, "Gemfile")):
            commands.append("bundle exec rspec")
    
    elif language == "php":
        if os.path.exists(os.path.join(repo_path, "phpunit.xml")):
            commands.append("./vendor/bin/phpunit")
    
    return commands


def detect_test_framework(command: str) -> str:
    if "pytest" in command:
        return "pytest"
    elif "npm test" in command:
        return "jest"
    elif "mvn test" in command:
        return "junit"
    elif "gradle" in command:
        return "junit"
    elif "go test" in command:
        return "go test"
    elif "rspec" in command:
        return "rspec"
    elif "phpunit" in command:
        return "phpunit"
    return "unknown"