# -*- coding: utf-8 -*-
"""
对话路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, BACKEND_DIR)

from services.rag_service import get_rag_service
from services.llm_service import get_llm_service

router = APIRouter(prefix="/api/chat", tags=["对话"])


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    use_rag: Optional[bool] = True
    n_results: Optional[int] = 3


class ChatResponse(BaseModel):
    success: bool
    answer: str
    sources: Optional[List[dict]] = None
    error: Optional[str] = None


@router.post("/ask", response_model=ChatResponse)
async def ask(request: ChatRequest):
    rag_service = get_rag_service()
    llm_service = get_llm_service()

    context = ""
    sources = []

    if request.use_rag and rag_service.is_ready():
        search_result = rag_service.search(request.question, request.n_results)
        if search_result['success'] and search_result['results']:
            sources = search_result['results'][:3]
            context = rag_service.get_context(request.question, request.n_results)

    llm_result = llm_service.chat(request.question, context)

    if not llm_result['success']:
        if sources:
            answer = sources[0].get('answer', '服务暂时不可用')
        else:
            answer = "服务暂时不可用，请稍后再试。"
        return ChatResponse(
            success=False,
            answer=answer,
            sources=sources if sources else None,
            error=llm_result['error']
        )

    return ChatResponse(
        success=True,
        answer=llm_result['answer'],
        sources=sources if sources else None,
        error=None
    )


@router.get("/health")
async def health():
    rag_service = get_rag_service()
    llm_service = get_llm_service()
    return {
        "status": "ok",
        "rag_ready": rag_service.is_ready(),
        "llm_ready": llm_service.is_ready()
    }