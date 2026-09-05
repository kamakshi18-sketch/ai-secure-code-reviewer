from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
import structlog
import asyncio
import os
import shutil
from datetime import datetime, timedelta

from core.celery_app import celery_app
from core.logging import get_logger, log_task_event
from database.session import async_session_maker
from models import Scan, ScanStatus, Finding, Patch, PatchStatus, TestResult, AuditLog, Embedding
from core.config import settings

logger = get_logger("maintenance_tasks")


@celery_app.task
def cleanup_old_scans():
    log_task_event("cleanup_old_scans", "started")
    
    async def _cleanup():
        async with async_session_maker() as db:
            cutoff = datetime.utcnow() - timedelta(days=90)
            
            old_scans = await db.execute(
                select(Scan).where(
                    Scan.created_at < cutoff,
                    Scan.status.in_([ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED])
                ).limit(1000)
            )
            scans = old_scans.scalars().all()
            
            for scan in scans:
                await db.delete(scan)
            
            await db.commit()
            
            logger.info("Old scans cleaned up", count=len(scans))
            log_task_event("cleanup_old_scans", "completed", count=len(scans))
    
    asyncio.run(_cleanup())


@celery_app.task
def cleanup_temp_files():
    log_task_event("cleanup_temp_files", "started")
    
    temp_dir = settings.TEMP_DIR
    cutoff = datetime.utcnow() - timedelta(days=7)
    
    try:
        if os.path.exists(temp_dir):
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                if os.path.isdir(item_path):
                    mtime = datetime.fromtimestamp(os.path.getmtime(item_path))
                    if mtime < cutoff:
                        shutil.rmtree(item_path)
                        logger.info("Cleaned up temp directory", path=item_path)
        
        log_task_event("cleanup_temp_files", "completed")
    except Exception as e:
        logger.error("Temp file cleanup failed", error=str(e))
        log_task_event("cleanup_temp_files", "failed", error=str(e))


@celery_app.task
def update_knowledge_base_embeddings():
    log_task_event("update_knowledge_base_embeddings", "started")
    
    async def _update():
        from rag.engine import RAGEngine
        
        rag_engine = RAGEngine()
        
        sources = [
            ("owasp_top_10", "https://owasp.org/www-project-top-ten/"),
            ("owasp_cheatsheets", "https://cheatsheetseries.owasp.org/"),
            ("cwe", "https://cwe.mitre.org/"),
            ("cert_python", "https://wiki.sei.cmu.edu/confluence/display/python"),
            ("cert_java", "https://wiki.sei.cmu.edu/confluence/display/java"),
        ]
        
        for source_name, url in sources:
            try:
                await rag_engine.update_source(source_name, url)
                logger.info("Updated knowledge source", source=source_name)
            except Exception as e:
                logger.error("Failed to update knowledge source", source=source_name, error=str(e))
        
        log_task_event("update_knowledge_base_embeddings", "completed")
    
    asyncio.run(_update())


@celery_app.task
def cleanup_failed_patches():
    log_task_event("cleanup_failed_patches", "started")
    
    async def _cleanup():
        async with async_session_maker() as db:
            cutoff = datetime.utcnow() - timedelta(days=30)
            
            result = await db.execute(
                delete(Patch).where(
                    Patch.status.in_([PatchStatus.FAILED, PatchStatus.REJECTED]),
                    Patch.created_at < cutoff
                )
            )
            
            await db.commit()
            
            logger.info("Failed patches cleaned up", count=result.rowcount)
            log_task_event("cleanup_failed_patches", "completed", count=result.rowcount)
    
    asyncio.run(_cleanup())


@celery_app.task
def cleanup_old_audit_logs():
    log_task_event("cleanup_old_audit_logs", "started")
    
    async def _cleanup():
        async with async_session_maker() as db:
            cutoff = datetime.utcnow() - timedelta(days=365)
            
            result = await db.execute(
                delete(AuditLog).where(AuditLog.created_at < cutoff)
            )
            
            await db.commit()
            
            logger.info("Old audit logs cleaned up", count=result.rowcount)
            log_task_event("cleanup_old_audit_logs", "completed", count=result.rowcount)
    
    asyncio.run(_cleanup())


@celery_app.task
def vacuum_database():
    log_task_event("vacuum_database", "started")
    
    async def _vacuum():
        async with async_session_maker() as db:
            await db.execute(text("VACUUM ANALYZE"))
            logger.info("Database vacuumed")
            log_task_event("vacuum_database", "completed")
    
    asyncio.run(_vacuum())