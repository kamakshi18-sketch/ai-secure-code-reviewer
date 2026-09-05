export type UserRole = 'admin' | 'developer' | 'security_engineer' | 'viewer';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_superuser: boolean;
  github_id?: number;
  github_login?: string;
  created_at: string;
  updated_at: string;
  last_login?: string;
}

export interface Repository {
  id: string;
  owner_id: string;
  github_id?: number;
  name: string;
  full_name: string;
  description?: string;
  url: string;
  clone_url: string;
  ssh_url?: string;
  default_branch: string;
  language?: string;
  languages?: string[];
  is_private: boolean;
  status: RepositoryStatus;
  local_path?: string;
  last_scan_at?: string;
  created_at: string;
  updated_at: string;
}

export type RepositoryStatus = 
  | 'pending' | 'cloning' | 'cloned' 
  | 'scanning' | 'scanned' 
  | 'patching' | 'verifying' 
  | 'completed' | 'failed';

export interface Scan {
  id: string;
  repository_id: string;
  initiated_by_id?: string;
  scan_type: ScanType;
  status: ScanStatus;
  commit_sha?: string;
  branch?: string;
  scanners_used: string[];
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  duration_seconds?: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export type ScanType = 'full' | 'incremental' | 'pr_check' | 'manual';
export type ScanStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface Finding {
  id: string;
  scan_id: string;
  scanner: string;
  rule_id: string;
  rule_name: string;
  severity: Severity;
  status: FindingStatus;
  cwe_id?: string;
  owasp_category?: string;
  file_path: string;
  line_start: number;
  line_end?: number;
  column_start?: number;
  column_end?: number;
  code_snippet?: string;
  message: string;
  confidence?: number;
  metadata: Record<string, any>;
  ai_explanation?: string;
  ai_root_cause?: string;
  ai_recommended_fix?: string;
  ai_confidence?: number;
  created_at: string;
  updated_at: string;
}

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type FindingStatus = 'open' | 'fixed' | 'false_positive' | 'wont_fix' | 'ignored' | 'in_progress';

export interface Patch {
  id: string;
  scan_id: string;
  finding_id: string;
  status: PatchStatus;
  diff: string;
  file_path: string;
  language: string;
  llm_provider: string;
  llm_model: string;
  prompt_tokens?: number;
  completion_tokens?: number;
  generation_time_ms?: number;
  retry_count: number;
  error_message?: string;
  verification_result?: PatchVerificationResult;
  created_at: string;
  updated_at: string;
  patch_attempts?: PatchAttempt[];
}

export type PatchStatus = 'pending' | 'generating' | 'generated' | 'applying' | 'applied' | 'failed' | 'rejected';

export interface PatchAttempt {
  id: string;
  patch_id: string;
  attempt_number: number;
  diff: string;
  test_passed?: boolean;
  scan_passed?: boolean;
  findings_before: number;
  findings_after?: number;
  error_message?: string;
  duration_ms?: number;
  created_at: string;
}

export interface PatchVerificationResult {
  test_passed: boolean;
  scan_passed: boolean;
  findings_before: number;
  findings_after: number;
  verified_at: string;
}

export interface SecurityReport {
  id: string;
  scan_id: string;
  format: ReportFormat;
  title: string;
  executive_summary: string;
  security_score?: number;
  risk_score?: number;
  severity_distribution: Record<string, number>;
  owasp_mapping: Record<string, number>;
  cwe_mapping: Record<string, number>;
  fixed_issues: number;
  remaining_issues: number;
  patch_summary: Record<string, any>;
  content: string;
  file_path?: string;
  created_at: string;
}

export type ReportFormat = 'markdown' | 'pdf' | 'json' | 'html';

export interface PullRequest {
  id: string;
  repository_id: string;
  scan_id?: string;
  github_pr_id?: number;
  github_pr_number?: number;
  title: string;
  body: string;
  head_branch: string;
  base_branch: string;
  status: PullRequestStatus;
  patches_included: string[];
  files_changed: number;
  additions: number;
  deletions: number;
  merge_commit_sha?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
  merged_at?: string;
  closed_at?: string;
}

export type PullRequestStatus = 'draft' | 'open' | 'merged' | 'closed' | 'failed';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  repository_id?: string;
  scan_id?: string;
  finding_id?: string;
  context?: Record<string, any>;
}

export interface ChatResponse {
  message: ChatMessage;
  sources: Array<{ source: string; content: string }>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  timestamp: string;
  services: Record<string, string>;
}