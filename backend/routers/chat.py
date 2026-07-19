# -*- coding: utf-8 -*-
"""
对话路由 - 基于知识库的问答接口。
"""

import time
import random
import re
from datetime import datetime
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
from services.knowledge_constants import extract_attraction_name

router = APIRouter(prefix="/api/chat", tags=["对话"])
SESSION_ID_RE = re.compile(r"^lingshan_\d{8}_\d{4}$")


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    device_id: Optional[str] = None
    use_rag: Optional[bool] = True
    n_results: Optional[int] = 5
    verify: Optional[bool] = True


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


def filter_sources_by_attraction(sources: List[dict], question: str) -> List[dict]:
    """完全禁用景点过滤，避免非景区内容被丢弃。"""
    return sources


def persist_conversation(session_id: str, question: str, answer: str, sources: List[dict], started_at: float):
    try:
        sentiment = analyze_sentiment(question)
        save_conversation(
            session_id=session_id or "unknown",
            question=question,
            answer=answer,
            sources=sources or None,
            response_time=time.time() - started_at,
            sentiment=sentiment
        )
        print("[API] 对话记录已保存")
    except Exception as e:
        print(f"[API] 保存对话记录失败: {e}")


def normalize_device_id(device_id: Optional[str]) -> str:
    value = (device_id or "").strip()
    value = "".join(ch for ch in value if ch.isalnum() or ch in ("-", "_"))
    return value[:80] or "unknown"


def ensure_session_owner(session_id: Optional[str], device_id: Optional[str]) -> bool:
    if not session_id:
        return True
    if not SESSION_ID_RE.match(session_id):
        return False

    from models.database import SessionLocal
    from sqlalchemy import text

    owner = normalize_device_id(device_id)
    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT device_id FROM session_allocations WHERE session_id = :session_id"),
            {"session_id": session_id}
        ).fetchone()

        if row:
            if row[0] and row[0] not in (owner, "review_only"):
                return False
            db.execute(
                text(
                    "UPDATE session_allocations "
                    "SET device_id = :device_id, updated_at = :updated_at "
                    "WHERE session_id = :session_id"
                ),
                {"session_id": session_id, "device_id": owner, "updated_at": datetime.now()}
            )
        else:
            result = db.execute(
                text(
                    "INSERT OR IGNORE INTO session_allocations (session_id, device_id, created_at, updated_at) "
                    "VALUES (:session_id, :device_id, :created_at, :updated_at)"
                ),
                {
                    "session_id": session_id,
                    "device_id": owner,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            )
            if result.rowcount != 1:
                row = db.execute(
                    text("SELECT device_id FROM session_allocations WHERE session_id = :session_id"),
                    {"session_id": session_id}
                ).fetchone()
                if not row or (row[0] and row[0] not in (owner, "review_only")):
                    db.rollback()
                    return False
                db.execute(
                    text(
                        "UPDATE session_allocations "
                        "SET device_id = :device_id, updated_at = :updated_at "
                        "WHERE session_id = :session_id"
                    ),
                    {"session_id": session_id, "device_id": owner, "updated_at": datetime.now()}
                )
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"[session/owner] 检查失败: {e}")
        return False
    finally:
        db.close()


def friendly_no_context_answer(question: str) -> str:
    attraction_name = extract_attraction_name(question)
    if attraction_name:
        return f"我这边这次没有稳定查到{attraction_name}的对应资料。你可以换个问法，比如问“{attraction_name}介绍”“{attraction_name}有什么看点”或“{attraction_name}开放时间”，我再帮你查。"
    return "我这边资料里暂时没查到这部分。你可以把问题说得更具体一点，比如问某个景点、门票、开放时间、演出或路线，我再帮你查。"


def friendly_service_error() -> str:
    return "我这边刚刚连接有点不稳定，你可以稍后再问一次，我会继续帮你查。"


