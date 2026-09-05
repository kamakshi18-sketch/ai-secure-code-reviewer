from fastapi import APIRouter

from api.v1.endpoints import auth, repositories, scans, findings, patches, reports, chat, pull_requests, users, webhooks, agents

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(repositories.router, prefix="/repositories", tags=["Repositories"])
api_router.include_router(scans.router, prefix="/scans", tags=["Scans"])
api_router.include_router(findings.router, prefix="/findings", tags=["Findings"])
api_router.include_router(patches.router, prefix="/patches", tags=["Patches"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(pull_requests.router, prefix="/pull-requests", tags=["Pull Requests"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(agents.router, prefix="/agents", tags=["AI Agents"])