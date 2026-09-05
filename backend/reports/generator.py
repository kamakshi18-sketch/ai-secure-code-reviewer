from typing import Dict, Any, List, Optional, BinaryIO
from uuid import UUID
from datetime import datetime
from pathlib import Path
import json
import structlog
import asyncio
from io import BytesIO
from sqlalchemy import select

from core.config import settings
from core.logging import get_logger
from models import Scan, Finding, Patch, Repository, Severity, FindingStatus, PatchStatus
from agents.documentation import DocumentationAgent
from rag.engine import RAGEngine

logger = get_logger("reports.generator")


class ReportGenerator:
    def __init__(self, rag_engine: RAGEngine = None):
        self.rag_engine = rag_engine or RAGEngine()
        self.doc_agent = DocumentationAgent(self.rag_engine)
        self.output_dir = Path(settings.REPORT_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate_report(
        self,
        scan_id: UUID,
        db,
        format: str = "markdown",
        title: str = None
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
        
        findings_data = self._serialize_findings(findings)
        patches_data = self._serialize_patches(patches)
        
        report_data = {
            "scan": self._serialize_scan(scan),
            "repository": self._serialize_repository(repo),
            "findings": findings_data,
            "patches": patches_data,
            "format": format,
            "title": title or f"Security Report - {repo.full_name}",
        }
        
        if format == "markdown":
            content = await self.doc_agent.generate_report(report_data)
            return {"content": content, "format": "markdown", "filename": f"report_{scan_id}.md"}
        
        elif format == "json":
            json_report = self.doc_agent._generate_json_report(report_data)
            return {"content": json.dumps(json_report, indent=2), "format": "json", "filename": f"report_{scan_id}.json"}
        
        elif format == "html":
            content = await self._generate_html_report(report_data)
            return {"content": content, "format": "html", "filename": f"report_{scan_id}.html"}
        
        elif format == "pdf":
            pdf_bytes = await self._generate_pdf_report(report_data)
            return {"content": pdf_bytes, "format": "pdf", "filename": f"report_{scan_id}.pdf"}
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _serialize_scan(self, scan: Scan) -> Dict[str, Any]:
        return {
            "id": str(scan.id),
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
            "branch": scan.branch,
            "commit_sha": scan.commit_sha,
            "scan_type": scan.scan_type.value,
            "status": scan.status.value,
            "scanners_used": scan.scanners_used,
            "duration_seconds": scan.duration_seconds,
        }
    
    def _serialize_repository(self, repo: Repository) -> Dict[str, Any]:
        return {
            "full_name": repo.full_name,
            "language": repo.language,
            "url": repo.url,
            "default_branch": repo.default_branch,
        }
    
    def _serialize_findings(self, findings: List[Finding]) -> List[Dict[str, Any]]:
        return [
            {
                "id": str(f.id),
                "scanner": f.scanner,
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "severity": f.severity.value,
                "file_path": f.file_path,
                "line_start": f.line_start,
                "line_end": f.line_end,
                "message": f.message,
                "cwe_id": f.cwe_id,
                "owasp_category": f.owasp_category,
                "confidence": f.confidence,
                "status": f.status.value,
                "ai_explanation": f.ai_explanation,
                "ai_root_cause": f.ai_root_cause,
                "ai_recommended_fix": f.ai_recommended_fix,
                "code_snippet": f.code_snippet,
            }
            for f in findings
        ]
    
    def _serialize_patches(self, patches: List[Patch]) -> List[Dict[str, Any]]:
        return [
            {
                "id": str(p.id),
                "finding_id": str(p.finding_id),
                "status": p.status.value,
                "file_path": p.file_path,
                "diff": p.diff,
                "language": p.language,
                "llm_provider": p.llm_provider,
                "llm_model": p.llm_model,
                "retry_count": p.retry_count,
                "verification_result": p.verification_result,
            }
            for p in patches
        ]
    
    async def _generate_html_report(self, data: Dict[str, Any]) -> str:
        markdown_content = data.get("content", "")
        if not markdown_content:
            markdown_content = self.doc_agent._generate_markdown_report(data)
        
        import markdown
        from bs4 import BeautifulSoup
        
        html_body = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code', 'codehilite'])
        
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data.get('title', 'Security Report')}</title>
    <style>
        {self._get_html_styles()}
    </style>
</head>
<body>
    <div class="container">
        {html_body}
    </div>
</body>
</html>
"""
        return html_template
    
    def _get_html_styles(self) -> str:
        return """
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 20px; }
        h1, h2, h3 { color: #1a1a2e; border-bottom: 2px solid #e0e0e0; padding-bottom: 8px; }
        h1 { font-size: 2.5em; }
        h2 { font-size: 1.8em; margin-top: 30px; }
        h3 { font-size: 1.4em; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border: 1px solid #ddd; }
        th { background-color: #f5f5f5; font-weight: 600; }
        tr:nth-child(even) { background-color: #fafafa; }
        code { background: #f4f4f4; padding: 2px 6px; border-radius: 4px; font-family: 'Monaco', 'Consolas', monospace; font-size: 0.9em; }
        pre { background: #1e1e1e; color: #d4d4d4; padding: 16px; border-radius: 8px; overflow-x: auto; }
        pre code { background: none; padding: 0; color: inherit; }
        .badge { display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 0.75em; font-weight: 600; margin: 2px; }
        .badge-critical { background: #fee; color: #c00; }
        .badge-high { background: #ffe; color: #e60; }
        .badge-medium { background: #fff3cd; color: #856404; }
        .badge-low { background: #d4edda; color: #155724; }
        .badge-info { background: #d1ecf1; color: #0c5460; }
        .badge-fixed { background: #d4edda; color: #155724; }
        .badge-open { background: #f8d7da; color: #721c24; }
        .badge-false_positive { background: #e2e3e5; color: #383d41; }
        .badge-wont_fix { background: #fff3cd; color: #856404; }
        .badge-ignored { background: #e2e3e5; color: #383d41; }
        .badge-in_progress { background: #cce5ff; color: #004085; }
        .badge-pending { background: #fff3cd; color: #856404; }
        .badge-generating { background: #cce5ff; color: #004085; }
        .badge-generated { background: #d4edda; color: #155724; }
        .badge-applying { background: #fff3cd; color: #856404; }
        .badge-applied { background: #d4edda; color: #155724; }
        .badge-failed { background: #f8d7da; color: #721c24; }
        .badge-rejected { background: #e2e3e5; color: #383d41; }
        .section { margin: 30px 0; }
        .meta { color: #666; font-size: 0.9em; margin: 10px 0; }
        .code-snippet { background: #f8f8f8; border-left: 4px solid #007acc; padding: 12px; margin: 15px 0; }
        .finding-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin: 20px 0; background: #fafafa; }
        .severity-critical { border-left: 5px solid #c00; }
        .severity-high { border-left: 5px solid #e60; }
        .severity-medium { border-left: 5px solid #f0ad4e; }
        .severity-low { border-left: 5px solid #5cb85c; }
        .severity-info { border-left: 5px solid #5bc0de; }
        .toc { background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .toc ul { list-style: none; padding-left: 0; }
        .toc li { margin: 8px 0; }
        .toc a { text-decoration: none; color: #007acc; }
        .toc a:hover { text-decoration: underline; }
        @media print {
            body { font-size: 12px; }
            .no-print { display: none; }
            pre { page-break-inside: avoid; }
        }
        """
    
    async def _generate_pdf_report(self, data: Dict[str, Any]) -> bytes:
        html_content = await self._generate_html_report(data)
        
        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            
            font_config = FontConfiguration()
            html_doc = HTML(string=html_content)
            
            css = CSS(string=self._get_pdf_styles(), font_config=font_config)
            
            pdf_bytes = html_doc.write_pdf(stylesheets=[css], font_config=font_config)
            return pdf_bytes
            
        except ImportError:
            logger.warning("WeasyPrint not available, falling back to markdown")
            markdown_content = self.doc_agent._generate_markdown_report(data)
            return markdown_content.encode('utf-8')
        except Exception as e:
            logger.error("PDF generation failed", error=str(e))
            markdown_content = self.doc_agent._generate_markdown_report(data)
            return markdown_content.encode('utf-8')
    
    def _get_pdf_styles(self) -> str:
        return """
        @page {
            size: A4;
            margin: 2.5cm;
            @top-center { content: "AI Secure Code Reviewer - Security Report"; font-size: 10px; color: #666; }
            @bottom-center { content: counter(page); font-size: 10px; color: #666; }
        }
        body { font-family: 'DejaVu Sans', 'Helvetica', sans-serif; font-size: 11pt; line-height: 1.5; }
        h1 { font-size: 24pt; page-break-after: avoid; }
        h2 { font-size: 18pt; page-break-after: avoid; margin-top: 24pt; }
        h3 { font-size: 14pt; page-break-after: avoid; }
        table { width: 100%; page-break-inside: auto; }
        tr { page-break-inside: avoid; page-break-after: auto; }
        thead { display: table-header-group; }
        tfoot { display: table-footer-group; }
        pre { page-break-inside: avoid; }
        .no-print { display: none; }
        .finding-card { page-break-inside: avoid; }
        """
    
    async def save_report(self, scan_id: UUID, content: Any, format: str) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"security_report_{scan_id}_{timestamp}.{format}"
        filepath = self.output_dir / filename
        
        if format == "pdf":
            with open(filepath, "wb") as f:
                f.write(content)
        else:
            with open(filepath, "w") as f:
                f.write(content)
        
        return str(filepath)


class ReportService:
    def __init__(self):
        self.generator = ReportGenerator()
    
    async def create_report(
        self,
        db,
        scan_id: UUID,
        format: str = "markdown",
        title: str = None
    ) -> Dict[str, Any]:
        from tasks.report_tasks import generate_report_task
        
        from models import SecurityReport, ReportFormat
        
        scan = await db.get(Scan, scan_id)
        if not scan:
            raise ValueError("Scan not found")
        
        if scan.status != "completed":
            raise ValueError("Scan must be completed before generating report")
        
        report = SecurityReport(
            scan_id=scan_id,
            format=ReportFormat(format),
            title=title or f"Security Report - {scan.repository_id}",
            executive_summary="",
            security_score=0.0,
            risk_score=0.0,
            severity_distribution={},
            owasp_mapping={},
            cwe_mapping={},
            fixed_issues=0,
            remaining_issues=0,
            patch_summary={},
            content="",
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        
        generate_report_task.delay(str(report.id))
        
        return {"report_id": str(report.id), "status": "generating"}
    
    async def get_report(self, db, report_id: UUID) -> Dict[str, Any]:
        from models import SecurityReport
        report = await db.get(SecurityReport, report_id)
        if not report:
            raise ValueError("Report not found")
        return report
    
    async def download_report(self, db, report_id: UUID) -> tuple:
        from models import SecurityReport, ReportFormat
        report = await db.get(SecurityReport, report_id)
        if not report:
            raise ValueError("Report not found")
        
        if report.file_path and Path(report.file_path).exists():
            with open(report.file_path, "rb") as f:
                content = f.read()
        else:
            content = report.content.encode('utf-8') if isinstance(report.content, str) else report.content
        
        media_type = {
            ReportFormat.MARKDOWN: "text/markdown",
            ReportFormat.PDF: "application/pdf",
            ReportFormat.JSON: "application/json",
            ReportFormat.HTML: "text/html",
        }.get(report.format, "application/octet-stream")
        
        filename = f"security_report_{report_id}.{report.format.value}"
        return content, media_type, filename
    
    async def list_reports(
        self,
        db,
        scan_id: UUID = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        from sqlalchemy import select, func
        from models import SecurityReport
        
        query = select(SecurityReport)
        if scan_id:
            query = query.where(SecurityReport.scan_id == scan_id)
        
        total = await db.scalar(select(func.count()).select_from(query.subquery()))
        
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(SecurityReport.created_at.desc())
        result = await db.execute(query)
        reports = result.scalars().all()
        
        return {
            "items": reports,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }


report_service = ReportService()