@router.post("/ask", response_model=ChatResponse)
async def ask(request: ChatRequest):
    """对话接口 - 基于知识库的问答。"""
    total_start = time.time()
    question = request.question.strip()
    print(f"\n[API] 收到请求: {question[:50]}...")
    print(f"[API] session_id: {request.session_id or '新会话'}")

    if not question:
        return ChatResponse(success=False, answer="请输入问题。", sources=None, error="empty question")

    if not ensure_session_owner(request.session_id, request.device_id):
        return ChatResponse(
            success=False,
            answer="当前会话 ID 已在另一台设备使用，请开启新的会话后继续。",
            sources=None,
            error="SESSION_OCCUPIED"
        )

    try:
        rag_service = get_rag_service()
        llm_service = get_llm_service()

        resolved_question = llm_service.resolve_pronoun(question, request.session_id)
        print(f"[API] 解析后问题: {resolved_question}")

        needs_knowledge = request.use_rag and llm_service.needs_knowledge_base(resolved_question)

        if not needs_knowledge:
            llm_result = llm_service.chat_general(
                question=resolved_question,
                session_id=request.session_id
            )
            answer = llm_result["answer"] if llm_result["success"] else "你好，我是灵山胜境景区的 AI 数字导游小灵。"
            persist_conversation(request.session_id, resolved_question, answer, [], total_start)
            return ChatResponse(success=True, answer=answer, sources=None, error=None)

        context = ""
        sources = []

        if needs_knowledge and rag_service.is_ready():
            rag_start = time.time()
            search_result = rag_service.search(resolved_question, request.n_results)
            print(f"[API] RAG检索耗时: {time.time() - rag_start:.2f}秒")

            if search_result["success"] and search_result["results"]:
                sources = search_result["results"]
                context = rag_service.build_context(sources, request.n_results)

        if needs_knowledge and not context:
            answer = friendly_no_context_answer(resolved_question)
            llm_service.remember_turn(request.session_id, resolved_question, answer)
            persist_conversation(request.session_id, resolved_question, answer, sources, total_start)
            return ChatResponse(success=True, answer=answer, sources=None, error=None)

        llm_start = time.time()
        llm_result = llm_service.chat(
            question=resolved_question,
            context=context,
            session_id=request.session_id,
            remember=False
        )
        print(f"[API] LLM调用耗时: {time.time() - llm_start:.2f}秒")

        if not llm_result["success"]:
            fallback = sources[0].get("answer", friendly_service_error()) if sources else friendly_service_error()
            return ChatResponse(
                success=False,
                answer=fallback,
                sources=sources or None,
                error=llm_result.get("error")
            )

        answer = llm_result["answer"]

        should_verify = False
        verify_reason = ""
        if request.verify:
            should_verify, verify_reason = llm_service.should_verify_answer(
                resolved_question,
                context,
                answer,
                sources
            )

        elapsed_before_verify = time.time() - total_start
        if should_verify and elapsed_before_verify >= 4.8:
            print(f"[API] 跳过LLM核验: 已耗时 {elapsed_before_verify:.2f}秒，优先保证响应速度")
            should_verify = False
            verify_reason = "时间预算不足，跳过二次核验"

        if should_verify:
            verify_start = time.time()
            verify_result = llm_service.verify_answer(resolved_question, context, answer)
            print(
                f"[API] LLM核验耗时: {time.time() - verify_start:.2f}秒 | "
                f"触发原因: {verify_reason} | 结论: {verify_result.get('verdict')} | 原因: {verify_result.get('reason')}"
            )
            if verify_result.get("success"):
                answer = verify_result.get("answer") or answer
        else:
            print(f"[API] 跳过LLM核验: {verify_reason or '未开启核验'}")

        llm_service.remember_turn(request.session_id, resolved_question, answer)
        persist_conversation(request.session_id, resolved_question, answer, sources, total_start)

        print(f"[API] 总耗时: {time.time() - total_start:.2f}秒")
        return ChatResponse(success=True, answer=answer, sources=sources or None, error=None)
    except Exception as e:
        print(f"[API] 异常: {e}")
        return ChatResponse(
            success=False,
            answer=friendly_service_error(),
            sources=None,
            error=str(e)
        )


@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    rag_service = get_rag_service()
    if not rag_service.is_ready():
        raise HTTPException(status_code=503, detail="RAG服务未就绪")
    result = rag_service.search(request.question, request.n_results)
    return SearchResponse(
        success=result["success"],
        results=result["results"],
        total=result["total"],
        error=result["error"]
    )


@router.post("/clear")
def clear_session(session_id: str):
    llm_service = get_llm_service()
    llm_service.clear_session(session_id)
    return {"success": True, "message": f"会话 {session_id} 已清空"}


@router.get("/health")
def health():
    rag_service = get_rag_service()
    llm_service = get_llm_service()
    return {
        "status": "ok",
        "rag_ready": rag_service.is_ready(),
        "llm_ready": llm_service.is_ready(),
        "rag_count": rag_service.collection.count() if rag_service.is_ready() else 0,
        "knowledge_version": "word_rag_20260703_exact_attraction_fallback"
    }


@router.get("/session/init")
async def init_session(device_id: Optional[str] = None):
    from models.database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        today = datetime.now().strftime("%Y%m%d")
        owner = normalize_device_id(device_id)
        rng = random.SystemRandom()

        for _ in range(10000):
            suffix = f"{rng.randint(0, 9999):04d}"
            session_id = f"lingshan_{today}_{suffix}"
            now = datetime.now()
            result = db.execute(
                text(
                    "INSERT OR IGNORE INTO session_allocations "
                    "(session_id, device_id, created_at, updated_at) "
                    "VALUES (:session_id, :device_id, :created_at, :updated_at)"
                ),
                {
                    "session_id": session_id,
                    "device_id": owner,
                    "created_at": now,
                    "updated_at": now
                }
            )

            if result.rowcount == 1:
                db.commit()
                return {"code": 0, "data": {"session_id": session_id}, "msg": "success"}

        db.rollback()
        return {"code": 1, "msg": "今日可用会话 ID 已用完，请明天再试", "data": None}
    except Exception as e:
        db.rollback()
        print(f"[session/init] 错误: {e}")
        return {"code": 1, "msg": str(e), "data": None}
    finally:
        db.close()