import structlog
from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage
from datetime import datetime

from agents.base import BaseAgent
from rag.engine import RAGEngine

logger = structlog.get_logger("agents.documentation")


class DocumentationAgent(BaseAgent):
    def __init__(self, rag_engine: RAGEngine = None):
        super().__init__(rag_engine)
        self.system_prompt = """You are a Senior Technical Writer specializing in security documentation.
Your task is to generate professional security reports that are:
1. Clear and actionable for developers
2. Comprehensive for security teams
3. Executive-friendly for management
4. Compliant with industry standards (OWASP, CWE, etc.)

Guidelines:
- Use proper markdown formatting
- Include executive summary
- Map findings to OWASP and CWE
- Provide before/after comparison
- Include patch summary
- Generate in multiple formats (Markdown, JSON, PDF-ready)"""

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action", "generate_report")
        
        if action == "generate_report":
            return await self.generate_report(input_data)
        elif action == "generate_executive_summary":
            return await self.generate_executive_summary(input_data)
        elif action == "format_finding":
            return await self.format_finding(input_data)
        else:
            return await self.generate_report(input_data)
    
    async def generate_report(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        scan = input_data.get("scan")
        findings = input_data.get("findings", [])
        patches = input_data.get("patches", [])
        repository = input_data.get("repository")
        format_type = input_data.get("format", "markdown")
        
        severity_dist = {}
        for sev in ["critical", "high", "medium", "low", "info"]:
            severity_dist[sev] = sum(1 for f in findings if f.get("severity") == sev)
        
        owasp_mapping = {}
        for f in findings:
            if f.get("owasp_category"):
                owasp_mapping[f["owasp_category"]] = owasp_mapping.get(f["owasp_category"], 0) + 1
        
        cwe_mapping = {}
        for f in findings:
            if f.get("cwe_id"):
                cwe_mapping[f["cwe_id"]] = cwe_mapping.get(f["cwe_id"], 0) + 1
        
        fixed_issues = sum(1 for f in findings if f.get("status") == "fixed")
        remaining_issues = sum(1 for f in findings if f.get("status") == "open")
        
        applied_patches = [p for p in patches if p.get("status") == "applied"]
        patch_summary = {
            "total_generated": len(patches),
            "applied": len(applied_patches),
            "failed": sum(1 for p in patches if p.get("status") == "failed"),
            "rejected": sum(1 for p in patches if p.get("status") == "rejected"),
        }
        
        security_score = self._calculate_security_score(findings)
        risk_score = self._calculate_risk_score(findings)
        
        executive_summary = await self.generate_executive_summary({
            "scan": scan,
            "findings": findings,
            "patches": patches,
            "repository": repository,
            "security_score": security_score,
            "risk_score": risk_score
        })
        
        content = self._generate_markdown_report({
            "scan": scan,
            "repository": repository,
            "findings": findings,
            "patches": patches,
            "severity_distribution": severity_dist,
            "owasp_mapping": owasp_mapping,
            "cwe_mapping": cwe_mapping,
            "fixed_issues": fixed_issues,
            "remaining_issues": remaining_issues,
            "patch_summary": patch_summary,
            "security_score": security_score,
            "risk_score": risk_score,
            "executive_summary": executive_summary.get("summary", "")
        })
        
        if format_type == "json":
            return self._generate_json_report({
                "scan": scan,
                "repository": repository,
                "findings": findings,
                "patches": patches,
                "severity_distribution": severity_dist,
                "owasp_mapping": owasp_mapping,
                "cwe_mapping": cwe_mapping,
                "fixed_issues": fixed_issues,
                "remaining_issues": remaining_issues,
                "patch_summary": patch_summary,
                "security_score": security_score,
                "risk_score": risk_score,
                "executive_summary": executive_summary.get("summary", ""),
                "content": content
            })
        
        return {
            "content": content,
            "format": format_type,
            "security_score": security_score,
            "risk_score": risk_score,
            "severity_distribution": severity_dist,
            "owasp_mapping": owasp_mapping,
            "cwe_mapping": cwe_mapping,
            "fixed_issues": fixed_issues,
            "remaining_issues": remaining_issues,
            "patch_summary": patch_summary,
        }
    
    async def generate_executive_summary(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        scan = input_data.get("scan")
        findings = input_data.get("findings", [])
        patches = input_data.get("patches", [])
        repository = input_data.get("repository")
        security_score = input_data.get("security_score", 0)
        risk_score = input_data.get("risk_score", 0)
        
        critical = sum(1 for f in findings if f.get("severity") == "critical")
        high = sum(1 for f in findings if f.get("severity") == "high")
        applied = sum(1 for p in patches if p.get("status") == "applied")
        
        rag_results = await self.rag_engine.query(
            "security report executive summary best practices",
            top_k=3
        )
        
        context = f"""
Repository: {repository.get('full_name') if repository else 'Unknown'}
Scan Date: {scan.get('created_at') if scan else 'Unknown'}
Total Findings: {len(findings)}
Critical: {critical}, High: {high}
Security Score: {security_score}/100
Risk Score: {risk_score}/100
Patches Applied: {applied}/{len(patches)}

Relevant Guidelines:
{chr(10).join([r['content'][:300] for r in rag_results])}
"""
        
        messages = [
            SystemMessage(content="""You are a Security Executive writing a summary for leadership.
Be concise, business-focused, and highlight risk posture.
Mention key metrics: security score, critical findings, remediation progress.
Avoid technical jargon - focus on business impact."""),
            SystemMessage(content=context),
            HumanMessage(content="Write an executive summary for this security report.")
        ]
        
        response = await self._call_llm(messages)
        
        return {"summary": response}
    
    async def format_finding(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        finding = input_data.get("finding")
        format_type = input_data.get("format", "markdown")
        
        if format_type == "markdown":
            return {"content": self._format_finding_markdown(finding)}
        elif format_type == "json":
            return {"content": finding}
        else:
            return {"content": self._format_finding_markdown(finding)}
    
    def _calculate_security_score(self, findings: List[Dict[str, Any]]) -> float:
        if not findings:
            return 100.0
        
        weights = {
            "critical": 20,
            "high": 10,
            "medium": 5,
            "low": 2,
            "info": 1,
        }
        
        total_penalty = sum(weights.get(f.get("severity", "info"), 0) for f in findings)
        score = max(0, 100 - total_penalty)
        return round(score, 1)
    
    def _calculate_risk_score(self, findings: List[Dict[str, Any]]) -> float:
        if not findings:
            return 0.0
        
        weights = {
            "critical": 10,
            "high": 7,
            "medium": 4,
            "low": 2,
            "info": 1,
        }
        
        total_risk = sum(weights.get(f.get("severity", "info"), 0) for f in findings)
        max_possible = len(findings) * 10
        score = min(100, (total_risk / max_possible) * 100) if max_possible > 0 else 0
        return round(score, 1)
    
    def _generate_markdown_report(self, data: Dict[str, Any]) -> str:
        scan = data.get("scan", {})
        repo = data.get("repository", {})
        findings = data.get("findings", [])
        patches = data.get("patches", [])
        
        lines = []
        
        lines.append(f"# Security Report: {repo.get('full_name', 'Unknown Repository')}")
        lines.append("")
        lines.append(f"**Repository:** {repo.get('full_name', 'Unknown')}")
        lines.append(f"**Scan ID:** {scan.get('id', 'Unknown')}")
        lines.append(f"**Scan Date:** {scan.get('created_at', 'Unknown')}")
        lines.append(f"**Branch:** {scan.get('branch', 'Unknown')}")
        lines.append(f"**Commit:** {scan.get('commit_sha', 'N/A')}")
        lines.append(f"**Report Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("")
        
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(data.get("executive_summary", "No executive summary provided."))
        lines.append("")
        
        lines.append("## Security Score")
        lines.append("")
        lines.append(f"**Overall Security Score:** {data.get('security_score', 0)}/100")
        lines.append(f"**Risk Score:** {data.get('risk_score', 0)}/100")
        lines.append("")
        
        lines.append("## Severity Distribution")
        lines.append("")
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        for sev in ["critical", "high", "medium", "low", "info"]:
            count = data.get("severity_distribution", {}).get(sev, 0)
            lines.append(f"| {sev.capitalize()} | {count} |")
        lines.append("")
        
        lines.append("## OWASP Top 10 Mapping")
        lines.append("")
        if data.get("owasp_mapping"):
            lines.append("| OWASP Category | Count |")
            lines.append("|----------------|-------|")
            for cat, count in sorted(data.get("owasp_mapping", {}).items(), key=lambda x: -x[1]):
                lines.append(f"| {cat} | {count} |")
        else:
            lines.append("No OWASP categories identified.")
        lines.append("")
        
        lines.append("## CWE Mapping (Top 10)")
        lines.append("")
        if data.get("cwe_mapping"):
            lines.append("| CWE ID | Count |")
            lines.append("|--------|-------|")
            for cwe, count in sorted(data.get("cwe_mapping", {}).items(), key=lambda x: -x[1])[:10]:
                lines.append(f"| {cwe} | {count} |")
        else:
            lines.append("No CWEs identified.")
        lines.append("")
        
        lines.append("## Patch Summary")
        lines.append("")
        ps = data.get("patch_summary", {})
        lines.append(f"- **Total Patches Generated:** {ps.get('total_generated', 0)}")
        lines.append(f"- **Successfully Applied:** {ps.get('applied', 0)}")
        lines.append(f"- **Failed:** {ps.get('failed', 0)}")
        lines.append(f"- **Rejected:** {ps.get('rejected', 0)}")
        lines.append("")
        
        lines.append("## Fixed Issues")
        lines.append("")
        lines.append(f"**Total Fixed:** {data.get('fixed_issues', 0)}")
        lines.append("")
        
        fixed_findings = [f for f in findings if f.get("status") == "fixed"]
        if fixed_findings:
            lines.append("| File | Rule | Severity |")
            lines.append("|------|------|----------|")
            for f in fixed_findings:
                lines.append(f"| {f.get('file_path')}:{f.get('line_start')} | {f.get('rule_name')} | {f.get('severity')} |")
        else:
            lines.append("No issues fixed in this scan.")
        lines.append("")
        
        lines.append("## Remaining Issues")
        lines.append("")
        lines.append(f"**Total Remaining:** {data.get('remaining_issues', 0)}")
        lines.append("")
        
        open_findings = [f for f in findings if f.get("status") == "open"]
        if open_findings:
            lines.append("| File | Rule | Severity | Status |")
            lines.append("|------|------|----------|--------|")
            for f in sorted(open_findings, key=lambda x: (x.get("severity", ""), x.get("file_path", ""))):
                lines.append(f"| {f.get('file_path')}:{f.get('line_start')} | {f.get('rule_name')} | {f.get('severity')} | {f.get('status')} |")
        else:
            lines.append("No open issues remaining.")
        lines.append("")
        
        lines.append("## Detailed Findings")
        lines.append("")
        for finding in sorted(findings, key=lambda x: (x.get("severity", ""), x.get("file_path", ""))):
            lines.append(f"### {finding.get('rule_name')} ({finding.get('severity', '').upper()})")
            lines.append("")
            lines.append(f"- **Scanner:** {finding.get('scanner')}")
            lines.append(f"- **Rule ID:** {finding.get('rule_id')}")
            lines.append(f"- **File:** {finding.get('file_path')}:{finding.get('line_start')}")
            if finding.get("cwe_id"):
                lines.append(f"- **CWE:** {finding.get('cwe_id')}")
            if finding.get("owasp_category"):
                lines.append(f"- **OWASP:** {finding.get('owasp_category')}")
            lines.append(f"- **Status:** {finding.get('status')}")
            lines.append("")
            lines.append(f"**Description:** {finding.get('message')}")
            lines.append("")
            
            if finding.get("ai_explanation"):
                lines.append("**AI Explanation:**")
                lines.append(finding.get("ai_explanation"))
                lines.append("")
            
            if finding.get("code_snippet"):
                lines.append("**Code Snippet:**")
                lines.append("```")
                lines.append(finding.get("code_snippet"))
                lines.append("```")
                lines.append("")
        
        lines.append("---")
        lines.append("*Report generated by AI Secure Code Reviewer*")
        
        return "\n".join(lines)
    
    def _generate_json_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": f"Security Report: {data.get('repository', {}).get('full_name', 'Unknown')}",
            "scan_id": str(data.get("scan", {}).get("id", "")),
            "generated_at": datetime.utcnow().isoformat(),
            "security_score": data.get("security_score"),
            "risk_score": data.get("risk_score"),
            "severity_distribution": data.get("severity_distribution"),
            "owasp_mapping": data.get("owasp_mapping"),
            "cwe_mapping": data.get("cwe_mapping"),
            "fixed_issues": data.get("fixed_issues"),
            "remaining_issues": data.get("remaining_issues"),
            "patch_summary": data.get("patch_summary"),
            "content": data.get("content"),
        }
    
    def _format_finding_markdown(self, finding: Dict[str, Any]) -> str:
        lines = []
        lines.append(f"## {finding.get('rule_name')} ({finding.get('severity', '').upper()})")
        lines.append("")
        lines.append(f"- **Scanner:** {finding.get('scanner')}")
        lines.append(f"- **Rule ID:** {finding.get('rule_id')}")
        lines.append(f"- **File:** {finding.get('file_path')}:{finding.get('line_start')}")
        if finding.get("cwe_id"):
            lines.append(f"- **CWE:** {finding.get('cwe_id')}")
        if finding.get("owasp_category"):
            lines.append(f"- **OWASP:** {finding.get('owasp_category')}")
        lines.append(f"- **Status:** {finding.get('status')}")
        lines.append("")
        lines.append(f"**Description:** {finding.get('message')}")
        lines.append("")
        
        if finding.get("ai_explanation"):
            lines.append("**AI Explanation:**")
            lines.append(finding.get("ai_explanation"))
            lines.append("")
        
        if finding.get("code_snippet"):
            lines.append("**Code Snippet:**")
            lines.append("```")
            lines.append(finding.get("code_snippet"))
            lines.append("```")
            lines.append("")
        
        return "\n".join(lines)