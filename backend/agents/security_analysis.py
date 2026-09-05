import structlog
from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage

from agents.base import BaseAgent
from rag.engine import RAGEngine

logger = structlog.get_logger("agents.security_analysis")


class SecurityAnalysisAgent(BaseAgent):
    def __init__(self, rag_engine: RAGEngine = None):
        super().__init__(rag_engine)
        self.system_prompt = """You are a Senior Security Engineer specializing in code vulnerability analysis.
Your task is to analyze security findings from static analysis tools and provide:
1. Root cause analysis
2. Severity assessment with justification
3. OWASP category mapping
4. CWE identification
5. Business impact assessment
6. Likelihood of exploitation
7. Confidence in the finding
8. Recommended fix with explanation
9. Code explanation for developers

Guidelines:
- Base your analysis on the scanner output and retrieved secure coding practices
- Never hallucinate vulnerabilities or fixes
- Always cite sources from the RAG system
- Provide actionable, specific recommendations
- Explain technical concepts clearly for developers
- Consider the programming language and framework context"""

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        finding = input_data.get("finding")
        source_code = input_data.get("source_code", "")
        file_path = input_data.get("file_path", "")
        language = input_data.get("language", "")
        question = input_data.get("question")
        
        if question:
            return await self.explain_finding(finding, question, input_data.get("context", {}))
        
        return await self.analyze_finding(finding, source_code, file_path, language)
    
    async def analyze_finding(
        self,
        finding: Dict[str, Any],
        source_code: str,
        file_path: str,
        language: str
    ) -> Dict[str, Any]:
        rag_results = await self.rag_engine.query(
            f"{finding['rule_name']} {finding['message']} {language} secure coding",
            top_k=5
        )
        
        context = self._build_context(finding, source_code, file_path, language, rag_results)
        
        messages = [
            SystemMessage(content=self.system_prompt),
            SystemMessage(content=context),
            HumanMessage(content=f"Analyze this {finding['severity']} severity finding and provide comprehensive security analysis.")
        ]
        
        response = await self._call_llm(messages)
        
        return self._parse_analysis(response, rag_results)
    
    async def explain_finding(
        self,
        finding: Dict[str, Any],
        question: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        rag_results = await self.rag_engine.query(
            f"{question} {finding.get('rule_name', '')} {finding.get('message', '')}",
            top_k=5
        )
        
        context_str = self._build_explanation_context(finding, context, rag_results)
        
        messages = [
            SystemMessage(content="""You are a Security Engineer explaining vulnerabilities to developers.
Provide clear, educational explanations with code examples.
Reference OWASP, CWE, and secure coding standards.
Be specific to the programming language and framework."""),
            SystemMessage(content=context_str),
            HumanMessage(content=question)
        ]
        
        response = await self._call_llm(messages)
        
        return {
            "answer": response,
            "sources": [{"source": r["metadata"].get("source"), "content": r["content"][:200]} for r in rag_results]
        }
    
    def _build_context(
        self,
        finding: Dict[str, Any],
        source_code: str,
        file_path: str,
        language: str,
        rag_results: List[Dict[str, Any]]
    ) -> str:
        rag_context = "\n\n".join([
            f"Source: {r['metadata'].get('source', 'Unknown')}\n{r['content']}"
            for r in rag_results
        ])
        
        lines = source_code.split('\n')
        line_start = finding.get('line_start', 1)
        context_start = max(0, line_start - 10)
        context_end = min(len(lines), line_start + 10)
        context_code = '\n'.join(lines[context_start:context_end])
        
        return f"""
Finding Details:
- Scanner: {finding.get('scanner', 'Unknown')}
- Rule ID: {finding.get('rule_id', 'Unknown')}
- Rule Name: {finding.get('rule_name', 'Unknown')}
- Severity: {finding.get('severity', 'Unknown')}
- File: {file_path}
- Line: {line_start}
- Message: {finding.get('message', 'No message')}
- CWE: {finding.get('cwe_id', 'Not specified')}
- OWASP: {finding.get('owasp_category', 'Not specified')}
- Confidence: {finding.get('confidence', 'Not specified')}

Source Code Context (lines {context_start+1}-{context_end}):
```{language}
{context_code}
```

Full File (for reference):
```{language}
{source_code[:5000]}
```

Relevant Security Knowledge:
{rag_context}
"""
    
    def _build_explanation_context(
        self,
        finding: Dict[str, Any],
        context: Dict[str, Any],
        rag_results: List[Dict[str, Any]]
    ) -> str:
        rag_context = "\n\n".join([
            f"Source: {r['metadata'].get('source', 'Unknown')}\n{r['content']}"
            for r in rag_results
        ])
        
        return f"""
Finding to Explain:
- Rule: {finding.get('rule_name', 'Unknown')} ({finding.get('rule_id', 'Unknown')})
- Severity: {finding.get('severity', 'Unknown')}
- File: {finding.get('file_path', 'Unknown')}:{finding.get('line_start', 'Unknown')}
- Message: {finding.get('message', 'No message')}
- CWE: {finding.get('cwe_id', 'Not specified')}
- OWASP: {finding.get('owasp_category', 'Not specified')}

Repository Context:
- Language: {context.get('language', 'Unknown')}
- Repository: {context.get('repository', 'Unknown')}

Relevant Security Knowledge:
{rag_context}
"""
    
    def _parse_analysis(self, response: str, rag_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "explanation": response,
            "root_cause": "Extracted from analysis",
            "recommended_fix": "Extracted from analysis",
            "confidence": 0.85,
            "sources": [{"source": r["metadata"].get("source"), "content": r["content"][:200]} for r in rag_results]
        }