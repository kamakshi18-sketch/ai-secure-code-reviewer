import enum
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Text, Integer, DateTime, ForeignKey, Enum, Index, JSON, Boolean, Float, LargeBinary
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.session import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    SECURITY_ENGINEER = "security_engineer"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.DEVELOPER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    github_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, index=True, nullable=True)
    github_login: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    github_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    github_refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    github_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    repositories: Mapped[List["Repository"]] = relationship("Repository", back_populates="owner")
    scans: Mapped[List["Scan"]] = relationship("Scan", back_populates="initiated_by")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class RepositoryStatus(str, enum.Enum):
    PENDING = "pending"
    CLONING = "cloning"
    CLONED = "cloned"
    SCANNING = "scanning"
    SCANNED = "scanned"
    PATCHING = "patching"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    github_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    clone_url: Mapped[str] = mapped_column(String(500), nullable=False)
    ssh_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    default_branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    languages: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[RepositoryStatus] = mapped_column(Enum(RepositoryStatus), default=RepositoryStatus.PENDING, nullable=False)
    local_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    last_scan_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    github_installation_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner: Mapped["User"] = relationship("User", back_populates="repositories")
    scans: Mapped[List["Scan"]] = relationship("Scan", back_populates="repository", cascade="all, delete-orphan")
    pull_requests: Mapped[List["PullRequest"]] = relationship("PullRequest", back_populates="repository", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_repositories_owner_status", "owner_id", "status"),
        Index("ix_repositories_full_name", "full_name"),
    )

    def __repr__(self) -> str:
        return f"<Repository(id={self.id}, full_name={self.full_name}, status={self.status})>"


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanType(str, enum.Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    PR_CHECK = "pr_check"
    MANUAL = "manual"


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    initiated_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    scan_type: Mapped[ScanType] = mapped_column(Enum(ScanType), default=ScanType.FULL, nullable=False)
    status: Mapped[ScanStatus] = mapped_column(Enum(ScanStatus), default=ScanStatus.PENDING, nullable=False)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    branch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    scanners_used: Mapped[List[str]] = mapped_column(ARRAY(String), default=[], nullable=False)
    total_findings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    high_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    medium_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    info_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="scans")
    initiated_by: Mapped[Optional["User"]] = relationship("User", back_populates="scans")
    findings: Mapped[List["Finding"]] = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")
    patches: Mapped[List["Patch"]] = relationship("Patch", back_populates="scan", cascade="all, delete-orphan")
    test_results: Mapped[List["TestResult"]] = relationship("TestResult", back_populates="scan", cascade="all, delete-orphan")
    security_reports: Mapped[List["SecurityReport"]] = relationship("SecurityReport", back_populates="scan", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_scans_repository_status", "repository_id", "status"),
        Index("ix_scans_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Scan(id={self.id}, repository_id={self.repository_id}, status={self.status})>"


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingStatus(str, enum.Enum):
    OPEN = "open"
    FIXED = "fixed"
    FALSE_POSITIVE = "false_positive"
    WONT_FIX = "wont_fix"
    IGNORED = "ignored"
    IN_PROGRESS = "in_progress"


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    scanner: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), nullable=False, index=True)
    status: Mapped[FindingStatus] = mapped_column(Enum(FindingStatus), default=FindingStatus.OPEN, nullable=False, index=True)
    cwe_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    owasp_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    line_start: Mapped[int] = mapped_column(Integer, nullable=False)
    line_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    column_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    column_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    code_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ai_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_recommended_fix: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    scan: Mapped["Scan"] = relationship("Scan", back_populates="findings")
    patches: Mapped[List["Patch"]] = relationship("Patch", back_populates="finding", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_findings_scan_severity", "scan_id", "severity"),
        Index("ix_findings_file_path", "file_path"),
        Index("ix_findings_rule_id", "rule_id"),
    )

    def __repr__(self) -> str:
        return f"<Finding(id={self.id}, rule={self.rule_id}, severity={self.severity}, file={self.file_path})>"
    
    def fingerprint(self) -> str:
        return f"{self.scanner}:{self.rule_id}:{self.file_path}:{self.line_start}"


class PatchStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    GENERATED = "generated"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    REJECTED = "rejected"


class Patch(Base):
    __tablename__ = "patches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[PatchStatus] = mapped_column(Enum(PatchStatus), default=PatchStatus.PENDING, nullable=False, index=True)
    diff: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    generation_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    scan: Mapped["Scan"] = relationship("Scan", back_populates="patches")
    finding: Mapped["Finding"] = relationship("Finding", back_populates="patches")
    patch_attempts: Mapped[List["PatchAttempt"]] = relationship("PatchAttempt", back_populates="patch", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Patch(id={self.id}, finding_id={self.finding_id}, status={self.status})>"


class PatchAttempt(Base):
    __tablename__ = "patch_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patches.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    diff: Mapped[str] = mapped_column(Text, nullable=False)
    test_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    scan_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    findings_before: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    findings_after: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    patch: Mapped["Patch"] = relationship("Patch", back_populates="patch_attempts")

    def __repr__(self) -> str:
        return f"<PatchAttempt(id={self.id}, patch_id={self.patch_id}, attempt={self.attempt_number})>"


class TestStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    test_command: Mapped[str] = mapped_column(String(500), nullable=False)
    test_framework: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[TestStatus] = mapped_column(Enum(TestStatus), default=TestStatus.PENDING, nullable=False)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coverage_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tests_run: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tests_passed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tests_failed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tests_skipped: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    scan: Mapped["Scan"] = relationship("Scan", back_populates="test_results")

    def __repr__(self) -> str:
        return f"<TestResult(id={self.id}, scan_id={self.scan_id}, status={self.status})>"


class ReportFormat(str, enum.Enum):
    MARKDOWN = "markdown"
    PDF = "pdf"
    JSON = "json"
    HTML = "html"


class SecurityReport(Base):
    __tablename__ = "security_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    format: Mapped[ReportFormat] = mapped_column(Enum(ReportFormat), default=ReportFormat.MARKDOWN, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    security_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    severity_distribution: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    owasp_mapping: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    cwe_mapping: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    fixed_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    remaining_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    patch_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    scan: Mapped["Scan"] = relationship("Scan", back_populates="security_reports")

    def __repr__(self) -> str:
        return f"<SecurityReport(id={self.id}, scan_id={self.scan_id}, format={self.format})>"


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[List[float]] = mapped_column(ARRAY(Float), nullable=False)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_embeddings_source_source_id", "source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<Embedding(id={self.id}, source={self.source}, source_id={self.source_id})>"


class PullRequestStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"
    FAILED = "failed"


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="SET NULL"), nullable=True)
    github_pr_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, index=True, nullable=True)
    github_pr_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    head_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    base_branch: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    status: Mapped[PullRequestStatus] = mapped_column(Enum(PullRequestStatus), default=PullRequestStatus.DRAFT, nullable=False)
    patches_included: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=[], nullable=False)
    files_changed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    additions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deletions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    merge_commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    merged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="pull_requests")
    scan: Mapped[Optional["Scan"]] = relationship("Scan")

    def __repr__(self) -> str:
        return f"<PullRequest(id={self.id}, pr_number={self.github_pr_number}, status={self.status})>"


class AuditAction(str, enum.Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    REPOSITORY_CREATE = "repository_create"
    REPOSITORY_DELETE = "repository_delete"
    SCAN_START = "scan_start"
    SCAN_COMPLETE = "scan_complete"
    PATCH_GENERATE = "patch_generate"
    PATCH_APPLY = "patch_apply"
    PATCH_VERIFY = "patch_verify"
    PR_CREATE = "pr_create"
    PR_MERGE = "pr_merge"
    SETTINGS_CHANGE = "settings_change"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, resource={self.resource_type})>"