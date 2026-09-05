from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import asyncio
import os
import subprocess
from datetime import datetime
from github import Github

from core.celery_app import celery_app
from core.logging import get_logger, log_task_event
from database.session import async_session_maker
from models import PullRequest, PullRequestStatus, Patch, PatchStatus, Finding, Repository, Scan
from core.config import settings

logger = get_logger("github_tasks")


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def create_pull_request_task(self, pr_id: str):
    log_task_event("create_pull_request", "started", pr_id=pr_id)
    
    async def _create():
        async with async_session_maker() as db:
            pr = await db.get(PullRequest, pr_id)
            if not pr:
                logger.error("Pull request not found", pr_id=pr_id)
                return
            
            repo = await db.get(Repository, pr.repository_id)
            if not repo:
                logger.error("Repository not found", repo_id=pr.repository_id)
                return
            
            if not repo.owner.github_access_token:
                pr.status = PullRequestStatus.FAILED
                pr.error_message = "GitHub access token not available"
                await db.commit()
                return
            
            pr.status = PullRequestStatus.DRAFT
            await db.commit()
            
            try:
                g = Github(repo.owner.github_access_token)
                github_repo = g.get_repo(repo.full_name)
                
                head_branch = pr.head_branch
                base_branch = pr.base_branch
                
                try:
                    github_repo.get_branch(head_branch)
                except:
                    base_ref = github_repo.get_branch(base_branch)
                    github_repo.create_git_ref(f"refs/heads/{head_branch}", base_ref.commit.sha)
                
                patches = []
                for patch_id in pr.patches_included:
                    patch = await db.get(Patch, patch_id)
                    if patch and patch.status == PatchStatus.APPLIED:
                        patches.append(patch)
                
                if not patches:
                    pr.status = PullRequestStatus.FAILED
                    pr.error_message = "No applied patches to include"
                    await db.commit()
                    return
                
                commit_message = f"Security fixes: {len(patches)} vulnerabilities patched\n\n"
                for patch in patches:
                    finding = await db.get(Finding, patch.finding_id)
                    if finding:
                        commit_message += f"- Fix {finding.rule_id}: {finding.rule_name} in {finding.file_path}\n"
                
                for patch in patches:
                    file_path = patch.file_path
                    local_file = os.path.join(repo.local_path, file_path)
                    if os.path.exists(local_file):
                        with open(local_file, 'r') as f:
                            content = f.read()
                        
                        github_repo.update_file(
                            path=file_path,
                            message=commit_message,
                            content=content,
                            branch=head_branch,
                        )
                
                github_pr = github_repo.create_pull(
                    title=pr.title,
                    body=pr.body,
                    head=head_branch,
                    base=base_branch,
                )
                
                pr.github_pr_id = github_pr.id
                pr.github_pr_number = github_pr.number
                pr.status = PullRequestStatus.OPEN
                pr.files_changed = len(patches)
                pr.additions = sum(p.additions for p in patches if hasattr(p, 'additions'))
                pr.deletions = sum(p.deletions for p in patches if hasattr(p, 'deletions'))
                await db.commit()
                
                log_task_event("create_pull_request", "completed", pr_id=pr_id, github_pr_number=github_pr.number)
                
            except Exception as e:
                pr.status = PullRequestStatus.FAILED
                pr.error_message = str(e)
                await db.commit()
                
                logger.error("PR creation failed", pr_id=pr_id, error=str(e))
                log_task_event("create_pull_request", "failed", pr_id=pr_id, error=str(e))
                raise self.retry(exc=e)
    
    asyncio.run(_create())


@celery_app.task
def sync_pull_request_task(pr_id: str):
    log_task_event("sync_pull_request", "started", pr_id=pr_id)
    
    async def _sync():
        async with async_session_maker() as db:
            pr = await db.get(PullRequest, pr_id)
            if not pr or not pr.github_pr_id:
                return
            
            repo = await db.get(Repository, pr.repository_id)
            if not repo or not repo.owner.github_access_token:
                return
            
            try:
                g = Github(repo.owner.github_access_token)
                github_repo = g.get_repo(repo.full_name)
                github_pr = github_repo.get_pull(pr.github_pr_number)
                
                if github_pr.merged:
                    pr.status = PullRequestStatus.MERGED
                    pr.merged_at = github_pr.merged_at
                    pr.merge_commit_sha = github_pr.merge_commit_sha
                elif github_pr.state == "closed":
                    pr.status = PullRequestStatus.CLOSED
                    pr.closed_at = github_pr.closed_at
                else:
                    pr.status = PullRequestStatus.OPEN
                
                await db.commit()
                
            except Exception as e:
                logger.error("PR sync failed", pr_id=pr_id, error=str(e))
    
    asyncio.run(_sync())