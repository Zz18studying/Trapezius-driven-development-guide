# -*- coding: utf-8 -*-
"""
数据库操作服务
"""

import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models.database import Conversation, HotTopicCache, get_db


def save_conversation(session_id: str, question: str, answer: str,
                      sources: list = None, response_time: float = 0.0,
                      sentiment: str = None):
    """保存对话记录"""
    db = next(get_db())
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


def get_dashboard_stats(days: int = 7):
    """获取仪表盘统计数据（KPI 和每日趋势）"""
    db = next(get_db())
    try:
        # 总对话数
        total = db.query(Conversation).count()

        # 今日对话数
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = db.query(Conversation).filter(Conversation.created_at >= today).count()

        # 平均响应时间
        avg_time = db.query(func.avg(Conversation.response_time)).scalar() or 0

        # 近 days 天每日统计
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

        return {
            "total_conversations": total,
            "today_count": today_count,
            "avg_response_time": round(avg_time, 2),
            "daily_stats": daily_stats
        }
    finally:
        db.close()


def get_hot_topics_from_cache(limit: int = 5):
    """从缓存表获取热门话题"""
    db = next(get_db())
    try:
        topics = db.query(HotTopicCache).order_by(HotTopicCache.count.desc()).limit(limit).all()
        return [{"topic": t.topic, "count": t.count} for t in topics]
    finally:
        db.close()


def update_hot_topic_cache(topics: list):
    """更新话题缓存（全量替换）"""
    db = next(get_db())
    try:
        # 清空旧缓存
        db.query(HotTopicCache).delete()
        # 插入新数据
        for item in topics:
            cache = HotTopicCache(
                topic=item["topic"],
                count=item["count"],
                keywords=json.dumps(item.get("keywords", []), ensure_ascii=False)
            )
            db.add(cache)
        db.commit()
    finally:
        db.close()