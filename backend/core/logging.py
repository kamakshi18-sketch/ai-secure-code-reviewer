import sys
import structlog
from typing import Any, Dict
from core.config import settings


def configure_logging() -> None:
    timestamper = structlog.processors.TimeStamper(fmt="ISO", utc=True)
    
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if settings.ENVIRONMENT == "development":
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    import logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)


class LoggerMixin:
    @property
    def logger(self) -> structlog.BoundLogger:
        return get_logger(self.__class__.__module__)


def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: str = None,
    **kwargs: Any
) -> None:
    logger = get_logger("api.request")
    logger.info(
        "API request completed",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        user_id=user_id,
        **kwargs
    )


def log_task_event(
    task_name: str,
    event: str,
    task_id: str = None,
    **kwargs: Any
) -> None:
    logger = get_logger("celery.task")
    logger.info(
        f"Task {event}",
        task_name=task_name,
        task_id=task_id,
        event=event,
        **kwargs
    )


def log_security_event(
    event: str,
    user_id: str = None,
    ip_address: str = None,
    resource: str = None,
    success: bool = True,
    **kwargs: Any
) -> None:
    logger = get_logger("security.audit")
    logger.info(
        f"Security event: {event}",
        event=event,
        user_id=user_id,
        ip_address=ip_address,
        resource=resource,
        success=success,
        **kwargs
    )


def log_scan_event(
    scan_id: str,
    event: str,
    repository_id: str = None,
    findings_count: int = None,
    duration_ms: float = None,
    **kwargs: Any
) -> None:
    logger = get_logger("scan")
    logger.info(
        f"Scan {event}",
        scan_id=scan_id,
        event=event,
        repository_id=repository_id,
        findings_count=findings_count,
        duration_ms=duration_ms,
        **kwargs
    )


def log_patch_event(
    patch_id: str,
    event: str,
    finding_id: str = None,
    success: bool = True,
    **kwargs: Any
) -> None:
    logger = get_logger("patch")
    logger.info(
        f"Patch {event}",
        patch_id=patch_id,
        event=event,
        finding_id=finding_id,
        success=success,
        **kwargs
    )