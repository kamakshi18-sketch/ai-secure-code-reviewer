from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass
import structlog

from core.logging import get_logger
from security.scanners import Finding, Severity

logger = get_logger("security.aggregator")


@dataclass
class AggregatedFinding:
    fingerprint: str
    scanners: List[str]
    rule_ids: Dict[str, str]
    rule_names: Dict[str, str]
    severity: Severity
    max_severity: Severity
    file_path: str
    line_start: int
    line_end: Optional[int]
    messages: Dict[str, str]
    code_snippets: Dict[str, str]
    cwe_ids: Dict[str, Optional[str]]
    owasp_categories: Dict[str, Optional[str]]
    confidence: Dict[str, Optional[float]]
    metadata: Dict[str, Dict[str, Any]]
    is_duplicate: bool = False
    primary_scanner: str = ""
    
    def to_finding(self) -> Finding:
        return Finding(
            scanner=self.primary_scanner,
            rule_id=self.rule_ids.get(self.primary_scanner, ""),
            rule_name=self.rule_names.get(self.primary_scanner, ""),
            severity=self.max_severity,
            cwe_id=self.cwe_ids.get(self.primary_scanner),
            owasp_category=self.owasp_categories.get(self.primary_scanner),
            file_path=self.file_path,
            line_start=self.line_start,
            line_end=self.line_end,
            code_snippet=self.code_snippets.get(self.primary_scanner),
            message=self.messages.get(self.primary_scanner, ""),
            confidence=self.confidence.get(self.primary_scanner),
            metadata={
                "aggregated_from": self.scanners,
                "all_rule_ids": self.rule_ids,
                "all_rule_names": self.rule_names,
                "all_severities": {s: self.severity.value for s in self.scanners},
                "all_messages": self.messages,
                "all_cwe_ids": self.cwe_ids,
                "all_owasp_categories": self.owasp_categories,
            }
        )


class FindingAggregator:
    SEVERITY_ORDER = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
    
    def __init__(self):
        self.similarity_threshold = 0.8
    
    def aggregate(self, findings: List[Finding]) -> List[AggregatedFinding]:
        groups = self._group_by_location(findings)
        
        aggregated = []
        for group in groups.values():
            if len(group) == 1:
                agg = self._create_aggregated(group[0])
                agg.is_duplicate = False
            else:
                agg = self._merge_findings(group)
                agg.is_duplicate = True
            aggregated.append(agg)
        
        return aggregated
    
    def _group_by_location(self, findings: List[Finding]) -> Dict[str, List[Finding]]:
        groups = defaultdict(list)
        
        for finding in findings:
            key = f"{finding.file_path}:{finding.line_start}"
            groups[key].append(finding)
        
        return groups
    
    def _create_aggregated(self, finding: Finding) -> AggregatedFinding:
        return AggregatedFinding(
            fingerprint=finding.fingerprint(),
            scanners=[finding.scanner],
            rule_ids={finding.scanner: finding.rule_id},
            rule_names={finding.scanner: finding.rule_name},
            severity=finding.severity,
            max_severity=finding.severity,
            file_path=finding.file_path,
            line_start=finding.line_start,
            line_end=finding.line_end,
            messages={finding.scanner: finding.message},
            code_snippets={finding.scanner: finding.code_snippet},
            cwe_ids={finding.scanner: finding.cwe_id},
            owasp_categories={finding.scanner: finding.owasp_category},
            confidence={finding.scanner: finding.confidence},
            metadata={finding.scanner: finding.metadata},
            primary_scanner=finding.scanner,
        )
    
    def _merge_findings(self, findings: List[Finding]) -> AggregatedFinding:
        primary = max(findings, key=lambda f: self.SEVERITY_ORDER.index(f.severity))
        
        scanners = []
        rule_ids = {}
        rule_names = {}
        messages = {}
        code_snippets = {}
        cwe_ids = {}
        owasp_categories = {}
        confidence = {}
        metadata = {}
        
        max_severity = primary.severity
        
        for f in findings:
            scanners.append(f.scanner)
            rule_ids[f.scanner] = f.rule_id
            rule_names[f.scanner] = f.rule_name
            messages[f.scanner] = f.message
            code_snippets[f.scanner] = f.code_snippet
            cwe_ids[f.scanner] = f.cwe_id
            owasp_categories[f.scanner] = f.owasp_category
            confidence[f.scanner] = f.confidence
            metadata[f.scanner] = f.metadata
            
            if self.SEVERITY_ORDER.index(f.severity) < self.SEVERITY_ORDER.index(max_severity):
                max_severity = f.severity
        
        return AggregatedFinding(
            fingerprint=primary.fingerprint(),
            scanners=scanners,
            rule_ids=rule_ids,
            rule_names=rule_names,
            severity=primary.severity,
            max_severity=max_severity,
            file_path=primary.file_path,
            line_start=primary.line_start,
            line_end=primary.line_end,
            messages=messages,
            code_snippets=code_snippets,
            cwe_ids=cwe_ids,
            owasp_categories=owasp_categories,
            confidence=confidence,
            metadata=metadata,
            is_duplicate=True,
            primary_scanner=primary.scanner,
        )


class FindingCorrelator:
    def __init__(self):
        self.correlation_rules = {
            ("sql", "injection"): ["cwe-89", "a03"],
            ("xss", "cross-site"): ["cwe-79", "a03"],
            ("command", "injection"): ["cwe-78", "a03"],
            ("path", "traversal"): ["cwe-22", "a01"],
            ("secret", "credential"): ["cwe-798", "a02"],
            ("deserialization"): ["cwe-502", "a08"],
            ("ssrf"): ["cwe-918", "a10"],
        }
    
    def correlate(self, findings: List[Finding]) -> Dict[str, List[Finding]]:
        correlated = defaultdict(list)
        
        for finding in findings:
            key = self._get_correlation_key(finding)
            correlated[key].append(finding)
        
        return {k: v for k, v in correlated.items() if len(v) > 1}
    
    def _get_correlation_key(self, finding: Finding) -> str:
        text = f"{finding.rule_name} {finding.message}".lower()
        
        for keywords, tags in self.correlation_rules.items():
            if all(kw in text for kw in keywords):
                return "+".join(tags)
        
        if finding.cwe_id:
            return finding.cwe_id.lower()
        
        return finding.rule_id.lower()


class FindingDeduplicator:
    def __init__(self):
        pass
    
    def deduplicate(self, findings: List[Finding]) -> Tuple[List[Finding], List[Finding]]:
        seen = {}
        unique = []
        duplicates = []
        
        for finding in findings:
            fingerprint = finding.fingerprint()
            
            if fingerprint in seen:
                existing = seen[fingerprint]
                if self._is_more_severe(finding, existing):
                    duplicates.append(existing)
                    seen[fingerprint] = finding
                else:
                    duplicates.append(finding)
            else:
                seen[fingerprint] = finding
                unique.append(finding)
        
        return unique, duplicates
    
    def _is_more_severe(self, f1: Finding, f2: Finding) -> bool:
        severity_order = {
            Severity.CRITICAL: 5,
            Severity.HIGH: 4,
            Severity.MEDIUM: 3,
            Severity.LOW: 2,
            Severity.INFO: 1,
        }
        
        s1 = severity_order.get(f1.severity, 0)
        s2 = severity_order.get(f2.severity, 0)
        
        if s1 != s2:
            return s1 > s2
        
        c1 = f1.confidence or 0
        c2 = f2.confidence or 0
        return c1 > c2


finding_aggregator = FindingAggregator()
finding_correlator = FindingCorrelator()
finding_deduplicator = FindingDeduplicator()