from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import subprocess
import json
import os
import structlog
import asyncio
from pathlib import Path

from core.config import settings
from core.logging import get_logger

logger = get_logger("security.scanners")


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Finding:
    scanner: str
    rule_id: str
    rule_name: str
    severity: Severity
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    file_path: str = ""
    line_start: int = 1
    line_end: Optional[int] = None
    column_start: Optional[int] = None
    column_end: Optional[int] = None
    code_snippet: Optional[str] = None
    message: str = ""
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scanner": self.scanner,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "cwe_id": self.cwe_id,
            "owasp_category": self.owasp_category,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "column_start": self.column_start,
            "column_end": self.column_end,
            "code_snippet": self.code_snippet,
            "message": self.message,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }
    
    def fingerprint(self) -> str:
        return f"{self.scanner}:{self.rule_id}:{self.file_path}:{self.line_start}"


class BaseScanner(ABC):
    name: str = "base"
    supported_languages: List[str] = []
    requires_files: List[str] = []
    
    def __init__(self):
        self.timeout = settings.SCAN_TIMEOUT
    
    @abstractmethod
    async def scan(self, path: str, language: Optional[str] = None) -> List[Finding]:
        pass
    
    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                [self.name, "--version"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _run_command(self, cmd: List[str], cwd: str = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
    
    def _map_severity(self, severity: str, scanner: str) -> Severity:
        severity = severity.upper()
        if scanner == "semgrep":
            mapping = {"ERROR": Severity.HIGH, "WARNING": Severity.MEDIUM, "INFO": Severity.LOW}
        elif scanner == "bandit":
            mapping = {"HIGH": Severity.HIGH, "MEDIUM": Severity.MEDIUM, "LOW": Severity.LOW}
        elif scanner == "gitleaks":
            mapping = {"": Severity.HIGH}
        elif scanner == "trivy":
            mapping = {"CRITICAL": Severity.CRITICAL, "HIGH": Severity.HIGH, "MEDIUM": Severity.MEDIUM, "LOW": Severity.LOW}
        elif scanner in ["pip-audit", "npm-audit"]:
            mapping = {"critical": Severity.CRITICAL, "high": Severity.HIGH, "moderate": Severity.MEDIUM, "medium": Severity.MEDIUM, "low": Severity.LOW}
        else:
            mapping = {}
        return mapping.get(severity, Severity.MEDIUM)
    
    def _extract_cwe(self, metadata: Dict[str, Any]) -> Optional[str]:
        cwe = metadata.get("cwe")
        if isinstance(cwe, str) and cwe.startswith("CWE-"):
            return cwe
        if isinstance(cwe, list):
            for item in cwe:
                if isinstance(item, str) and item.startswith("CWE-"):
                    return item
        return None
    
    def _extract_owasp(self, metadata: Dict[str, Any]) -> Optional[str]:
        owasp = metadata.get("owasp")
        if isinstance(owasp, str):
            return owasp
        if isinstance(owasp, list) and owasp:
            return owasp[0]
        return None


class SemgrepScanner(BaseScanner):
    name = "semgrep"
    supported_languages = ["python", "javascript", "typescript", "java", "go", "ruby", "php", "csharp", "c", "cpp", "rust", "swift", "kotlin", "scala"]
    
    async def scan(self, path: str, language: Optional[str] = None) -> List[Finding]:
        findings = []
        config = settings.SEMGREP_CONFIG
        
        cmd = [
            "semgrep", "scan",
            f"--config={config}",
            "--json",
            "--quiet",
            "--timeout=300",
            path
        ]
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self._run_command(cmd))
            
            if result.returncode not in [0, 1]:
                logger.warning("Semgrep returned non-zero exit code", code=result.returncode, stderr=result.stderr[:500])
            
            if result.stdout:
                data = json.loads(result.stdout)
                for item in data.get("results", []):
                    findings.append(Finding(
                        scanner="semgrep",
                        rule_id=item.get("check_id", ""),
                        rule_name=item.get("extra", {}).get("message", ""),
                        severity=self._map_severity(item.get("extra", {}).get("severity", "ERROR"), "semgrep"),
                        cwe_id=self._extract_cwe(item.get("extra", {}).get("metadata", {})),
                        owasp_category=self._extract_owasp(item.get("extra", {}).get("metadata", {})),
                        file_path=item.get("path", ""),
                        line_start=item.get("start", {}).get("line", 1),
                        line_end=item.get("end", {}).get("line"),
                        column_start=item.get("start", {}).get("col"),
                        column_end=item.get("end", {}).get("col"),
                        code_snippet=item.get("extra", {}).get("lines", ""),
                        message=item.get("extra", {}).get("message", ""),
                        confidence=0.8,
                        metadata=item.get("extra", {}).get("metadata", {}),
                    ))
        except subprocess.TimeoutExpired:
            logger.warning("Semgrep scan timeout", path=path)
        except json.JSONDecodeError as e:
            logger.error("Semgrep JSON decode error", error=str(e))
        except Exception as e:
            logger.error("Semgrep scan error", error=str(e))
        
        return findings


class BanditScanner(BaseScanner):
    name = "bandit"
    supported_languages = ["python"]
    
    async def scan(self, path: str, language: Optional[str] = None) -> List[Finding]:
        if language != "python":
            return []
        
        findings = []
        cmd = ["bandit", "-r", path, "-f", "json", "-q"]
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self._run_command(cmd))
            
            if result.stdout:
                data = json.loads(result.stdout)
                for item in data.get("results", []):
                    findings.append(Finding(
                        scanner="bandit",
                        rule_id=item.get("test_id", ""),
                        rule_name=item.get("test_name", ""),
                        severity=self._map_severity(item.get("issue_severity", "MEDIUM"), "bandit"),
                        cwe_id=item.get("issue_cwe", {}).get("id") if item.get("issue_cwe") else None,
                        file_path=item.get("filename", "").replace(path + "/", "").replace(path + "\\", ""),
                        line_start=item.get("line_number", 1),
                        line_end=item.get("line_number"),
                        code_snippet=item.get("code", ""),
                        message=item.get("issue_text", ""),
                        confidence=self._map_confidence(item.get("issue_confidence", "MEDIUM")),
                        metadata={"more_info": item.get("more_info", "")},
                    ))
        except subprocess.TimeoutExpired:
            logger.warning("Bandit scan timeout", path=path)
        except Exception as e:
            logger.error("Bandit scan error", error=str(e))
        
        return findings
    
    def _map_confidence(self, confidence: str) -> float:
        mapping = {"HIGH": 0.9, "MEDIUM": 0.7, "LOW": 0.5}
        return mapping.get(confidence.upper(), 0.7)


