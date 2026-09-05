from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, HttpUrl, ConfigDict
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    SECURITY_ENGINEER = "security_engineer"
    VIEWER = "viewer"


class RepositoryStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    CLONED = "cloned"
    SCANNING = "scanning"
    SCANNED = "scanned"
    PATCHING = "patching"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanType(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    PR_CHECK = "pr_check"
    MANUAL = "manual"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingStatus(str, Enum):
    OPEN = "open"
    FIXED = "fixed"
    FALSE_POSITIVE = "false_positive"
    WONT_FIX = "wont_fix"
    IGNORED = "ignored"
    IN_PROGRESS = "in_progress"


class PatchStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    GENERATED = "generated"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    REJECTED = "rejected"


class TestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class ReportFormat(str, Enum):
    MARKDOWN = "markdown"
    PDF = "pdf"
    JSON = "json"
    HTML = "html"


class PullRequestStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"
    FAILED = "failed"


class AuditAction(str, Enum):
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


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.DEVELOPER


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    is_superuser: bool
    github_id: Optional[int] = None
    github_login: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None


class UserWithToken(UserResponse):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: UUID
    exp: int
    type: Literal["access", "refresh"] = "access"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RepositoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    full_name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    url: HttpUrl
    clone_url: HttpUrl
    ssh_url: Optional[HttpUrl] = None
    default_branch: str = "main"
    language: Optional[str] = None
    languages: Optional[List[str]] = None
    is_private: bool = False


class RepositoryCreate(BaseModel):
    github_url: HttpUrl = Field(..., description="GitHub repository URL (https://github.com/owner/repo)")
    github_token: Optional[str] = Field(None, description="GitHub personal access token for private repos")


class RepositoryUpdate(BaseModel):
    description: Optional[str] = None
    default_branch: Optional[str] = None
    is_private: Optional[bool] = None


class RepositoryResponse(RepositoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    github_id: Optional[int] = None
    status: RepositoryStatus
    local_path: Optional[str] = None
    last_scan_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class RepositoryListResponse(BaseModel):
    items: List[RepositoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ScanBase(BaseModel):
    scan_type: ScanType = ScanType.FULL
    commit_sha: Optional[str] = Field(None, min_length=40, max_length=40)
    branch: Optional[str] = None
    scanners: Optional[List[str]] = None


class ScanCreate(ScanBase):
    repository_id: UUID


class ScanUpdate(BaseModel):
    status: Optional[ScanStatus] = None
    error_message: Optional[str] = None


class ScanResponse(ScanBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    initiated_by_id: Optional[UUID] = None
    status: ScanStatus
    scanners_used: List[str] = []
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ScanListResponse(BaseModel):
    items: List[ScanResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class FindingBase(BaseModel):
    scanner: str
    rule_id: str
    rule_name: str
    severity: Severity
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    file_path: str
    line_start: int = Field(..., ge=1)
    line_end: Optional[int] = Field(None, ge=1)
    column_start: Optional[int] = None
    column_end: Optional[int] = None
    code_snippet: Optional[str] = None
    message: str
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = {}


class FindingCreate(FindingBase):
    scan_id: UUID


class FindingUpdate(BaseModel):
    status: Optional[FindingStatus] = None
    ai_explanation: Optional[str] = None
    ai_root_cause: Optional[str] = None
    ai_recommended_fix: Optional[str] = None
    ai_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class FindingResponse(FindingBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scan_id: UUID
    status: FindingStatus
    ai_explanation: Optional[str] = None
    ai_root_cause: Optional[str] = None
    ai_recommended_fix: Optional[str] = None
    ai_confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class FindingListResponse(BaseModel):
    items: List[FindingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PatchBase(BaseModel):
    diff: str
    file_path: str
    language: str


class PatchCreate(PatchBase):
    scan_id: UUID
    finding_id: UUID


class PatchUpdate(BaseModel):
    status: Optional[PatchStatus] = None
    diff: Optional[str] = None
    error_message: Optional[str] = None
    verification_result: Optional[Dict[str, Any]] = None


class PatchResponse(PatchBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scan_id: UUID
    finding_id: UUID
    status: PatchStatus
    llm_provider: str
    llm_model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    generation_time_ms: Optional[int] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    verification_result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class PatchAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patch_id: UUID
    attempt_number: int
    diff: str
    test_passed: Optional[bool] = None
    scan_passed: Optional[bool] = None
    findings_before: int = 0
    findings_after: Optional[int] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime


class PatchDetailResponse(PatchResponse):
    patch_attempts: List[PatchAttemptResponse] = []


class TestResultBase(BaseModel):
    test_command: str
    test_framework: Optional[str] = None


class TestResultCreate(TestResultBase):
    scan_id: UUID


class TestResultUpdate(BaseModel):
    status: Optional[TestStatus] = None
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    duration_seconds: Optional[float] = None
    coverage_percent: Optional[float] = None
    tests_run: Optional[int] = None
    tests_passed: Optional[int] = None
    tests_failed: Optional[int] = None
    tests_skipped: Optional[int] = None


class TestResultResponse(TestResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scan_id: UUID
    status: TestStatus
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    duration_seconds: Optional[float] = None
    coverage_percent: Optional[float] = None
    tests_run: Optional[int] = None
    tests_passed: Optional[int] = None
    tests_failed: Optional[int] = None
    tests_skipped: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class SecurityReportBase(BaseModel):
    format: ReportFormat = ReportFormat.MARKDOWN
    title: str


class SecurityReportCreate(SecurityReportBase):
    scan_id: UUID


class SecurityReportUpdate(BaseModel):
    content: Optional[str] = None
    file_path: Optional[str] = None


class SecurityReportResponse(SecurityReportBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scan_id: UUID
    executive_summary: str
    security_score: Optional[float] = None
    risk_score: Optional[float] = None
    severity_distribution: Dict[str, int] = {}
    owasp_mapping: Dict[str, int] = {}
    cwe_mapping: Dict[str, int] = {}
    fixed_issues: int = 0
    remaining_issues: int = 0
    patch_summary: Dict[str, Any] = {}
    content: str
    file_path: Optional[str] = None
    created_at: datetime


class PullRequestBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body: str
    head_branch: str
    base_branch: str = "main"


class PullRequestCreate(PullRequestBase):
    repository_id: UUID
    scan_id: Optional[UUID] = None
    patch_ids: List[UUID] = []


class PullRequestUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    status: Optional[PullRequestStatus] = None


class PullRequestResponse(PullRequestBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    scan_id: Optional[UUID] = None
    github_pr_id: Optional[int] = None
    github_pr_number: Optional[int] = None
    status: PullRequestStatus
    patches_included: List[UUID] = []
    files_changed: int = 0
    additions: int = 0
    deletions: int = 0
    merge_commit_sha: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    merged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    repository_id: Optional[UUID] = None
    scan_id: Optional[UUID] = None
    finding_id: Optional[UUID] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    message: ChatMessage
    sources: List[Dict[str, Any]] = []


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    timestamp: datetime
    services: Dict[str, str]


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class WebhookEvent(BaseModel):
    action: str
    repository: Dict[str, Any]
    sender: Dict[str, Any]
    pull_request: Optional[Dict[str, Any]] = None
    issue: Optional[Dict[str, Any]] = None


# GitHub OAuth schemas
class GitHubAuthUrlResponse(BaseModel):
    auth_url: str


class GitHubCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


class GitHubInstallationResponse(BaseModel):
    id: int
    account: Dict[str, Any]
    repository_selection: str
    permissions: Dict[str, str]
    created_at: str


class GitHubRepositoryResponse(BaseModel):
    id: int
    name: str
    full_name: str
    private: bool
    html_url: str
    clone_url: str
    default_branch: str
    language: Optional[str] = None