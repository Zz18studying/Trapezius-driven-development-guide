# -*- coding: utf-8 -*-
"""
管理后台路由
包含：仪表盘统计 + 游客感受度报告（情感分析、趋势、建议、高级报告）
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db_service import get_dashboard_stats
from services.topic_service import get_cached_topics

# ============================================================
# 游客感受度报告服务（新增）
# ============================================================
from services.sentiment_service import (
    get_sentiment_overview,
    get_sentiment_trend,
    get_high_risk_sessions,
    generate_suggestions,
    generate_advanced_report,
    get_session_history,
    get_session_sentiment_trajectory
)

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


# ============================================================
# 原有接口：仪表盘
# ============================================================
@router.get("/dashboard/stats")
async def get_stats(days: int = 7, limit: int = 10):
    """获取仪表盘统计数据（KPI + 趋势 + 热门话题）"""
    stats = get_dashboard_stats(days)
    topics = await get_cached_topics(limit)
    return {
        "code": 0,
        "data": {
            "stats": stats,
            "hot_topics": topics
        },
        "msg": "success"
    }


@router.get("/dashboard/hot-topics")
async def get_hot_topics(limit: int = 10):
    """获取热门话题 TOP N（增量汇总）"""
    topics = await get_cached_topics(limit)
    return {
        "code": 0,
        "data": topics,
        "msg": "success"
    }


# ============================================================
# 模拟数据接口（仅用于前端开发测试）
# ============================================================
@router.get("/dashboard/mock")
async def get_mock_data():
    """返回模拟数据用于前端开发测试"""
    mock_stats = {
        "total_conversations": 8732,
        "today_count": 324,
        "avg_response_time": 2.3,
        "daily_stats": [
            {"date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"),
             "count": 200 + i * 20} for i in range(6, -1, -1)
        ]
    }
    mock_topics = [
        {"topic": "开放时间", "count": 15},
        {"topic": "门票价格", "count": 12},
        {"topic": "交通路线", "count": 8},
        {"topic": "祈福体验", "count": 6},
        {"topic": "景点介绍", "count": 5}
    ]
    return {
        "code": 0,
        "data": {
            "stats": mock_stats,
            "hot_topics": mock_topics
        },
        "msg": "success (mock)"
    }


# ============================================================
# 游客感受度报告 API（比赛核心功能）
# ============================================================

@router.get("/sentiment/overview")
async def sentiment_overview(days: int = 7):
    """
    情感分析总览
    返回：总对话数、今日对话数、情感分布、占比、平均响应时间
    """
    data = get_sentiment_overview(days)
    return {"code": 0, "data": data, "msg": "success"}


@router.get("/sentiment/trend")
async def sentiment_trend(days: int = 7):
    """
    每日情感趋势
    返回：近 N 天每天的 positive/neutral/negative 数量
    """
    data = get_sentiment_trend(days)
    return {"code": 0, "data": data, "msg": "success"}


@router.get("/sentiment/hot-topics")
async def sentiment_hot_topics(limit: int = 10):
    """
    热门话题（复用词云数据）
    如果 topic_service 未就绪，返回空数组
    """
    try:
        topics = await get_cached_topics(limit)
        return {"code": 0, "data": topics, "msg": "success"}
    except Exception as e:
        print(f"[热门话题] 获取失败: {e}")
        return {"code": 0, "data": [], "msg": "话题服务未就绪"}


@router.get("/sentiment/suggestions")
async def sentiment_suggestions(days: int = 7):
    """
    生成服务改进建议（基于统计数据）
    返回：建议列表（含等级、标题、描述、行动项）
    """
    overview = get_sentiment_overview(days)
    trend = get_sentiment_trend(days)
    suggestions = generate_suggestions(overview, trend)
    return {"code": 0, "data": suggestions, "msg": "success"}


@router.get("/sentiment/high-risk")
async def high_risk_sessions(days: int = 7, threshold: int = 2):
    """
    获取高风险会话列表（情绪持续下降）
    threshold: 负面情绪出现次数阈值，默认2次
    """
    data = get_high_risk_sessions(days, threshold)
    return {"code": 0, "data": data, "msg": "success"}


@router.get("/sentiment/session/{session_id}/history")
async def session_history(session_id: str):
    """
    查看某个会话的完整对话记录（按时间排序）
    返回：每轮的 question/answer/sentiment/created_at
    """
    data = get_session_history(session_id)
    return {"code": 0, "data": data, "msg": "success"}


@router.get("/sentiment/session/{session_id}/trajectory")
async def session_trajectory(session_id: str):
    """
    查看某个会话的情绪轨迹
    返回：起始情绪、结束情绪、变化方向（improving/declining/stable）、完整轨迹
    """
    data = get_session_sentiment_trajectory(session_id)
    return {"code": 0, "data": data, "msg": "success"}


@router.get("/sentiment/advanced-report")
async def advanced_report(days: int = 7):
    """
    【比赛亮点】高级报告：表格描述 + Prompt 结合
    用 LLM 生成自然语言的管理报告，包含：
    - 满意度总体评价
    - 情绪变化趋势分析
    - 重点问题与风险预警
    - 具体改进建议
    
    返回：raw_data（原始统计数据）+ report_text（LLM 生成的文字报告）
    """
    data = generate_advanced_report(days)
    return {"code": 0, "data": data, "msg": "success"}