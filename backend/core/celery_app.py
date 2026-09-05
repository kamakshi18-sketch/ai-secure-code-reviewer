from celery import Celery
from celery.schedules import crontab
from core.config import settings


celery_app = Celery(
    "ai_code_reviewer",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.repository_tasks",
        "tasks.scan_tasks",
        "tasks.patch_tasks",
        "tasks.verification_tasks",
        "tasks.report_tasks",
        "tasks.github_tasks",
        "tasks.maintenance_tasks",
        "tasks.retry_tasks",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_TIME_LIMIT - 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    result_expires=3600,
    result_extended=True,
    task_routes={
        "tasks.repository_tasks.*": {"queue": "repository"},
        "tasks.scan_tasks.*": {"queue": "scan"},
        "tasks.patch_tasks.*": {"queue": "patch"},
        "tasks.verification_tasks.*": {"queue": "verification"},
        "tasks.report_tasks.*": {"queue": "report"},
        "tasks.github_tasks.*": {"queue": "github"},
        "tasks.maintenance_tasks.*": {"queue": "maintenance"},
        "tasks.retry_tasks.*": {"queue": "retry"},
    },
    task_annotations={
        "*": {
            "rate_limit": "10/m",
        },
        "tasks.scan_tasks.run_security_scan_task": {
            "rate_limit": "2/m",
            "time_limit": 3600,
        },
        "tasks.patch_tasks.generate_patch_task": {
            "rate_limit": "5/m",
            "time_limit": 600,
        },
        "tasks.verification_tasks.verify_patch_task": {
            "rate_limit": "3/m",
            "time_limit": 900,
        },
        "tasks.retry_tasks.retry_patch_with_analysis_task": {
            "rate_limit": "2/m",
            "time_limit": 600,
        },
    },
    beat_schedule={
        "cleanup-old-scans": {
            "task": "tasks.maintenance_tasks.cleanup_old_scans",
            "schedule": crontab(hour=2, minute=0),
        },
        "cleanup-temp-files": {
            "task": "tasks.maintenance_tasks.cleanup_temp_files",
            "schedule": crontab(hour=3, minute=0),
        },
        "update-embeddings": {
            "task": "tasks.maintenance_tasks.update_knowledge_base_embeddings",
            "schedule": crontab(hour=4, minute=0),
        },
    },
)

celery_app.autodiscover_tasks()


@celery_app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")