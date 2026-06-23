# -*- coding: utf-8 -*-
"""
对话路由 - 支持多轮对话记忆 + 双模型交叉验证
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
from services.safe_llm_service import get_safe_llm_service

router = APIRouter(prefix="/api/chat", tags=["对话"])


# ==================== 请求/响应模型 ====================
class ChatRequest(BaseModel):
    """对话请求"""
    question: str
    session_id: Optional[str] = None
    use_rag: Optional[bool] = True
    n_results: Optional[int] = 3


class ChatResponse(BaseModel):
    """对话响应"""
    success: bool
    answer: str
    sources: Optional[List[dict]] = None
    error: Optional[str] = None


class SearchRequest(BaseModel):
    """检索请求"""
    question: str
    n_results: Optional[int] = 5


class SearchResponse(BaseModel):
    """检索响应"""
    success: bool
    results: List[dict]
    total: int
    error: Optional[str] = None


class VerifiedChatResponse(BaseModel):
    """验证对话响应"""
    success: bool
    answer: str
    confidence: float
    verified_sentences: Optional[List[dict]] = None
    sources: Optional[List[dict]] = None
    error: Optional[str] = None


# ==================== API 端点 ====================
@router.post("/ask", response_model=ChatResponse)
async def ask(request: ChatRequest):
    """
    对话接口
    - 支持多轮对话记忆（通过 session_id）
    - 支持 RAG 检索增强
    """
    total_start = time.time()
    print(f"\n[API] 收到请求: {request.question[:50]}...")
    print(f"[API] session_id: {request.session_id or '新会话'}")

    rag_service = get_rag_service()
    llm_service = get_llm_service()

    context = ""
    sources = []

    # 1. RAG 检索
    if request.use_rag and rag_service.is_ready():
        rag_start = time.time()
        search_result = rag_service.search(request.question, request.n_results)
        print(f"[API] RAG检索耗时: {time.time() - rag_start:.2f}秒")

        if search_result['success'] and search_result['results']:
            sources = search_result['results'][:3]
            context = rag_service.get_context(request.question, request.n_results)

    # 2. 调用大模型（带 session_id）
    llm_start = time.time()
    llm_result = llm_service.chat(
        question=request.question,
        context=context,
        session_id=request.session_id
    )
    print(f"[API] LLM调用耗时: {time.time() - llm_start:.2f}秒")

    # 3. 处理结果
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

    # 4. 保存对话记录
    try:
        sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
        save_conversation(
            session_id=request.session_id or "unknown",
            question=request.question,
            answer=llm_result['answer'],
            sources=sources_json,
            response_time=time.time() - total_start,
            sentiment=None
        )
        print("[API] 对话记录已保存")
    except Exception as e:
        print(f"[API] 保存对话记录失败: {e}")

    print(f"[API] 总耗时: {time.time() - total_start:.2f}秒")
    return ChatResponse(
        success=True,
        answer=llm_result['answer'],
        sources=sources if sources else None,
        error=None
    )


@router.post("/ask/verified", response_model=VerifiedChatResponse)
async def ask_verified(request: ChatRequest):
    """
    验证对话接口：分段生成 + 逐句交叉验证（更可靠）
    """
    total_start = time.time()
    print(f"\n[API] 收到验证请求: {request.question[:50]}...")

    rag_service = get_rag_service()
    safe_llm_service = get_safe_llm_service()

    context = ""
    sources = []

    if request.use_rag and rag_service.is_ready():
        rag_start = time.time()
        search_result = rag_service.search(request.question, request.n_results)
        print(f"[API] RAG检索耗时: {time.time() - rag_start:.2f}秒")

        if search_result['success'] and search_result['results']:
            sources = search_result['results'][:3]
            context = rag_service.get_context(request.question, request.n_results)

    # 调用安全问答服务（含验证）
    # 注意：不提前返回拒答，由 safe_llm_service 内部处理
    result = await safe_llm_service.ask_with_verification(
        question=request.question,
        context=context,
        session_id=request.session_id
    )

    # 保存对话记录
    try:
        sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
        save_conversation(
            session_id=request.session_id or "unknown",
            question=request.question,
            answer=result.get("answer", ""),
            sources=sources_json,
            response_time=time.time() - total_start,
            sentiment=None
        )
        print("[API] 验证对话记录已保存")
    except Exception as e:
        print(f"[API] 保存验证对话记录失败: {e}")

    print(f"[API] 总耗时: {time.time() - total_start:.2f}秒")
    return VerifiedChatResponse(
        success=result["success"],
        answer=result["answer"],
        confidence=result.get("confidence", 0.0),
        verified_sentences=result.get("verified_sentences"),
        sources=sources if sources else None,
        error=result.get("error")
    )


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
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
async def clear_session(session_id: str):
    """
    清空会话历史
    """
    llm_service = get_llm_service()
    llm_service.clear_session(session_id)
    return {"success": True, "message": f"会话 {session_id} 已清空"}


@router.get("/health")
async def health():
    """健康检查"""
    rag_service = get_rag_service()
    llm_service = get_llm_service()

    return {
        "status": "ok",
        "rag_ready": rag_service.is_ready(),
        "llm_ready": llm_service.is_ready(),
        "rag_count": rag_service.collection.count() if rag_service.is_ready() else 0
    }