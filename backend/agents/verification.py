import structlog
from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage

from agents.base import BaseAgent
from rag.engine import RAGEngine

logger = structlog.get_logger("agents.verification")


class VerificationAgent(BaseAgent):
    def __init__(self, rag_engine: RAGEngine = None):
        super().__init__(rag_engine)
        self.system_prompt = """You are a Senior Software Engineer specializing in patch verification and test analysis.
Your task is to analyze patch verification results and provide:
1. Test failure analysis
2. Root cause of test failures
3. Security scan regression analysis
4. Recommendations for fixing failed patches
5. Alternative approaches

Guidelines:
- Focus on the specific failure, not general code quality
- Provide actionable recommendations for fixing the patch
- Consider both test failures and security regressions
- Suggest minimal changes to make the patch pass
- Never suggest weakening security to pass tests"""

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action", "analyze_failure")
        
        if action == "analyze_failure":
            return await self.analyze_failure(input_data)
        elif action == "analyze_test_failure":
            return await self.analyze_test_failure(input_data)
        elif action == "analyze_scan_regression":
            return await self.analyze_scan_regression(input_data)
        else:
            return await self.analyze_failure(input_data)
    
    async def analyze_failure(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        patch = input_data.get("patch")
        test_results = input_data.get("test_results", {})
        scan_results = input_data.get("scan_results", {})
        original_finding = input_data.get("original_finding")
        
        rag_results = await self.rag_engine.query(
            f"test failure analysis patch verification secure coding",
            top_k=3
        )
        
        context = self._build_failure_context(patch, test_results, scan_results, original_finding, rag_results)
        
        messages = [
            SystemMessage(content=self.system_prompt),
            SystemMessage(content=context),
            HumanMessage(content="Analyze this patch verification failure and provide recommendations for fixing it.")
        ]
        
        response = await self._call_llm(messages)
        
        return {
            "analysis": response,
            "recommendations": self._extract_recommendations(response),
            "confidence": 0.8,
            "sources": [{"source": r["metadata"].get("source"), "content": r["content"][:200]} for r in rag_results]
        }
    
    async def analyze_test_failure(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        test_output = input_data.get("test_output", "")
        test_framework = input_data.get("test_framework", "unknown")
        patch = input_data.get("patch")
        
        rag_results = await self.rag_engine.query(
            f"{test_framework} test failure analysis patch fix",
            top_k=3
        )
        
        context = f"""
Test Framework: {test_framework}
Test Output:
{test_output}

Patch Diff:
{patch.get('diff', '') if patch else 'Not provided'}

Relevant Knowledge:
{chr(10).join([r['content'][:500] for r in rag_results])}
"""
        
        messages = [
            SystemMessage(content="""You are a Senior Developer analyzing test failures.
Identify the root cause of test failures related to security patches.
Provide specific fixes that maintain security while passing tests."""),
            SystemMessage(content=context),
            HumanMessage(content="Analyze this test failure and provide a fix that maintains security.")
        ]
        
        response = await self._call_llm(messages)
        
        return {
            "analysis": response,
            "suggested_fix": self._extract_suggested_fix(response),
            "confidence": 0.75,
        }
    
    async def analyze_scan_regression(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        new_findings = input_data.get("new_findings", [])
        fixed_finding = input_data.get("fixed_finding")
        patch = input_data.get("patch")
        
        rag_results = await self.rag_engine.query(
            f"security regression analysis new vulnerabilities introduced patch",
            top_k=3
        )
        
        context = f"""
Original Fixed Finding: {fixed_finding.get('rule_name') if fixed_finding else 'Unknown'}

New Findings Introduced:
{chr(10).join([f'- {f.get("rule_name")}: {f.get("message")} ({f.get("severity")})' for f in new_findings])}

Patch Diff:
{patch.get('diff', '') if patch else 'Not provided'}

Relevant Knowledge:
{chr(10).join([r['content'][:500] for r in rag_results])}
"""
        
        messages = [
            SystemMessage(content="""You are a Security Engineer analyzing security regressions.
Determine if new vulnerabilities were introduced by the patch.
Provide recommendations to fix the regression while maintaining the original fix."""),
            SystemMessage(content=context),
            HumanMessage(content="Analyze this security regression and provide recommendations.")
        ]
        
        response = await self._call_llm(messages)
        
        return {
            "analysis": response,
            "regression_confirmed": len(new_findings) > 0,
            "recommendations": self._extract_recommendations(response),
        }
    
    def _build_failure_context(
        self,
        patch: Dict[str, Any],
        test_results: Dict[str, Any],
        scan_results: Dict[str, Any],
        original_finding: Dict[str, Any],
        rag_results: List[Dict[str, Any]]
    ) -> str:
        rag_context = "\n\n".join([r['content'][:500] for r in rag_results])
        
        test_passed = test_results.get("test_passed", False)
        scan_passed = scan_results.get("scan_passed", False)
        
        return f"""
Original Finding: {original_finding.get('rule_name') if original_finding else 'Unknown'}
- Severity: {original_finding.get('severity') if original_finding else 'Unknown'}
- File: {original_finding.get('file_path') if original_finding else 'Unknown'}

Patch Diff:
{patch.get('diff', '') if patch else 'Not provided'}

Test Results:
- Passed: {test_passed}
- Commands Run: {len(test_results.get('commands', []))}
- Failures: {chr(10).join([f'  - {c.get("command")}: {c.get("stderr")[:200]}' for c in test_results.get('commands', []) if c.get('exit_code') != 0])}

Security Re-scan Results:
- Passed: {scan_passed}
- Findings Before: {scan_results.get('findings_before', 0)}
- Findings After: {scan_results.get('findings_after', 0)}
- New Findings: {chr(10).join([f'  - {f.get("rule_name")} ({f.get("severity")})' for f in scan_results.get('new_findings', [])])}

Relevant Knowledge:
{rag_context}
"""
    
    def _extract_recommendations(self, response: str) -> List[str]:
        recommendations = []
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('- ') or line.startswith('* ') or line.startswith('1.') or line.startswith('2.'):
                recommendations.append(line)
        return recommendations
    
    def _extract_suggested_fix(self, response: str) -> str:
        lines = response.split('\n')
        in_code_block = False
        fix_lines = []
        
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                fix_lines.append(line)
        
        return '\n'.join(fix_lines) if fix_lines else response[:500]