class GitleaksScanner(BaseScanner):
    name = "gitleaks"
    supported_languages = ["all"]
    
    async def scan(self, path: str, language: Optional[str] = None) -> List[Finding]:
        findings = []
        cmd = ["gitleaks", "detect", "--source", path, "--report-format", "json", "--verbose"]
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self._run_command(cmd))
            
            if result.stdout:
                leaks = json.loads(result.stdout)
                for leak in leaks:
                    findings.append(Finding(
                        scanner="gitleaks",
                        rule_id=leak.get("RuleID", ""),
                        rule_name=leak.get("Description", ""),
                        severity=Severity.HIGH,
                        cwe_id="CWE-798",
                        file_path=leak.get("File", "").replace(path + "/", "").replace(path + "\\", ""),
                        line_start=leak.get("StartLine", 1),
                        line_end=leak.get("EndLine"),
                        code_snippet=leak.get("Match", ""),
                        message=f"Secret detected: {leak.get('Description', 'Unknown')}",
                        confidence=0.9,
                        metadata={
                            "commit": leak.get("Commit", ""),
                            "entropy": leak.get("Entropy", 0),
                        },
                    ))
        except subprocess.TimeoutExpired:
            logger.warning("Gitleaks scan timeout", path=path)
        except Exception as e:
            logger.error("Gitleaks scan error", error=str(e))
        
        return findings


class TrivyScanner(BaseScanner):
    name = "trivy"
    supported_languages = ["all"]
    
    async def scan(self, path: str, language: Optional[str] = None) -> List[Finding]:
        findings = []
        severity = settings.TRIVY_SEVERITY
        cmd = ["trivy", "fs", "--format", "json", "--severity", severity, path]
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self._run_command(cmd))
            
            if result.stdout:
                data = json.loads(result.stdout)
                for item in data.get("Results", []):
                    target = item.get("Target", "")
                    for vuln in item.get("Vulnerabilities", []):
                        findings.append(Finding(
                            scanner="trivy",
                            rule_id=vuln.get("VulnerabilityID", ""),
                            rule_name=vuln.get("Title", ""),
                            severity=self._map_severity(vuln.get("Severity", "UNKNOWN"), "trivy"),
                            cwe_id=self._extract_cwe_from_trivy(vuln),
                            file_path=target.replace(path + "/", "").replace(path + "\\", ""),
                            line_start=1,
                            code_snippet="",
                            message=vuln.get("Description", ""),
                            confidence=0.7,
                            metadata={
                                "package": vuln.get("PkgName", ""),
                                "installed_version": vuln.get("InstalledVersion", ""),
                                "fixed_version": vuln.get("FixedVersion", ""),
                                "references": vuln.get("References", []),
                            },
                        ))
        except subprocess.TimeoutExpired:
            logger.warning("Trivy scan timeout", path=path)
        except Exception as e:
            logger.error("Trivy scan error", error=str(e))
        
        return findings
    
    def _extract_cwe_from_trivy(self, vuln: Dict[str, Any]) -> Optional[str]:
        cwe = vuln.get("CWE")
        if isinstance(cwe, str) and cwe.startswith("CWE-"):
            return cwe
        if isinstance(cwe, list):
            for item in cwe:
                if isinstance(item, str) and item.startswith("CWE-"):
                    return item
        return None


