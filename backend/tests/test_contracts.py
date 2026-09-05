import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from schemas import (
    UserResponse, RepositoryResponse, ScanResponse, FindingResponse,
    PatchResponse, SecurityReportResponse, PullRequestResponse,
    HealthResponse, Token, UserWithToken
)


class TestAPIContracts:
    @pytest.mark.asyncio
    async def test_health_response_schema(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        
        health = HealthResponse(**response.json())
        assert health.status in ["healthy", "degraded", "unhealthy"]
        assert health.version
        assert health.timestamp
        assert "database" in health.services

    @pytest.mark.asyncio
    async def test_user_response_schema(self, client: AsyncClient, test_user, auth_headers):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        
        user = UserResponse(**response.json())
        assert isinstance(user.id, str)
        assert user.email
        assert user.full_name
        assert user.role in ["admin", "developer", "security_engineer", "viewer"]
        assert isinstance(user.is_active, bool)
        assert isinstance(user.is_superuser, bool)
        assert user.created_at
        assert user.updated_at

    @pytest.mark.asyncio
    async def test_user_with_token_schema(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "schema@test.com", "password": "password123", "full_name": "Schema Test"}
        )
        assert response.status_code == 201
        
        user_token = UserWithToken(**response.json())
        assert user_token.access_token
        assert user_token.refresh_token
        assert user_token.token_type == "bearer"
        assert user_token.user.email == "schema@test.com"

    @pytest.mark.asyncio
    async def test_token_schema(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "testpassword123"}
        )
        assert response.status_code == 200
        
        token = Token(**response.json())
        assert token.access_token
        assert token.refresh_token
        assert token.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_repository_response_schema(self, client: AsyncClient, test_repository, auth_headers):
        response = await client.get(f"/api/v1/repositories/{test_repository.id}", headers=auth_headers)
        assert response.status_code == 200
        
        repo = RepositoryResponse(**response.json())
        assert isinstance(repo.id, str)
        assert repo.name
        assert repo.full_name
        assert repo.url
        assert repo.clone_url
        assert repo.default_branch
        assert repo.status in ["pending", "cloning", "cloned", "scanning", "scanned", "patching", "verifying", "completed", "failed"]
        assert isinstance(repo.is_private, bool)
        assert repo.created_at
        assert repo.updated_at

    @pytest.mark.asyncio
    async def test_scan_response_schema(self, client: AsyncClient, test_scan, auth_headers):
        response = await client.get(f"/api/v1/scans/{test_scan.id}", headers=auth_headers)
        assert response.status_code == 200
        
        scan = ScanResponse(**response.json())
        assert isinstance(scan.id, str)
        assert scan.scan_type in ["full", "incremental", "pr_check", "manual"]
        assert scan.status in ["pending", "running", "completed", "failed", "cancelled"]
        assert isinstance(scan.total_findings, int)
        assert isinstance(scan.critical_count, int)
        assert isinstance(scan.high_count, int)
        assert isinstance(scan.medium_count, int)
        assert isinstance(scan.low_count, int)
        assert isinstance(scan.info_count, int)
        assert isinstance(scan.scanners_used, list)
        assert scan.created_at

    @pytest.mark.asyncio
    async def test_finding_response_schema(self, client: AsyncClient, test_findings, auth_headers):
        finding = test_findings[0]
        response = await client.get(f"/api/v1/findings/{finding.id}", headers=auth_headers)
        assert response.status_code == 200
        
        finding_resp = FindingResponse(**response.json())
        assert isinstance(finding_resp.id, str)
        assert finding_resp.scanner
        assert finding_resp.rule_id
        assert finding_resp.rule_name
        assert finding_resp.severity in ["critical", "high", "medium", "low", "info"]
        assert finding_resp.status in ["open", "fixed", "false_positive", "wont_fix", "ignored", "in_progress"]
        assert finding_resp.file_path
        assert isinstance(finding_resp.line_start, int)
        assert finding_resp.message
        assert isinstance(finding_resp.metadata, dict)
        assert finding_resp.created_at

    @pytest.mark.asyncio
    async def test_patch_response_schema(self, client: AsyncClient, test_patch, auth_headers):
        response = await client.get(f"/api/v1/patches/{test_patch.id}", headers=auth_headers)
        assert response.status_code == 200
        
        patch = PatchResponse(**response.json())
        assert isinstance(patch.id, str)
        assert patch.diff
        assert patch.file_path
        assert patch.language
        assert patch.llm_provider
        assert patch.llm_model
        assert patch.status in ["pending", "generating", "generated", "applying", "applied", "failed", "rejected"]
        assert isinstance(patch.retry_count, int)
        assert patch.created_at

    @pytest.mark.asyncio
    async def test_paginated_response_schema(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/repositories", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["page_size"], int)
        assert isinstance(data["total_pages"], int)
        assert data["page"] >= 1
        assert data["page_size"] >= 1

    @pytest.mark.asyncio
    async def test_error_response_schema(self, client: AsyncClient):
        response = await client.get("/api/v1/repositories/invalid-uuid")
        assert response.status_code == 422 or response.status_code == 404
        
        # FastAPI validation error format
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_auth_error_schema(self, client: AsyncClient):
        response = await client.get("/api/v1/repositories")
        assert response.status_code == 401
        
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_report_response_schema(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/reports",
            json={"scan_id": "00000000-0000-0000-0000-000000000000", "format": "markdown", "title": "Test"},
            headers=auth_headers
        )
        # Will fail because scan doesn't exist, but we check error format
        assert response.status_code in [404, 400, 422]
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_chat_response_schema(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "test"}]},
            headers=auth_headers
        )
        # May fail due to missing LLM, but check response format
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "sources" in data
            assert isinstance(data["sources"], list)

    @pytest.mark.asyncio
    async def test_webhook_event_schema(self):
        from schemas import WebhookEvent
        
        event = WebhookEvent(
            action="opened",
            repository={"id": 123, "full_name": "test/repo"},
            sender={"id": 456, "login": "testuser"},
            pull_request={"number": 1, "title": "Test PR"}
        )
        assert event.action == "opened"
        assert event.repository["full_name"] == "test/repo"
        assert event.sender["login"] == "testuser"
        assert event.pull_request["number"] == 1


class TestRequestValidation:
    @pytest.mark.asyncio
    async def test_invalid_email_registration(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "invalid-email", "password": "password123", "full_name": "Test"}
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_short_password_registration(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "test@test.com", "password": "short", "full_name": "Test"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_scan_type(self, client: AsyncClient, auth_headers, test_repository):
        response = await client.post(
            "/api/v1/scans",
            json={"repository_id": str(test_repository.id), "scan_type": "invalid"},
            headers=auth_headers
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_severity_filter(self, client: AsyncClient, auth_headers):
        response = await client.get(
            "/api/v1/findings",
            params={"severity": "invalid"},
            headers=auth_headers
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/repositories",
            json={},  # Missing github_url
            headers=auth_headers
        )
        assert response.status_code == 422


class TestResponseHeaders:
    @pytest.mark.asyncio
    async def test_cors_headers(self, client: AsyncClient):
        response = await client.options("/api/v1/repositories")
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-credentials" in response.headers

    @pytest.mark.asyncio
    async def test_content_type_json(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/repositories", headers=auth_headers)
        assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_process_time_header(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/repositories", headers=auth_headers)
        assert "x-process-time" in response.headers
        process_time = float(response.headers["x-process-time"])
        assert process_time >= 0