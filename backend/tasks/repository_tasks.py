from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import asyncio
import os
import shutil
from git import Repo
from git.exc import GitCommandError

from core.celery_app import celery_app
from core.logging import get_logger, log_task_event
from database.session import async_session_maker
from models import Repository, RepositoryStatus
from core.config import settings

logger = get_logger("repository_tasks")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def clone_repository_task(self, repository_id: str):
    log_task_event("clone_repository", "started", task_id=self.request.id, repository_id=repository_id)
    
    async def _clone():
        async with async_session_maker() as db:
            repo = await db.get(Repository, repository_id)
            if not repo:
                logger.error("Repository not found", repository_id=repository_id)
                return
            
            repo.status = RepositoryStatus.CLONING
            await db.commit()
            
            local_path = os.path.join(settings.TEMP_DIR, "repos", str(repo.id))
            
            if os.path.exists(local_path):
                shutil.rmtree(local_path)
            
            os.makedirs(local_path, exist_ok=True)
            
            try:
                clone_url = repo.clone_url
                if repo.owner.github_access_token:
                    from urllib.parse import urlparse
                    parsed = urlparse(clone_url)
                    clone_url = f"https://{repo.owner.github_access_token}@{parsed.netloc}{parsed.path}"
                
                Repo.clone_from(clone_url, local_path, branch=repo.default_branch, depth=1)
                
                repo.local_path = local_path
                repo.status = RepositoryStatus.CLONED
                await db.commit()
                
                log_task_event("clone_repository", "completed", task_id=self.request.id, repository_id=repository_id)
                
                detect_language_task.delay(repository_id)
                
            except GitCommandError as e:
                repo.status = RepositoryStatus.FAILED
                await db.commit()
                logger.error("Git clone failed", repository_id=repository_id, error=str(e))
                log_task_event("clone_repository", "failed", task_id=self.request.id, repository_id=repository_id, error=str(e))
                raise self.retry(exc=e)
            except Exception as e:
                repo.status = RepositoryStatus.FAILED
                await db.commit()
                logger.error("Clone failed", repository_id=repository_id, error=str(e))
                log_task_event("clone_repository", "failed", task_id=self.request.id, repository_id=repository_id, error=str(e))
                raise
    
    asyncio.run(_clone())


@celery_app.task(bind=True, max_retries=2)
def detect_language_task(self, repository_id: str):
    log_task_event("detect_language", "started", task_id=self.request.id, repository_id=repository_id)
    
    async def _detect():
        async with async_session_maker() as db:
            repo = await db.get(Repository, repository_id)
            if not repo or not repo.local_path:
                logger.error("Repository not found or not cloned", repository_id=repository_id)
                return
            
            try:
                from collections import Counter
                extensions = Counter()
                
                for root, dirs, files in os.walk(repo.local_path):
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    for file in files:
                        ext = os.path.splitext(file)[1].lower()
                        if ext:
                            extensions[ext] += 1
                
                lang_map = {
                    '.py': 'python',
                    '.js': 'javascript',
                    '.ts': 'typescript',
                    '.jsx': 'javascript',
                    '.tsx': 'typescript',
                    '.java': 'java',
                    '.go': 'go',
                    '.rb': 'ruby',
                    '.php': 'php',
                    '.cs': 'csharp',
                    '.cpp': 'cpp',
                    '.c': 'c',
                    '.h': 'c',
                    '.rs': 'rust',
                    '.kt': 'kotlin',
                    '.swift': 'swift',
                    '.scala': 'scala',
                }
                
                lang_counts = Counter()
                for ext, count in extensions.items():
                    if ext in lang_map:
                        lang_counts[lang_map[ext]] += count
                
                if lang_counts:
                    primary_language = lang_counts.most_common(1)[0][0]
                    all_languages = [lang for lang, _ in lang_counts.most_common()]
                    
                    repo.language = primary_language
                    repo.languages = all_languages
                    await db.commit()
                    
                    logger.info("Language detected", repository_id=repository_id, language=primary_language, languages=all_languages)
                else:
                    logger.warning("No recognized languages found", repository_id=repository_id)
                
                log_task_event("detect_language", "completed", task_id=self.request.id, repository_id=repository_id)
                
            except Exception as e:
                logger.error("Language detection failed", repository_id=repository_id, error=str(e))
                log_task_event("detect_language", "failed", task_id=self.request.id, repository_id=repository_id, error=str(e))
                raise
    
    asyncio.run(_detect())