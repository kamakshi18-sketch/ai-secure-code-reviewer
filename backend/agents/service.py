from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import asyncio

from core.logging import get_logger
from database.session import get_db
from models import Scan, Finding, FindingStatus, Patch, Repository, PullRequest, ScanStatus
from rag.engine import RAGEngine, rag_engine
from agents.base import AgentOrchestrator
from agents.coordinator import CoordinatorAgent, WorkflowOrchestrator, workflow_orchestrator
from agents.security_analysis import SecurityAnalysisAgent
from agents.patch_generator import PatchGeneratorAgent
from agents.verification import VerificationAgent
from agents.documentation import DocumentationAgent
from agents.github_agent import GitHubAgent
from tasks.patch_tasks import generate_patch_task, apply_patch_task
from tasks.github_tasks import create_pull_request_task

logger = get_logger("agents.service")


class AgentService:
    def __init__(self):
        self.rag_engine = rag_engine
        self.coordinator = CoordinatorAgent(self.rag_engine)
        self.workflow_orchestrator = WorkflowOrchestrator(self.rag_engine)
        self.security_agent = SecurityAnalysisAgent(self.rag_engine)
        self.patch_agent = PatchGeneratorAgent(self.rag_engine)
        self.verification_agent = VerificationAgent(self.rag_engine)
        self.documentation_agent = DocumentationAgent(self.rag_engine)
        self.github_agent = GitHubAgent(self.rag_engine)
    
    async def initialize(self):
        await self.rag_engine.initialize()
    
    async def run_full_security_review(
        self,
        scan_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        scan = await db.get(Scan, scan_id)
        if not scan:
            raise ValueError("Scan not found")
        
        repo = await db.get(Repository, scan.repository_id)
        if not repo:
            raise ValueError("Repository not found")
        
        result = await db.execute(
            select(Finding).where(
                Finding.scan_id == scan_id,
                Finding.status == FindingStatus.OPEN
            )
        )
        findings = result.scalars().all()
        
        findings_data = []
        for f in findings:
            finding_dict = {
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
                "confidence": f.confidence,
                "status": f.status.value,
            }
            findings_data.append(finding_dict)
        
        repository_data = {
            "id": str(repo.id),
            "full_name": repo.full_name,
            "language": repo.language,
        }
        
        scan_data = {
            "id": str(scan.id),
            "branch": scan.branch,
            "commit_sha": scan.commit_sha,
        }
        
        return await self.workflow_orchestrator.run_security_review_workflow(
            scan_id=str(scan_id),
            findings=findings_data,
            repository=repository_data
        )
    
    async def analyze_finding(
        self,
        finding_id: UUID,
        db: AsyncSession,
        question: Optional[str] = None
    ) -> Dict[str, Any]:
        finding = await db.get(Finding, finding_id)
        if not finding:
            raise ValueError("Finding not found")
        
        scan = await db.get(Scan, finding.scan_id)
        repo = await db.get(Repository, scan.repository_id)
        
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
            "confidence": finding.confidence,
        }
        
        context = {
            "repository": repo.full_name,
            "language": repo.language,
        }
        
        if question:
            return await self.security_agent.explain_finding(finding_dict, question, context)
        
        return await self.security_agent.analyze_finding(
            finding=finding_dict,
            source_code="",
            file_path=finding.file_path,
            language=repo.language or "python"
        )
    
    async def generate_patch_for_finding(
        self,
        finding_id: UUID,
        db: AsyncSession,
        source_code: str = ""
    ) -> Dict[str, Any]:
        finding = await db.get(Finding, finding_id)
        if not finding:
            raise ValueError("Finding not found")
        
        scan = await db.get(Scan, finding.scan_id)
        repo = await db.get(Repository, scan.repository_id)
        
        if not source_code and repo.local_path:
            import os
            file_path = os.path.join(repo.local_path, finding.file_path)
            if os.path.exists(file_path):
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
        
        return await self.patch_agent.generate_patch(
            finding=finding_dict,
            source_code=source_code,
            file_path=finding.file_path,
            language=repo.language or "python"
        )
    
    async def verify_patch(
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
        
        patch_dict = {
            "id": str(patch.id),
            "diff": patch.diff,
            "file_path": patch.file_path,
            "status": patch.status.value,
        }
        
        finding_dict = {
            "id": str(finding.id),
            "rule_name": finding.rule_name,
            "severity": finding.severity.value,
            "file_path": finding.file_path,
        }
        
        verification = patch.verification_result or {}
        test_results = verification.get("test_details", {})
        scan_results = verification.get("scan_details", {})
        
        return await self.verification_agent.analyze_failure({
            "patch": patch_dict,
            "test_results": test_results,
            "scan_results": scan_results,
            "original_finding": finding_dict,
        })
    
    async def generate_report(
        self,
        scan_id: UUID,
        db: AsyncSession,
        format_type: str = "markdown"
    ) -> Dict[str, Any]:
        scan = await db.get(Scan, scan_id)
        if not scan:
            raise ValueError("Scan not found")
        
        repo = await db.get(Repository, scan.repository_id)
        
        result = await db.execute(
            select(Finding).where(Finding.scan_id == scan_id)
        )
        findings = result.scalars().all()
        
        result = await db.execute(
            select(Patch).where(Patch.scan_id == scan_id)
        )
        patches = result.scalars().all()
        
        findings_data = []
        for f in findings:
            findings_data.append({
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
            })
        
        patches_data = []
        for p in patches:
            patches_data.append({
                "id": str(p.id),
                "finding_id": str(p.finding_id),
                "status": p.status.value,
                "file_path": p.file_path,
                "diff": p.diff,
            })
        
        return await self.documentation_agent.generate_report({
            "scan": {
                "id": str(scan.id),
                "created_at": scan.created_at.isoformat() if scan.created_at else None,
                "branch": scan.branch,
                "commit_sha": scan.commit_sha,
            },
            "repository": {
                "full_name": repo.full_name,
                "language": repo.language,
            },
            "findings": findings_data,
            "patches": patches_data,
            "format": format_type,
        })
    
    async def create_pull_request(
        self,
        scan_id: UUID,
        db: AsyncSession,
        patch_ids: List[UUID],
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main"
    ) -> Dict[str, Any]:
        scan = await db.get(Scan, scan_id)
        if not scan:
            raise ValueError("Scan not found")
        
        repo = await db.get(Repository, scan.repository_id)
        if not repo:
            raise ValueError("Repository not found")
        
        if not repo.owner.github_access_token:
            raise ValueError("GitHub access token not available")
        
        patches = []
        for pid in patch_ids:
            patch = await db.get(Patch, pid)
            if patch and patch.status.value == "applied":
                finding = await db.get(Finding, patch.finding_id)
                patches.append({
                    "id": str(patch.id),
                    "finding": {
                        "rule_id": finding.rule_id if finding else None,
                        "rule_name": finding.rule_name if finding else None,
                        "severity": finding.severity.value if finding else None,
                    },
                    "file_path": patch.file_path,
                })
        
        if not patches:
            raise ValueError("No applied patches to include")
        
        return await self.github_agent.create_pr({
            "repository": {"full_name": repo.full_name},
            "patches": patches,
            "title": title,
            "body": body,
            "head_branch": head_branch,
            "base_branch": base_branch,
            "access_token": repo.owner.github_access_token,
            "local_path": repo.local_path,
        })


agent_service = AgentService()