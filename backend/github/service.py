from typing import Optional, List, Dict, Any
from github import Github, GithubException
from github.Repository import Repository as GithubRepository
from github.PullRequest import PullRequest as GithubPullRequest
import structlog

from core.config import settings
from core.logging import get_logger

logger = get_logger("github.service")


class GitHubService:
    def __init__(self, access_token: str = None):
        self.access_token = access_token or settings.GITHUB_CLIENT_SECRET
        self.client = Github(self.access_token) if self.access_token else None
    
    def get_client(self, access_token: str = None) -> Github:
        token = access_token or self.access_token
        if not token:
            raise ValueError("GitHub access token required")
        return Github(token)
    
    async def get_repository(self, full_name: str, access_token: str = None) -> Optional[Dict[str, Any]]:
        try:
            client = self.get_client(access_token)
            repo = client.get_repo(full_name)
            return self._repo_to_dict(repo)
        except GithubException as e:
            logger.error("Failed to get repository", full_name=full_name, error=str(e))
            return None
    
    async def list_user_repositories(self, access_token: str, per_page: int = 100) -> List[Dict[str, Any]]:
        try:
            client = self.get_client(access_token)
            user = client.get_user()
            repos = []
            for repo in user.get_repos(per_page=per_page):
                repos.append(self._repo_to_dict(repo))
            return repos
        except GithubException as e:
            logger.error("Failed to list repositories", error=str(e))
            return []
    
    async def create_pull_request(
        self,
        repo_full_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
        access_token: str
    ) -> Optional[Dict[str, Any]]:
        try:
            client = self.get_client(access_token)
            repo = client.get_repo(repo_full_name)
            
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
            
            return {
                "id": pr.id,
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "head_branch": pr.head.ref,
                "base_branch": pr.base.ref,
                "html_url": pr.html_url,
                "state": pr.state,
                "merged": pr.merged,
                "merge_commit_sha": pr.merge_commit_sha,
                "created_at": pr.created_at.isoformat() if pr.created_at else None,
                "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
            }
        except GithubException as e:
            logger.error("Failed to create PR", repo=repo_full_name, error=str(e))
            return None
    
    async def update_pull_request(
        self,
        repo_full_name: str,
        pr_number: int,
        title: str = None,
        body: str = None,
        state: str = None,
        access_token: str = None
    ) -> Optional[Dict[str, Any]]:
        try:
            client = self.get_client(access_token)
            repo = client.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)
            
            if title:
                pr.edit(title=title)
            if body:
                pr.edit(body=body)
            if state == "closed":
                pr.edit(state="closed")
            
            return {
                "id": pr.id,
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "merged": pr.merged,
            }
        except GithubException as e:
            logger.error("Failed to update PR", repo=repo_full_name, pr=pr_number, error=str(e))
            return None
    
    async def get_pull_request(
        self,
        repo_full_name: str,
        pr_number: int,
        access_token: str = None
    ) -> Optional[Dict[str, Any]]:
        try:
            client = self.get_client(access_token)
            repo = client.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)
            
            return {
                "id": pr.id,
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "head_branch": pr.head.ref,
                "base_branch": pr.base.ref,
                "html_url": pr.html_url,
                "state": pr.state,
                "merged": pr.merged,
                "merge_commit_sha": pr.merge_commit_sha,
                "files_changed": pr.changed_files,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "created_at": pr.created_at.isoformat() if pr.created_at else None,
                "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
            }
        except GithubException as e:
            logger.error("Failed to get PR", repo=repo_full_name, pr=pr_number, error=str(e))
            return None
    
    async def create_branch(
        self,
        repo_full_name: str,
        branch_name: str,
        from_branch: str,
        access_token: str
    ) -> bool:
        try:
            client = self.get_client(access_token)
            repo = client.get_repo(repo_full_name)
            
            source_branch = repo.get_branch(from_branch)
            repo.create_git_ref(f"refs/heads/{branch_name}", source_branch.commit.sha)
            return True
        except GithubException as e:
            logger.error("Failed to create branch", repo=repo_full_name, branch=branch_name, error=str(e))
            return False
    
    async def push_file(
        self,
        repo_full_name: str,
        file_path: str,
        content: str,
        branch: str,
        commit_message: str,
        access_token: str
    ) -> bool:
        try:
            client = self.get_client(access_token)
            repo = client.get_repo(repo_full_name)
            
            try:
                existing = repo.get_contents(file_path, ref=branch)
                repo.update_file(
                    path=file_path,
                    message=commit_message,
                    content=content,
                    sha=existing.sha,
                    branch=branch
                )
            except GithubException:
                repo.create_file(
                    path=file_path,
                    message=commit_message,
                    content=content,
                    branch=branch
                )
            return True
        except GithubException as e:
            logger.error("Failed to push file", repo=repo_full_name, file=file_path, error=str(e))
            return False
    
    async def get_file_content(
        self,
        repo_full_name: str,
        file_path: str,
        branch: str = None,
        access_token: str = None
    ) -> Optional[str]:
        try:
            client = self.get_client(access_token)
            repo = client.get_repo(repo_full_name)
            content = repo.get_contents(file_path, ref=branch)
            return content.decoded_content.decode("utf-8")
        except GithubException as e:
            logger.error("Failed to get file content", repo=repo_full_name, file=file_path, error=str(e))
            return None
    
    async def create_webhook(
        self,
        repo_full_name: str,
        webhook_url: str,
        secret: str,
        events: List[str] = None,
        access_token: str = None
    ) -> Optional[Dict[str, Any]]:
        try:
            client = self.get_client(access_token)
            repo = client.get_repo(repo_full_name)
            
            hook = repo.create_hook(
                name="web",
                config={
                    "url": webhook_url,
                    "content_type": "json",
                    "secret": secret,
                    "insecure_ssl": "0"
                },
                events=events or ["push", "pull_request"],
                active=True
            )
            
            return {"id": hook.id, "url": hook.config["url"]}
        except GithubException as e:
            logger.error("Failed to create webhook", repo=repo_full_name, error=str(e))
            return None
    
    def _repo_to_dict(self, repo: GithubRepository) -> Dict[str, Any]:
        return {
            "id": repo.id,
            "name": repo.name,
            "full_name": repo.full_name,
            "description": repo.description,
            "html_url": repo.html_url,
            "clone_url": repo.clone_url,
            "ssh_url": repo.ssh_url,
            "default_branch": repo.default_branch,
            "language": repo.language,
            "private": repo.private,
            "created_at": repo.created_at.isoformat() if repo.created_at else None,
            "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
            "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None,
            "size": repo.size,
            "stargazers_count": repo.stargazers_count,
            "forks_count": repo.forks_count,
        }


github_service = GitHubService()