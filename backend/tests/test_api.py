import pytest
from httpx import AsyncClient
from uuid import UUID


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_register_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "full_name": "New User",
                "role": "developer"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "password123",
                "full_name": "Another User",
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "testpassword123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "wrongpassword"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, test_user):
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "testpassword123"}
        )
        refresh_token = login_response.json()["refresh_token"]
        
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers, test_user):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_update_current_user(self, client: AsyncClient, auth_headers, test_user):
        response = await client.put(
            "/api/v1/auth/me",
            json={"full_name": "Updated Name"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_change_password(self, client: AsyncClient, auth_headers, test_user):
        response = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "testpassword123", "new_password": "newpassword123"},
            headers=auth_headers
        )
        assert response.status_code == 200

        # Verify new password works
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "newpassword123"}
        )
        assert login_response.status_code == 200


class TestUserEndpoints:
    @pytest.mark.asyncio
    async def test_list_users_admin(self, client: AsyncClient, admin_auth_headers):
        response = await client.get("/api/v1/users", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_list_users_non_admin(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/users", headers=auth_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_user(self, client: AsyncClient, auth_headers, test_user):
        response = await client.get(f"/api/v1/users/{test_user.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_create_user_admin(self, client: AsyncClient, admin_auth_headers):
        response = await client.post(
            "/api/v1/users",
            json={
                "email": "created@example.com",
                "password": "password123",
                "full_name": "Created User",
                "role": "developer"
            },
            headers=admin_auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "created@example.com"

    @pytest.mark.asyncio
    async def test_update_user_admin(self, client: AsyncClient, admin_auth_headers, test_user):
        response = await client.put(
            f"/api/v1/users/{test_user.id}",
            json={"role": "security_engineer"},
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "security_engineer"

    @pytest.mark.asyncio
    async def test_delete_user_admin(self, client: AsyncClient, admin_auth_headers, test_user):
        response = await client.delete(f"/api/v1/users/{test_user.id}", headers=admin_auth_headers)
        assert response.status_code == 204


class TestRepositoryEndpoints:
    @pytest.mark.asyncio
    async def test_list_repositories(self, client: AsyncClient, auth_headers, test_repository):
        response = await client.get("/api/v1/repositories", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(r["id"] == str(test_repository.id) for r in data["items"])

    @pytest.mark.asyncio
    async def test_get_repository(self, client: AsyncClient, auth_headers, test_repository):
        response = await client.get(f"/api/v1/repositories/{test_repository.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == test_repository.full_name

    @pytest.mark.asyncio
    async def test_update_repository(self, client: AsyncClient, auth_headers, test_repository):
        response = await client.put(
            f"/api/v1/repositories/{test_repository.id}",
            json={"description": "Updated description"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_delete_repository(self, client: AsyncClient, auth_headers, test_repository):
        response = await client.delete(f"/api/v1/repositories/{test_repository.id}", headers=auth_headers)
        assert response.status_code == 204


class TestScanEndpoints:
    @pytest.mark.asyncio
    async def test_list_scans(self, client: AsyncClient, auth_headers, test_scan):
        response = await client.get("/api/v1/scans", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(s["id"] == str(test_scan.id) for s in data["items"])

    @pytest.mark.asyncio
    async def test_create_scan(self, client: AsyncClient, auth_headers, test_repository):
        response = await client.post(
            "/api/v1/scans",
            json={"repository_id": str(test_repository.id), "scan_type": "full"},
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["repository_id"] == str(test_repository.id)
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_scan(self, client: AsyncClient, auth_headers, test_scan):
        response = await client.get(f"/api/v1/scans/{test_scan.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_scan.id)

    @pytest.mark.asyncio
    async def test_cancel_scan(self, client: AsyncClient, auth_headers, test_scan):
        response = await client.post(f"/api/v1/scans/{test_scan.id}/cancel", headers=auth_headers)
        assert response.status_code == 400  # Already completed

    @pytest.mark.asyncio
    async def test_retry_scan(self, client: AsyncClient, auth_headers, test_scan):
        response = await client.post(f"/api/v1/scans/{test_scan.id}/retry", headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_scan_summary(self, client: AsyncClient, auth_headers, test_scan):
        response = await client.get(f"/api/v1/scans/{test_scan.id}/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "by_severity" in data
        assert "by_scanner" in data


class TestFindingEndpoints:
    @pytest.mark.asyncio
    async def test_list_findings(self, client: AsyncClient, auth_headers, test_findings):
        response = await client.get("/api/v1/findings", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2

    @pytest.mark.asyncio
    async def test_list_findings_with_filters(self, client: AsyncClient, auth_headers, test_findings):
        response = await client.get(
            "/api/v1/findings",
            params={"severity": "high"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(f["severity"] == "high" for f in data["items"])

    @pytest.mark.asyncio
    async def test_get_finding(self, client: AsyncClient, auth_headers, test_findings):
        finding = test_findings[0]
        response = await client.get(f"/api/v1/findings/{finding.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["rule_name"] == finding.rule_name

    @pytest.mark.asyncio
    async def test_update_finding(self, client: AsyncClient, auth_headers, test_findings):
        finding = test_findings[0]
        response = await client.put(
            f"/api/v1/findings/{finding.id}",
            json={"status": "fixed"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "fixed"

    @pytest.mark.asyncio
    async def test_bulk_update_findings(self, client: AsyncClient, auth_headers, test_findings):
        finding_ids = [str(f.id) for f in test_findings]
        response = await client.post(
            "/api/v1/findings/bulk-update",
            json={"finding_ids": finding_ids, "status": "ignored"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] == 2

    @pytest.mark.asyncio
    async def test_get_findings_stats(self, client: AsyncClient, auth_headers, test_findings):
        response = await client.get("/api/v1/findings/stats/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "by_severity" in data
        assert "by_status" in data


class TestPatchEndpoints:
    @pytest.mark.asyncio
    async def test_list_patches(self, client: AsyncClient, auth_headers, test_patch):
        response = await client.get("/api/v1/patches", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_create_patch(self, client: AsyncClient, auth_headers, test_scan, test_findings):
        finding = test_findings[0]
        response = await client.post(
            "/api/v1/patches",
            json={"scan_id": str(test_scan.id), "finding_id": str(finding.id)},
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_patch(self, client: AsyncClient, auth_headers, test_patch):
        response = await client.get(f"/api/v1/patches/{test_patch.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_patch.id)
        assert "patch_attempts" in data

    @pytest.mark.asyncio
    async def test_apply_patch(self, client: AsyncClient, auth_headers, test_patch):
        response = await client.post(f"/api/v1/patches/{test_patch.id}/apply", headers=auth_headers)
        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_verify_patch(self, client: AsyncClient, auth_headers, test_patch):
        response = await client.post(f"/api/v1/patches/{test_patch.id}/verify", headers=auth_headers)
        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_retry_patch(self, client: AsyncClient, auth_headers, test_patch):
        response = await client.post(f"/api/v1/patches/{test_patch.id}/retry", headers=auth_headers)
        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_retry_with_analysis(self, client: AsyncClient, auth_headers, test_patch):
        response = await client.post(f"/api/v1/patches/{test_patch.id}/retry-with-analysis", headers=auth_headers)
        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_analyze_failure(self, client: AsyncClient, auth_headers, test_patch):
        response = await client.post(f"/api/v1/patches/{test_patch.id}/analyze-failure", headers=auth_headers)
        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_generate_alternative_patch(self, client: AsyncClient, auth_headers, test_patch):
        response = await client.post(
            f"/api/v1/patches/{test_patch.id}/alternative",
            params={"strategy": "defensive"},
            headers=auth_headers
        )
        assert response.status_code == 202


class TestReportEndpoints:
    @pytest.mark.asyncio
    async def test_list_reports(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/reports", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_create_report(self, client: AsyncClient, auth_headers, test_scan):
        response = await client.post(
            "/api/v1/reports",
            json={"scan_id": str(test_scan.id), "format": "markdown", "title": "Test Report"},
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert "report_id" in data

    @pytest.mark.asyncio
    async def test_get_report(self, client: AsyncClient, auth_headers):
        # First create a report
        create_response = await client.post(
            "/api/v1/reports",
            json={"scan_id": str(test_scan.id), "format": "markdown"},
            headers=auth_headers
        )
        report_id = create_response.json()["report_id"]
        
        response = await client.get(f"/api/v1/reports/{report_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == report_id

    @pytest.mark.asyncio
    async def test_download_report(self, client: AsyncClient, auth_headers):
        # First create a report
        create_response = await client.post(
            "/api/v1/reports",
            json={"scan_id": str(test_scan.id), "format": "markdown"},
            headers=auth_headers
        )
        report_id = create_response.json()["report_id"]
        
        response = await client.get(f"/api/v1/reports/{report_id}/download", headers=auth_headers)
        assert response.status_code == 200
        assert "attachment" in response.headers.get("content-disposition", "")


class TestPullRequestEndpoints:
    @pytest.mark.asyncio
    async def test_list_pull_requests(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/pull-requests", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_create_pull_request(self, client: AsyncClient, auth_headers, test_scan, test_patch):
        response = await client.post(
            "/api/v1/pull-requests",
            json={
                "repository_id": str(test_scan.repository_id),
                "scan_id": str(test_scan.id),
                "title": "Security fixes",
                "body": "Fixes vulnerabilities",
                "head_branch": "security/fixes",
                "patch_ids": [str(test_patch.id)]
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "draft"


class TestAgentEndpoints:
    @pytest.mark.asyncio
    async def test_analyze_finding(self, client: AsyncClient, auth_headers, test_findings):
        finding = test_findings[0]
        response = await client.post(
            f"/api/v1/agents/analyze-finding/{finding.id}",
            json={"question": "Why is this vulnerable?"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data or "explanation" in data

    @pytest.mark.asyncio
    async def test_generate_patch_endpoint(self, client: AsyncClient, auth_headers, test_findings):
        finding = test_findings[0]
        response = await client.post(
            f"/api/v1/agents/generate-patch/{finding.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestHealthAndRoot:
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "AI Secure Code Reviewer"

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client: AsyncClient):
        response = await client.get("/metrics")
        assert response.status_code == 200