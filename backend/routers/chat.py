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


# ==================== 景点名称列表与过滤函数 ====================
ATTRACTION_NAMES = [
    "灵山大佛", "九龙灌浴", "灵山梵宫", "五印坛城", "祥符禅寺",
    "拈花广场", "梵天花海", "香月花街", "五灯湖", "灵山大照壁",
    "阿育王柱", "百子戏弥勒", "曼飞龙塔", "无尽意斋", "鹿鸣谷",
    "灵山精舍", "菩提大道", "五明桥", "佛足坛", "五智门",
    "降魔浮雕", "佛教文化博览馆"
]


def extract_attraction_name(question: str) -> Optional[str]:
    """从用户问题中提取景点名称"""
    for name in ATTRACTION_NAMES:
        if name in question:
            return name
    return None


def filter_sources_by_attraction(sources: List[dict], question: str) -> List[dict]:
    """过滤检索结果，优先保留景点名称匹配的"""
    if not sources:
        return sources
    
    attraction_name = extract_attraction_name(question)
    if not attraction_name:
        return sources
    
    matched = []
    unmatched = []
    for source in sources:
        if attraction_name in source.get('question', ''):
            matched.append(source)
        else:
            unmatched.append(source)
    
    # 如果有匹配的，只返回匹配的；否则返回全部（让后续流程处理）
    if matched:
        print(f"[API] 景点过滤: 保留 {len(matched)} 条匹配 '{attraction_name}' 的结果")
        return matched
    return sources


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

    # ==================== 新增：解析指代词（必须在RAG检索之前） ====================
    resolved_question = llm_service.resolve_pronoun(request.question, request.session_id)
    print(f"[API] 解析后问题: {resolved_question}")
    # ==============================================================================

    context = ""
    sources = []

    if request.use_rag and rag_service.is_ready():
        rag_start = time.time()
        # 使用解析后的问题检索
        search_result = rag_service.search(resolved_question, request.n_results)
        print(f"[API] RAG检索耗时: {time.time() - rag_start:.2f}秒")

        if search_result['success'] and search_result['results']:
            sources = search_result['results'][:3]
            # 按景点名称过滤（传入解析后的问题）
            sources = filter_sources_by_attraction(sources, resolved_question)
            # 手动构建 context，避免重复调用 get_context（内部会再次检索）
            context_parts = []
            for i, r in enumerate(sources[:request.n_results], 1):
                context_parts.append(f"【参考{i}】\n问题：{r['question']}\n答案：{r['answer']}")
            context = "\n\n".join(context_parts)

    fast_answer = is_fast_path_answer(sources)
    if fast_answer:
        print(f"[API] ⚡ 快速路径命中！总耗时: {time.time() - total_start:.2f}秒")
        sentiment = analyze_sentiment(resolved_question)
        try:
            sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
            save_conversation(
                session_id=request.session_id or "unknown",
                question=resolved_question,  # 保存解析后的问题
                answer=fast_answer,
                sources=sources_json,
                response_time=time.time() - total_start,
                sentiment=sentiment
            )
        except Exception as e:
            print(f"[API] 保存对话记录失败: {e}")
        # 更新会话的 last_question，以便下一轮指代
        if request.session_id:
            session_data = llm_service.get_or_create_session(request.session_id)
            session_data["last_question"] = resolved_question
        return ChatResponse(
            success=True,
            answer=fast_answer,
            sources=sources if sources else None,
            error=None
        )

    if request.use_rag and not context:
        # 即使无 context，也要保存 last_question
        if request.session_id:
            session_data = llm_service.get_or_create_session(request.session_id)
            session_data["last_question"] = resolved_question
        return ChatResponse(
            success=True,
            answer="抱歉，目前知识库中暂无相关信息。",
            sources=None,
            error=None
        )

    llm_start = time.time()
    llm_result = llm_service.chat(
        question=resolved_question,  # 传入解析后的问题
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

    sentiment = analyze_sentiment(resolved_question)
    answer = llm_result['answer']

    try:
        sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
        save_conversation(
            session_id=request.session_id or "unknown",
            question=resolved_question,  # 保存解析后的问题
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
async def init_session():
    """
    分配一个新的 session_id，保证全局唯一且连续递增
    格式：lingshan_YYYYMMDD_XXXXXX（6位序号）
    """
    from models.database import SessionLocal
    from datetime import datetime
    from sqlalchemy import text

    db = SessionLocal()
    try:
        today = datetime.now().strftime("%Y%m%d")
        # 使用事务和行锁保证原子性
        # 先尝试插入今日记录，如果已存在则忽略
        db.execute(text("INSERT OR IGNORE INTO session_counter (date, counter) VALUES (:date, 0)"), {"date": today})
        # 递增计数器并返回新值
        result = db.execute(
            text("UPDATE session_counter SET counter = counter + 1 WHERE date = :date RETURNING counter"),
            {"date": today}
        ).fetchone()
        # 如果 SQLite 不支持 RETURNING，改用 SELECT 方式
        if result is None:
            # 部分 SQLite 版本不支持 RETURNING，手动查询
            db.execute(text("UPDATE session_counter SET counter = counter + 1 WHERE date = :date"), {"date": today})
            result = db.execute(text("SELECT counter FROM session_counter WHERE date = :date"), {"date": today}).fetchone()
        db.commit()
        seq = str(result[0]).zfill(6)
        session_id = f"lingshan_{today}_{seq}"
        return {"code": 0, "data": {"session_id": session_id}, "msg": "success"}
    except Exception as e:
        db.rollback()
        print(f"[session/init] 错误: {e}")
        return {"code": 1, "msg": str(e), "data": None}
    finally:
        db.close()