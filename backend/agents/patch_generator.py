from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage
import structlog
import re

from agents.base import BaseAgent
from rag.engine import RAGEngine
from core.config import settings

logger = structlog.get_logger("agents.patch_generator")


class PatchGeneratorAgent(BaseAgent):
    def __init__(self, rag_engine: RAGEngine = None):
        super().__init__(rag_engine)
        self.system_prompt = """You are a Senior Secure Code Engineer specializing in generating minimal, secure patches.
Your task is to generate a unified diff patch that fixes a specific security vulnerability.

CRITICAL RULES:
1. Generate MINIMAL patches - only change what's necessary to fix the vulnerability
2. Maintain existing code style, formatting, and comments
3. Use the same indentation and conventions as the surrounding code
4. Do NOT rewrite entire functions or files
5. Generate valid unified diff format
6. The patch must be directly applicable with `git apply`
7. Focus on the specific vulnerability, not general improvements
8. Use secure coding patterns from the retrieved knowledge
9. Preserve all existing functionality
10. Add comments only if they clarify the security fix

PATCH FORMAT:
```diff
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -line_start,context_lines +line_start,context_lines @@
 context line
-old vulnerable line
+new secure line
 context line
```

The patch should fix the specific vulnerability identified in the finding."""

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        finding = input_data.get("finding")
        source_code = input_data.get("source_code", "")
        file_path = input_data.get("file_path", "")
        language = input_data.get("language", "python")
        
        return await self.generate_patch(finding, source_code, file_path, language)
    
    async def generate_patch(
        self,
        finding: Dict[str, Any],
        source_code: str,
        file_path: str,
        language: str
    ) -> Dict[str, Any]:
        rag_results = await self.rag_engine.query(
            f"{finding['rule_name']} secure fix {language} patch example",
            top_k=5
        )
        
        context = self._build_patch_context(finding, source_code, file_path, language, rag_results)
        
        messages = [
            SystemMessage(content=self.system_prompt),
            SystemMessage(content=context),
            HumanMessage(content=f"Generate a minimal unified diff patch to fix this {finding['severity']} vulnerability.")
        ]
        
        response = await self._call_llm(messages, temperature=0.0)
        
        diff = self._extract_diff(response)
        
        if not diff:
            diff = self._generate_fallback_patch(finding, source_code, file_path, language)
        
        return {
            "diff": diff,
            "provider": settings.DEFAULT_LLM_PROVIDER,
            "model": settings.DEFAULT_MODEL,
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }
    
    def _build_patch_context(
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
Vulnerability to Fix:
- Scanner: {finding.get('scanner', 'Unknown')}
- Rule: {finding.get('rule_name', 'Unknown')} ({finding.get('rule_id', 'Unknown')})
- Severity: {finding.get('severity', 'Unknown')}
- File: {file_path}
- Line: {line_start}
- Message: {finding.get('message', 'No message')}
- CWE: {finding.get('cwe_id', 'Not specified')}
- OWASP: {finding.get('owasp_category', 'Not specified')}

Source Code Context (lines {context_start+1}-{context_end}):
```{language}
{context_code}
```

Full File (for reference):
```{language}
{source_code[:5000]}
```

Secure Coding References:
{rag_context}

Language: {language}
"""
    
    def _extract_diff(self, response: str) -> str:
        diff_pattern = r'```diff\n(.*?)\n```'
        matches = re.findall(diff_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        diff_pattern2 = r'(--- a/.*?\n(?:\+\+\+ b/.*?\n)?(?:@@.*?@@.*?\n(?: .*?\n|-.*?\n|\+.*?\n)*))'
        matches2 = re.findall(diff_pattern2, response, re.DOTALL)
        
        if matches2:
            return matches2[0].strip()
        
        return ""
    
    def _generate_fallback_patch(
        self,
        finding: Dict[str, Any],
        source_code: str,
        file_path: str,
        language: str
    ) -> str:
        rule_id = finding.get('rule_id', '').lower()
        line_start = finding.get('line_start', 1)
        
        if 'sql' in rule_id or 'injection' in finding.get('message', '').lower():
            return self._sql_injection_fallback(finding, source_code, file_path, line_start)
        elif 'xss' in rule_id or 'cross.site' in finding.get('message', '').lower():
            return self._xss_fallback(finding, source_code, file_path, line_start)
        elif 'secret' in rule_id or 'credential' in finding.get('message', '').lower():
            return self._secret_fallback(finding, source_code, file_path, line_start)
        elif 'path' in rule_id or 'traversal' in finding.get('message', '').lower():
            return self._path_traversal_fallback(finding, source_code, file_path, line_start)
        elif 'command' in rule_id or 'injection' in finding.get('message', '').lower():
            return self._command_injection_fallback(finding, source_code, file_path, line_start)
        
        return f"""--- a/{file_path}
+++ b/{file_path}
@@ -{max(1, line_start-2)},5 +{max(1, line_start-2)},5 @@
 context line
-vulnerable code
+// TODO: Fix {finding.get('rule_name', 'vulnerability')} - manual review required
 context line
"""
    
    def _sql_injection_fallback(self, finding: Dict, source_code: str, file_path: str, line: int) -> str:
        return f"""--- a/{file_path}
+++ b/{file_path}
@@ -{max(1, line-2)},7 +{max(1, line-2)},7 @@
     # Vulnerable SQL query
-    query = f"SELECT * FROM users WHERE id = {user_input}"
+    query = "SELECT * FROM users WHERE id = %s"
     cursor.execute(query, (user_input,))
     # Fixed: Using parameterized query to prevent SQL injection
 """
    
    def _xss_fallback(self, finding: Dict, source_code: str, file_path: str, line: int) -> str:
        return f"""--- a/{file_path}
+++ b/{file_path}
@@ -{max(1, line-2)},7 +{max(1, line-2)},7 @@
     # Vulnerable XSS output
-    return render_template_string(f"<div>{user_input}</div>")
+    return render_template_string("<div>{{ user_input | e }}</div>")
     # Fixed: Using template auto-escaping to prevent XSS
 """
    
    def _secret_fallback(self, finding: Dict, source_code: str, file_path: str, line: int) -> str:
        return f"""--- a/{file_path}
+++ b/{file_path}
@@ -{max(1, line-2)},5 +{max(1, line-2)},5 @@
     # Hardcoded secret
-    api_key = "sk_live_abcdef123456"
+    api_key = os.environ.get("API_KEY")
     # Fixed: Using environment variable instead of hardcoded secret
 """
    
    def _path_traversal_fallback(self, finding: Dict, source_code: str, file_path: str, line: int) -> str:
        return f"""--- a/{file_path}
+++ b/{file_path}
@@ -{max(1, line-2)},7 +{max(1, line-2)},7 @@
     # Vulnerable path traversal
-    file_path = os.path.join(base_dir, user_input)
+    file_path = os.path.join(base_dir, os.path.basename(user_input))
     # Fixed: Using basename to prevent directory traversal
 """
    
    def _command_injection_fallback(self, finding: Dict, source_code: str, file_path: str, line: int) -> str:
        return f"""--- a/{file_path}
+++ b/{file_path}
@@ -{max(1, line-2)},7 +{max(1, line-2)},7 @@
     # Vulnerable command injection
-    subprocess.run(f"ping {user_input}", shell=True)
+    subprocess.run(["ping", user_input], shell=False)
     # Fixed: Using subprocess with list args and shell=False
 """