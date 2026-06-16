# -*- coding: utf-8 -*-
"""
数据库操作服务
"""

import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from backend.models.database import (
    Conversation, KnowledgeDocument, DigitalHumanConfig, SessionLocal, init_db
)


def get_db_session():
    """获取数据库会话"""
    return SessionLocal()


def init_database():
    """初始化数据库"""
    init_db()
    print("✅ 数据库初始化完成")


# ==================== 对话记录 ====================
def save_conversation(session_id: str, question: str, answer: str, 
                      sources: list = None, response_time: float = 0.0,
                      sentiment: str = None):
    """保存对话记录"""
    db = get_db_session()
    try:
        conv = Conversation(
            session_id=session_id,
            user_question=question,
            ai_answer=answer,
            sources=json.dumps(sources, ensure_ascii=False) if sources else None,
            response_time=response_time,
            sentiment=sentiment
        )
        db.add(conv)
        db.commit()
        return conv.id
    finally:
        db.close()


def get_conversations(limit: int = 100, offset: int = 0):
    """获取对话列表"""
    db = get_db_session()
    try:
        total = db.query(Conversation).count()
        items = db.query(Conversation).order_by(desc(Conversation.created_at)).offset(offset).limit(limit).all()
        return {
            "total": total,
            "items": [{
                "id": c.id,
                "session_id": c.session_id,
                "question": c.user_question,
                "answer": c.ai_answer[:100] + "..." if len(c.ai_answer) > 100 else c.ai_answer,
                "sentiment": c.sentiment,
                "response_time": c.response_time,
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S")
            } for c in items]
        }
    finally:
        db.close()


def get_dashboard_stats(days: int = 7):
    """获取仪表盘统计数据"""
    db = get_db_session()
    try:
        # 总对话数
        total_conversations = db.query(Conversation).count()
        
        # 今日对话数
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = db.query(Conversation).filter(Conversation.created_at >= today).count()
        
        # 平均响应时间
        avg_time = db.query(func.avg(Conversation.response_time)).scalar() or 0
        
        # 近 N 天每日统计
        daily_stats = []
        for i in range(days - 1, -1, -1):
            date = datetime.now() - timedelta(days=i)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            count = db.query(Conversation).filter(
                Conversation.created_at >= date_start,
                Conversation.created_at <= date_end
            ).count()
            daily_stats.append({
                "date": date.strftime("%Y-%m-%d"),
                "count": count
            })
        
        # 情感分布
        sentiment_stats = {
            "positive": db.query(Conversation).filter(Conversation.sentiment == "positive").count(),
            "neutral": db.query(Conversation).filter(Conversation.sentiment == "neutral").count(),
            "negative": db.query(Conversation).filter(Conversation.sentiment == "negative").count()
        }
        
        return {
            "total_conversations": total_conversations,
            "today_count": today_count,
            "avg_response_time": round(avg_time, 2),
            "daily_stats": daily_stats,
            "sentiment_stats": sentiment_stats
        }
    finally:
        db.close()


def get_hot_questions(limit: int = 10):
    """获取热门问题"""
    db = get_db_session()
    try:
        # 使用 SQL 分组统计
        results = db.query(
            Conversation.user_question,
            func.count(Conversation.id).label("count")
        ).group_by(Conversation.user_question).order_by(desc("count")).limit(limit).all()
        
        return [{"question": r[0], "count": r[1]} for r in results]
    finally:
        db.close()


# ==================== 知识文档 ====================
def save_document(filename: str, file_path: str, file_type: str, file_size: int):
    """保存知识文档记录"""
    db = get_db_session()
    try:
        doc = KnowledgeDocument(
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size
        )
        db.add(doc)
        db.commit()
        return doc.id
    finally:
        db.close()


def get_documents():
    """获取所有文档"""
    db = get_db_session()
    try:
        docs = db.query(KnowledgeDocument).order_by(desc(KnowledgeDocument.created_at)).all()
        return [{
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "status": d.status,
            "chunk_count": d.chunk_count,
            "created_at": d.created_at.strftime("%Y-%m-%d %H:%M:%S")
        } for d in docs]
    finally:
        db.close()


def delete_document(doc_id: int):
    """删除文档记录"""
    db = get_db_session()
    try:
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
        if doc:
            # 同时删除物理文件
            import os
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
            db.delete(doc)
            db.commit()
            return True
        return False
    finally:
        db.close()


def update_document_status(doc_id: int, status: str, chunk_count: int = None):
    """更新文档状态"""
    db = get_db_session()
    try:
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
        if doc:
            doc.status = status
            if chunk_count is not None:
                doc.chunk_count = chunk_count
            db.commit()
            return True
        return False
    finally:
        db.close()


# ==================== 数字人配置 ====================
def get_config(key: str, default=None):
    """获取配置"""
    db = get_db_session()
    try:
        config = db.query(DigitalHumanConfig).filter(
            DigitalHumanConfig.config_key == key
        ).first()
        return config.config_value if config else default
    finally:
        db.close()


def set_config(key: str, value: str):
    """设置配置"""
    db = get_db_session()
    try:
        config = db.query(DigitalHumanConfig).filter(
            DigitalHumanConfig.config_key == key
        ).first()
        if config:
            config.config_value = value
        else:
            config = DigitalHumanConfig(config_key=key, config_value=value)
            db.add(config)
        db.commit()
        return True
    finally:
        db.close()


def get_all_configs():
    """获取所有配置"""
    db = get_db_session()
    try:
        configs = db.query(DigitalHumanConfig).all()
        return {c.config_key: c.config_value for c in configs}
    finally:
        db.close()