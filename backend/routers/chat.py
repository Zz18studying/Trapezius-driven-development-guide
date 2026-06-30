# -*- coding: utf-8 -*-
"""
对话路由 - 支持多轮对话记忆 + 双模型交叉验证 + 流式响应
"""

import time
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, AsyncIterable

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.rag_service import get_rag_service
from services.llm_service import get_llm_service
from services.db_service import save_conversation
from services.safe_llm_service import get_safe_llm_service
from services.sentiment_service import analyze_sentiment
from models.database import SessionLocal, Conversation
router = APIRouter(prefix="/api/chat", tags=["对话"])


# ==================== 请求/响应模型 ====================
class ChatRequest(BaseModel):
    """对话请求"""
    question: str
    session_id: Optional[str] = None
    use_rag: Optional[bool] = True
    n_results: Optional[int] = 3
    verify: Optional[bool] = True  # 是否启用交叉验证（避免幻觉），默认启用


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


# ==================== 辅助函数 ====================
def is_fast_path_answer(sources: List[dict]) -> Optional[str]:
    """检查是否可走快速路径（高相似度直接返回）"""
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

    # 快速路径
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

    # 无知识直接拒答
    if request.use_rag and not context:
        return ChatResponse(
            success=True,
            answer="抱歉，目前知识库中暂无相关信息。",
            sources=None,
            error=None
        )

    # 调用大模型（根据verify参数决定是否启用交叉验证）
    llm_start = time.time()
    if request.verify:
        print("[API] ✅ 启用交叉验证模式")
        safe_llm_service = get_safe_llm_service()
        llm_result = await safe_llm_service.ask_with_verification(
            question=request.question,
            context=context,
            session_id=request.session_id
        )
        print(f"[API] 验证LLM调用耗时: {time.time() - llm_start:.2f}秒")
    else:
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

    # 快速路径同样适用
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
        return VerifiedChatResponse(
            success=True,
            answer=fast_answer,
            confidence=1.0,
            verified_sentences=[],
            sources=sources if sources else None,
            error=None
        )

    result = await safe_llm_service.ask_with_verification(
        question=request.question,
        context=context,
        session_id=request.session_id
    )

    sentiment = analyze_sentiment(request.question)
    try:
        sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
        save_conversation(
            session_id=request.session_id or "unknown",
            question=request.question,
            answer=result.get("answer", ""),
            sources=sources_json,
            response_time=time.time() - total_start,
            sentiment=sentiment
        )
        print("[API] 验证对话记录已保存")
    except Exception as e:
        print(f"[API] 保存验证对话记录失败: {e}")

    print(f"[API] 总耗时: {time.time() - total_start:.2f}秒")
    return VerifiedChatResponse(
        success=result["success"],
        answer=result.get("answer", ""),
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


@router.post("/ask/stream")
async def ask_stream(request: ChatRequest):
    """
    流式对话接口 - 逐字返回回答内容（SSE）
    - 事件类型: token (内容块), done (完成), error (错误)
    - 前端使用 EventSource 或 fetch + ReadableStream 接收
    """
    total_start = time.time()
    print(f"\n[API] 收到流式请求: {request.question[:50]}...")
    print(f"[API] session_id: {request.session_id or '新会话'}")

    rag_service = get_rag_service()
    llm_service = get_llm_service()

    context = ""
    sources = []

    # RAG 检索
    if request.use_rag and rag_service.is_ready():
        rag_start = time.time()
        search_result = rag_service.search(request.question, request.n_results)
        print(f"[API] RAG检索耗时: {time.time() - rag_start:.2f}秒")

        if search_result['success'] and search_result['results']:
            sources = search_result['results'][:3]
            context = rag_service.get_context(request.question, request.n_results)

    # ===== 快速路径：高相似度直接返回 =====
    fast_answer = is_fast_path_answer(sources)
    if fast_answer:
        print(f"[API] ⚡ 快速路径命中！总耗时: {time.time() - total_start:.2f}秒")

        async def fast_stream() -> AsyncIterable[str]:
            # 直接作为流式输出
            yield f"data: {json.dumps({'type': 'token', 'content': fast_answer}, ensure_ascii=False)}\n\n"
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
                print("[API] 快速路径流式对话记录已保存")
            except Exception as e:
                print(f"[API] 保存快速路径流式记录失败: {e}")
            yield f"data: {json.dumps({
                'type': 'done',
                'content': fast_answer,
                'sources': sources if sources else None,
                'response_time': round(time.time() - total_start, 2)
            }, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            fast_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    # ===== 无知识直接拒答 =====
    if request.use_rag and not context:
        async def error_stream() -> AsyncIterable[str]:
            error_msg = "抱歉，目前知识库中暂无相关信息。"
            yield f"data: {json.dumps({'type': 'token', 'content': error_msg}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({
                'type': 'done',
                'content': error_msg,
                'sources': None,
                'response_time': round(time.time() - total_start, 2)
            }, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    # ===== 真正的流式生成（支持交叉验证）=====
    async def generate_stream() -> AsyncIterable[str]:
        error_occurred = False

        try:
            if request.verify:
                # 模式一：交叉验证模式 - 先生成完整答案并验证，再流式返回
                print("[API] ✅ 流式+交叉验证模式")
                safe_llm_service = get_safe_llm_service()
                
                # 调用验证服务获取完整答案
                verify_result = await safe_llm_service.ask_with_verification(
                    question=request.question,
                    context=context,
                    session_id=request.session_id
                )
                
                if not verify_result['success']:
                    error_occurred = True
                    yield f"data: {json.dumps({'type': 'error', 'content': verify_result.get('error', '验证失败')}, ensure_ascii=False)}\n\n"
                    return
                
                final_answer = verify_result['answer']
                confidence = verify_result.get('confidence', 0.0)
                verified_sentences = verify_result.get('verified_sentences', [])
                
                # 逐字流式返回验证后的答案
                for char in final_answer:
                    yield f"data: {json.dumps({'type': 'token', 'content': char}, ensure_ascii=False)}\n\n"
                
                # done事件返回验证信息
                sentiment = analyze_sentiment(request.question)
                try:
                    sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
                    save_conversation(
                        session_id=request.session_id or "unknown",
                        question=request.question,
                        answer=final_answer,
                        sources=sources_json,
                        response_time=time.time() - total_start,
                        sentiment=sentiment
                    )
                    print("[API] 验证流式对话记录已保存")
                except Exception as e:
                    print(f"[API] 保存验证流式记录失败: {e}")
                
                yield f"data: {json.dumps({
                    'type': 'done',
                    'content': final_answer,
                    'sources': sources if sources else None,
                    'response_time': round(time.time() - total_start, 2),
                    'confidence': confidence,
                    'verified_sentences': verified_sentences
                }, ensure_ascii=False)}\n\n"
            
            else:
                # 模式二：普通流式模式 - 直接流式生成
                full_answer = ""
                async for chunk in llm_service.astream_chat(
                    question=request.question,
                    context=context,
                    session_id=request.session_id
                ):
                    chunk_type = chunk.get("type")
                    content = chunk.get("content", "")

                    if chunk_type == "token":
                        full_answer += content
                        yield f"data: {json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"

                    elif chunk_type == "done":
                        final_answer = content
                        sentiment = analyze_sentiment(request.question)

                        try:
                            sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
                            save_conversation(
                                session_id=request.session_id or "unknown",
                                question=request.question,
                                answer=final_answer,
                                sources=sources_json,
                                response_time=time.time() - total_start,
                                sentiment=sentiment
                            )
                            print("[API] 流式对话记录已保存")
                        except Exception as e:
                            print(f"[API] 保存流式对话记录失败: {e}")

                        yield f"data: {json.dumps({
                            'type': 'done',
                            'content': final_answer,
                            'sources': sources if sources else None,
                            'response_time': round(time.time() - total_start, 2)
                        }, ensure_ascii=False)}\n\n"

                    elif chunk_type == "error":
                        error_occurred = True
                        yield f"data: {json.dumps({'type': 'error', 'content': content}, ensure_ascii=False)}\n\n"

        except Exception as e:
            print(f"[API] 流式响应异常: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/session/init")
async def init_session():
    """
    分配一个新的 session_id
    格式：lingshan_YYYYMMDD_XXXXXX（6位序号）
    """
    from models.database import SessionLocal, Conversation
    from datetime import datetime
    
    db = SessionLocal()
    try:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # 统计今日已有的会话数（按 session_id 去重）
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