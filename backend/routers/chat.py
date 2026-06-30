# -*- coding: utf-8 -*-
"""
对话路由 - 基于知识库的问答接口
"""

import time
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.rag_service import get_rag_service
from services.llm_service import get_llm_service
from services.db_service import save_conversation
from services.sentiment_service import analyze_sentiment
from models.database import SessionLocal, Conversation
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


class SearchRequest(BaseModel):
    question: str
    n_results: Optional[int] = 5


class SearchResponse(BaseModel):
    success: bool
    results: List[dict]
    total: int
    error: Optional[str] = None


def is_fast_path_answer(sources: List[dict]) -> Optional[str]:
    if not sources or len(sources) == 0:
        return None
    top = sources[0]
    similarity = top.get('similarity', 0)
    answer = top.get('answer', '')
    if (similarity >= 0.7 and
        "抱歉" not in answer and
        "暂无相关信息" not in answer and
        len(answer) < 350 and
        len(answer) > 5):
        return answer
    return None


@router.post("/ask", response_model=ChatResponse)
def ask(request: ChatRequest):
    """
    对话接口 - 基于知识库的问答
    """
    total_start = time.time()
    print(f"\n[API] 收到请求: {request.question[:50]}...")
    print(f"[API] session_id: {request.session_id or '新会话'}")

    rag_service = get_rag_service()
    llm_service = get_llm_service()

    context = ""
    sources = []

    if request.use_rag and rag_service.is_ready():
        rag_start = time.time()
        search_result = rag_service.search(request.question, request.n_results)
        print(f"[API] RAG检索耗时: {time.time() - rag_start:.2f}秒")

        if search_result['success'] and search_result['results']:
            sources = search_result['results'][:3]
            context = rag_service.get_context(request.question, request.n_results)

    fast_answer = is_fast_path_answer(sources)
    if fast_answer:
        print(f"[API] ⚡ 快速路径命中！总耗时: {time.time() - total_start:.2f}秒")
        sentiment = analyze_sentiment(request.question)
        try:
            sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
            save_conversation(
                session_id=request.session_id or "unknown",
                question=request.question,
                answer=fast_answer,
                sources=sources_json,
                response_time=time.time() - total_start,
                sentiment=sentiment
            )
        except Exception as e:
            print(f"[API] 保存对话记录失败: {e}")
        return ChatResponse(
            success=True,
            answer=fast_answer,
            sources=sources if sources else None,
            error=None
        )

    if request.use_rag and not context:
        return ChatResponse(
            success=True,
            answer="抱歉，目前知识库中暂无相关信息。",
            sources=None,
            error=None
        )

    llm_start = time.time()
    llm_result = llm_service.chat(
        question=request.question,
        context=context,
        session_id=request.session_id
    )
    print(f"[API] LLM调用耗时: {time.time() - llm_start:.2f}秒")

    if not llm_result['success']:
        if sources:
            answer = sources[0].get('answer', '服务暂时不可用，请稍后再试。')
        else:
            answer = "服务暂时不可用，请稍后再试。"
        return ChatResponse(
            success=False,
            answer=answer,
            sources=sources if sources else None,
            error=llm_result['error']
        )

    sentiment = analyze_sentiment(request.question)
    answer = llm_result['answer']

    try:
        sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
        save_conversation(
            session_id=request.session_id or "unknown",
            question=request.question,
            answer=answer,
            sources=sources_json,
            response_time=time.time() - total_start,
            sentiment=sentiment
        )
        print("[API] 对话记录已保存")
    except Exception as e:
        print(f"[API] 保存对话记录失败: {e}")

    print(f"[API] 总耗时: {time.time() - total_start:.2f}秒")
    return ChatResponse(
        success=True,
        answer=answer,
        sources=sources if sources else None,
        error=None
    )


@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    """
    检索接口（仅检索，不调用大模型）
    """
    rag_service = get_rag_service()

    if not rag_service.is_ready():
        raise HTTPException(status_code=503, detail="RAG服务未就绪")

    result = rag_service.search(request.question, request.n_results)

    return SearchResponse(
        success=result['success'],
        results=result['results'],
        total=result['total'],
        error=result['error']
    )


@router.post("/clear")
def clear_session(session_id: str):
    """
    清空会话历史
    """
    llm_service = get_llm_service()
    llm_service.clear_session(session_id)
    return {"success": True, "message": f"会话 {session_id} 已清空"}


@router.get("/health")
def health():
    """健康检查"""
    rag_service = get_rag_service()
    llm_service = get_llm_service()

    return {
        "status": "ok",
        "rag_ready": rag_service.is_ready(),
        "llm_ready": llm_service.is_ready(),
        "rag_count": rag_service.collection.count() if rag_service.is_ready() else 0
    }


@router.get("/session/init")
def init_session():
    """
    分配一个新的 session_id
    """
    from models.database import SessionLocal, Conversation
    from datetime import datetime
    
    db = SessionLocal()
    try:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        count = db.query(Conversation.session_id).filter(
            Conversation.created_at >= today_start,
            Conversation.created_at <= today_end,
            Conversation.session_id.isnot(None),
            Conversation.session_id != ""
        ).distinct().count()
        
        seq = str(count + 1).zfill(6)
        session_id = f"lingshan_{datetime.now().strftime('%Y%m%d')}_{seq}"
        
        return {"code": 0, "data": {"session_id": session_id}, "msg": "success"}
    finally:
        db.close()