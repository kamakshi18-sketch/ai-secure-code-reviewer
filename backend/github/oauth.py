from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import jwt
import httpx
import structlog
from github import Github, GithubIntegration, Auth
from github.GithubException import GithubException

from core.config import settings
from core.logging import get_logger

logger = get_logger("github.oauth")


class GitHubOAuthService:
    def __init__(self):
        self.client_id = settings.GITHUB_CLIENT_ID
        self.client_secret = settings.GITHUB_CLIENT_SECRET
        self.redirect_uri = f"{settings.BACKEND_URL}/api/v1/auth/github/callback"
    
    def get_authorization_url(self, state: str = None) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "repo read:user user:email read:org admin:repo_hook",
            "state": state or "",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://github.com/login/oauth/authorize?{query}"
    
    async def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            
            if response.status_code != 200:
                logger.error("Token exchange failed", status=response.status_code, response=response.text)
                return None
            
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            
            if response.status_code != 200:
                logger.error("Failed to get user info", status=response.status_code)
                return None
            
            return response.json()
    
    async def get_user_emails(self, access_token: str) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            
            if response.status_code != 200:
                return []
            
            return response.json()


class GitHubAppService:
    def __init__(self):
        self.app_id = settings.GITHUB_APP_ID
        self.private_key = settings.GITHUB_APP_PRIVATE_KEY
        self._integration = None
    
    @property
    def integration(self) -> GithubIntegration:
        if not self._integration and self.app_id and self.private_key:
            self._integration = GithubIntegration(
                auth=Auth.AppAuth(self.app_id, self.private_key)
            )
        return self._integration
    
    def get_installation_token(self, installation_id: int) -> Optional[str]:
        if not self.integration:
            return None
        
        try:
            token = self.integration.get_access_token(installation_id)
            return token.token
        except GithubException as e:
            logger.error("Failed to get installation token", installation_id=installation_id, error=str(e))
            return None
    
    def get_installations(self) -> List[Dict[str, Any]]:
        if not self.integration:
            return []
        
        try:
            installations = self.integration.get_installations()
            return [
                {
                    "id": inst.id,
                    "account": {
                        "login": inst.account.login,
                        "type": inst.account.type,
                    },
                    "repository_selection": inst.repository_selection,
                    "permissions": inst.permissions,
                    "created_at": inst.created_at.isoformat() if inst.created_at else None,
                }
                for inst in installations
            ]
        except GithubException as e:
            logger.error("Failed to get installations", error=str(e))
            return []
    
    def get_repositories_for_installation(self, installation_id: int) -> List[Dict[str, Any]]:
        token = self.get_installation_token(installation_id)
        if not token:
            return []
        
        try:
            g = Github(token)
            repos = []
            for repo in g.get_user().get_repos():
                repos.append({
                    "id": repo.id,
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "private": repo.private,
                    "html_url": repo.html_url,
                    "clone_url": repo.clone_url,
                    "default_branch": repo.default_branch,
                    "language": repo.language,
                })
            return repos
        except GithubException as e:
            logger.error("Failed to get repositories", installation_id=installation_id, error=str(e))
            return []


class GitHubTokenManager:
    def __init__(self):
        self.oauth_service = GitHubOAuthService()
    
    async def refresh_user_token(self, user) -> Optional[str]:
        if not user.github_refresh_token:
            return None
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": self.oauth_service.client_id,
                    "client_secret": self.oauth_service.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": user.github_refresh_token,
                },
                headers={"Accept": "application/json"},
            )
            
            if response.status_code != 200:
                logger.error("Token refresh failed", user_id=user.id, status=response.status_code)
                return None
            
            data = response.json()
            return data.get("access_token")
    
    def create_jwt_for_app(self) -> Optional[str]:
        if not settings.GITHUB_APP_ID or not settings.GITHUB_APP_PRIVATE_KEY:
            return None
        
        now = datetime.utcnow()
        payload = {
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=10)).timestamp()),
            "iss": settings.GITHUB_APP_ID,
        }
        
        return jwt.encode(payload, settings.GITHUB_APP_PRIVATE_KEY, algorithm="RS256")


github_oauth_service = GitHubOAuthService()
github_app_service = GitHubAppService()
github_token_manager = GitHubTokenManager()