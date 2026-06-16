# -*- coding: utf-8 -*-
"""
对话路由
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
from services.db_service import save_conversation   # 导入保存函数

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
    total_start = time.time()
    print(f"\n[API] 收到请求: {request.question[:50]}...")

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

    llm_start = time.time()
    llm_result = llm_service.chat(request.question, context)
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

    # ========== 新增：保存对话记录 ==========
    try:
        # 将 sources 转为 JSON 字符串存储
        sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
        await save_conversation(
            session_id=request.session_id or "unknown",
            question=request.question,
            answer=llm_result['answer'],
            sources=sources_json,
            response_time=time.time() - total_start,
            sentiment=None  # 后续可增加情感分析
        )
        print("[API] 对话记录已保存")
    except Exception as e:
        print(f"[API] 保存对话记录失败: {e}")
    # ======================================

    print(f"[API] 总耗时: {time.time() - total_start:.2f}秒")
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