class DependencyScanner(BaseScanner):
    name = "dependency"
    supported_languages = ["python", "javascript", "typescript"]
    
    async def scan(self, path: str, language: Optional[str] = None) -> List[Finding]:
        findings = []
        
        if language == "python":
            findings.extend(await self._scan_python(path))
        elif language in ["javascript", "typescript"]:
            findings.extend(await self._scan_javascript(path))
        
        return findings
    
    async def _scan_python(self, path: str) -> List[Finding]:
        findings = []
        req_file = Path(path) / "requirements.txt"
        pyproject = Path(path) / "pyproject.toml"
        setup_py = Path(path) / "setup.py"
        
        if not (req_file.exists() or pyproject.exists() or setup_py.exists()):
            return findings
        
        if req_file.exists():
            cmd = ["pip-audit", "-r", str(req_file), "-f", "json"]
        elif pyproject.exists():
            cmd = ["pip-audit", "--project", path, "-f", "json"]
        else:
            cmd = ["pip-audit", "-r", str(setup_py), "-f", "json"]
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self._run_command(cmd))
            
            if result.stdout:
                data = json.loads(result.stdout)
                for vuln in data.get("vulnerabilities", []):
                    findings.append(Finding(
                        scanner="pip-audit",
                        rule_id=vuln.get("id", ""),
                        rule_name=vuln.get("name", ""),
                        severity=self._map_severity(vuln.get("severity", "UNKNOWN"), "pip-audit"),
                        file_path="requirements.txt" if req_file.exists() else "pyproject.toml",
                        line_start=1,
                        code_snippet="",
                        message=f"Vulnerable dependency: {vuln.get('name', '')} {vuln.get('version', '')}",
                        confidence=0.8,
                        metadata=vuln,
                    ))
        except Exception as e:
            logger.error("pip-audit error", error=str(e))
        
        return findings
    
    async def _scan_javascript(self, path: str) -> List[Finding]:
        findings = []
        pkg_file = Path(path) / "package.json"
        
        if not pkg_file.exists():
            return findings
        
        cmd = ["npm", "audit", "--json"]
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self._run_command(cmd, cwd=path))
            
            if result.stdout:
                data = json.loads(result.stdout)
                for vuln in data.get("vulnerabilities", {}).values():
                    findings.append(Finding(
                        scanner="npm-audit",
                        rule_id=vuln.get("name", ""),
                        rule_name=vuln.get("title", ""),
                        severity=self._map_severity(vuln.get("severity", "unknown"), "npm-audit"),
                        cwe_id=vuln.get("cwe"),
                        file_path="package.json",
                        line_start=1,
                        code_snippet="",
                        message=vuln.get("overview", ""),
                        confidence=0.8,
                        metadata=vuln,
                    ))
        except Exception as e:
            logger.error("npm audit error", error=str(e))
        
        return findings


class ScannerRegistry:
    def __init__(self):
        self.scanners: Dict[str, BaseScanner] = {
            "semgrep": SemgrepScanner(),
            "bandit": BanditScanner(),
            "gitleaks": GitleaksScanner(),
            "trivy": TrivyScanner(),
            "dependency": DependencyScanner(),
        }
    
    def get_scanner(self, name: str) -> Optional[BaseScanner]:
        return self.scanners.get(name)
    
    def get_available_scanners(self, language: Optional[str] = None) -> List[str]:
        available = []
        for name, scanner in self.scanners.items():
            if scanner.is_available():
                if not language or language in scanner.supported_languages or "all" in scanner.supported_languages:
                    available.append(name)
        return available
    
    async def run_scanners(self, path: str, language: Optional[str] = None, scanner_names: Optional[List[str]] = None) -> List[Finding]:
        all_findings = []
        scanners_to_run = scanner_names or self.get_available_scanners(language)
        
        tasks = []
        for name in scanners_to_run:
            scanner = self.get_scanner(name)
            if scanner:
                tasks.append(scanner.scan(path, language))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Scanner failed", scanner=scanners_to_run[i], error=str(result))
            else:
                all_findings.extend(result)
                logger.info("Scanner completed", scanner=scanners_to_run[i], findings=len(result))
        
        return all_findings


scanner_registry = ScannerRegistry()