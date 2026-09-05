from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.security import get_current_active_user
from database.session import get_db
from models import User, Finding, Scan, Repository
from schemas import ChatRequest, ChatResponse, ChatMessage

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from agents.coordinator import CoordinatorAgent
    from rag.engine import RAGEngine
    
    context = {}
    
    if request.repository_id:
        repo = await db.get(Repository, request.repository_id)
        if repo and (current_user.role in ["admin", "security_engineer"] or repo.owner_id == current_user.id):
            context["repository"] = {
                "id": str(repo.id),
                "name": repo.name,
                "full_name": repo.full_name,
                "language": repo.language,
            }
    
    if request.scan_id:
        scan = await db.get(Scan, request.scan_id)
        if scan:
            context["scan"] = {
                "id": str(scan.id),
                "status": scan.status.value,
                "total_findings": scan.total_findings,
            }
    
    if request.finding_id:
        finding = await db.get(Finding, request.finding_id)
        if finding:
            context["finding"] = {
                "id": str(finding.id),
                "rule_id": finding.rule_id,
                "rule_name": finding.rule_name,
                "severity": finding.severity.value,
                "file_path": finding.file_path,
                "line_start": finding.line_start,
                "message": finding.message,
                "ai_explanation": finding.ai_explanation,
                "ai_root_cause": finding.ai_root_cause,
                "ai_recommended_fix": finding.ai_recommended_fix,
            }
    
    if request.context:
        context.update(request.context)
    
    rag_engine = RAGEngine()
    coordinator = CoordinatorAgent(rag_engine=rag_engine)
    
    response = await coordinator.process_chat(
        messages=[msg.model_dump() for msg in request.messages],
        context=context,
        user_id=str(current_user.id)
    )
    
    return ChatResponse(
        message=ChatMessage(role="assistant", content=response["answer"]),
        sources=response.get("sources", [])
    )


@router.post("/explain-finding/{finding_id}")
async def explain_finding_chat(
    finding_id: UUID,
    question: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    finding = await db.get(Finding, finding_id)
    
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found"
        )
    
    scan = await db.get(Scan, finding.scan_id)
    repo = await db.get(Repository, scan.repository_id) if scan else None
    
    if repo and current_user.role not in ["admin", "security_engineer"] and repo.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this finding"
        )
    
    from agents.security_analysis import SecurityAnalysisAgent
    from rag.engine import RAGEngine
    
    rag_engine = RAGEngine()
    agent = SecurityAnalysisAgent(rag_engine=rag_engine)
    
    response = await agent.explain_finding(
        finding=finding,
        question=question,
        context={
            "repository": repo.name if repo else None,
            "language": repo.language if repo else None,
        }
    )
    
    return ChatResponse(
        message=ChatMessage(role="assistant", content=response["answer"]),
        sources=response.get("sources", [])
    )


@router.get("/history")
async def get_chat_history(
    repository_id: Optional[UUID] = None,
    scan_id: Optional[UUID] = None,
    finding_id: Optional[UUID] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return {
        "messages": [],
        "message": "Chat history endpoint - to be implemented with persistent storage"
    }