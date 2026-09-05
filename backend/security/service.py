from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import structlog

from core.logging import get_logger
from database.session import get_db
from models import Scan, ScanStatus, Finding, Severity, Repository
from security.scanners import scanner_registry
from security.aggregator import finding_aggregator, finding_deduplicator
from tasks.scan_tasks import run_security_scan_task

logger = get_logger("security.service")


class ScanService:
    def __init__(self):
        pass
    
    async def create_scan(
        self,
        db: AsyncSession,
        repository_id: UUID,
        initiated_by_id: UUID,
        scan_type: str = "full",
        commit_sha: Optional[str] = None,
        branch: Optional[str] = None,
        scanners: Optional[List[str]] = None
    ) -> Scan:
        repo = await db.get(Repository, repository_id)
        if not repo:
            raise ValueError("Repository not found")
        
        scan = Scan(
            repository_id=repository_id,
            initiated_by_id=initiated_by_id,
            scan_type=scan_type,
            commit_sha=commit_sha,
            branch=branch or repo.default_branch,
            scanners_used=scanners or [],
            status=ScanStatus.PENDING,
        )
        db.add(scan)
        await db.commit()
        await db.refresh(scan)
        
        return scan
    
    async def start_scan(self, scan_id: UUID) -> None:
        run_security_scan_task.delay(str(scan_id))
    
    async def cancel_scan(self, db: AsyncSession, scan_id: UUID) -> Scan:
        scan = await db.get(Scan, scan_id)
        if not scan:
            raise ValueError("Scan not found")
        
        if scan.status not in [ScanStatus.PENDING, ScanStatus.RUNNING]:
            raise ValueError(f"Cannot cancel scan with status {scan.status}")
        
        scan.status = ScanStatus.CANCELLED
        await db.commit()
        await db.refresh(scan)
        
        return scan
    
    async def retry_scan(self, db: AsyncSession, scan_id: UUID) -> Scan:
        scan = await db.get(Scan, scan_id)
        if not scan:
            raise ValueError("Scan not found")
        
        if scan.status not in [ScanStatus.FAILED, ScanStatus.CANCELLED, ScanStatus.COMPLETED]:
            raise ValueError(f"Cannot retry scan with status {scan.status}")
        
        new_scan = Scan(
            repository_id=scan.repository_id,
            initiated_by_id=scan.initiated_by_id,
            scan_type=scan.scan_type,
            commit_sha=scan.commit_sha,
            branch=scan.branch,
            scanners_used=scan.scanners_used,
            status=ScanStatus.PENDING,
        )
        db.add(new_scan)
        await db.commit()
        await db.refresh(new_scan)
        
        run_security_scan_task.delay(str(new_scan.id))
        
        return new_scan
    
    async def get_scan_summary(self, db: AsyncSession, scan_id: UUID) -> Dict[str, Any]:
        scan = await db.get(Scan, scan_id)
        if not scan:
            raise ValueError("Scan not found")
        
        severity_counts = await db.execute(
            select(Finding.severity, func.count(Finding.id))
            .where(Finding.scan_id == scan_id)
            .group_by(Finding.severity)
        )
        
        scanner_counts = await db.execute(
            select(Finding.scanner, func.count(Finding.id))
            .where(Finding.scan_id == scan_id)
            .group_by(Finding.scanner)
        )
        
        status_counts = await db.execute(
            select(Finding.status, func.count(Finding.id))
            .where(Finding.scan_id == scan_id)
            .group_by(Finding.status)
        )
        
        return {
            "scan_id": str(scan_id),
            "total_findings": scan.total_findings,
            "by_severity": {s.value: c for s, c in severity_counts.all()},
            "by_scanner": dict(scanner_counts.all()),
            "by_status": {s.value: c for s, c in status_counts.all()},
            "status": scan.status.value,
            "duration_seconds": scan.duration_seconds,
            "scanners_used": scan.scanners_used,
        }
    
    async def run_scan_manually(
        self,
        path: str,
        language: Optional[str] = None,
        scanners: Optional[List[str]] = None
    ) -> List[Finding]:
        return await scanner_registry.run_scanners(path, language, scanners)
    
    async def get_scanner_status(self) -> Dict[str, bool]:
        status = {}
        for name in scanner_registry.scanners:
            scanner = scanner_registry.get_scanner(name)
            if scanner:
                status[name] = scanner.is_available()
        return status


class FindingService:
    def __init__(self):
        pass
    
    async def update_finding_status(
        self,
        db: AsyncSession,
        finding_id: UUID,
        status: str
    ) -> Finding:
        finding = await db.get(Finding, finding_id)
        if not finding:
            raise ValueError("Finding not found")
        
        finding.status = status
        await db.commit()
        await db.refresh(finding)
        
        return finding
    
    async def bulk_update_status(
        self,
        db: AsyncSession,
        finding_ids: List[UUID],
        status: str
    ) -> int:
        result = await db.execute(
            select(Finding).where(Finding.id.in_(finding_ids))
        )
        findings = result.scalars().all()
        
        for finding in findings:
            finding.status = status
        
        await db.commit()
        
        return len(findings)
    
    async def get_finding_stats(
        self,
        db: AsyncSession,
        repository_id: Optional[UUID] = None,
        scan_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        query = select(Finding)
        
        if repository_id:
            query = query.join(Scan).where(Scan.repository_id == repository_id)
        if scan_id:
            query = query.where(Finding.scan_id == scan_id)
        
        total = await db.scalar(select(func.count()).select_from(query.subquery()))
        
        severity_counts = await db.execute(
            query.with_only_columns(Finding.severity, func.count(Finding.id))
            .group_by(Finding.severity)
        )
        
        status_counts = await db.execute(
            query.with_only_columns(Finding.status, func.count(Finding.id))
            .group_by(Finding.status)
        )
        
        scanner_counts = await db.execute(
            query.with_only_columns(Finding.scanner, func.count(Finding.id))
            .group_by(Finding.scanner)
        )
        
        cwe_counts = await db.execute(
            query.with_only_columns(Finding.cwe_id, func.count(Finding.id))
            .where(Finding.cwe_id.isnot(None))
            .group_by(Finding.cwe_id)
            .order_by(func.count(Finding.id).desc())
            .limit(10)
        )
        
        return {
            "total": total,
            "by_severity": {s.value: c for s, c in severity_counts.all()},
            "by_status": {s.value: c for s, c in status_counts.all()},
            "by_scanner": dict(scanner_counts.all()),
            "top_cwes": dict(cwe_counts.all()),
        }
    
    async def get_finding_details(
        self,
        db: AsyncSession,
        finding_id: UUID
    ) -> Optional[Finding]:
        return await db.get(Finding, finding_id)


scan_service = ScanService()
finding_service = FindingService()