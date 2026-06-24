# -*- coding: utf-8 -*-
"""
管理后台路由
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db_service import get_dashboard_stats, get_hot_topics_from_cache

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


@router.get("/dashboard/stats")
async def get_stats(days: int = 7):
    """获取仪表盘统计数据（KPI + 趋势）"""
    stats = get_dashboard_stats(days)
    return {
        "code": 0,
        "data": {
            "stats": stats,
            "hot_topics": get_hot_topics_from_cache(10)
        },
        "msg": "success"
    }


@router.get("/dashboard/hot-topics")
async def get_hot_topics(limit: int = 5):
    """获取热门话题 TOP N"""
    topics = get_hot_topics_from_cache(limit)
    return {
        "code": 0,
        "data": topics,
        "msg": "success"
    }


# 用于测试的模拟数据注入（如果数据库为空，可以返回模拟数据）
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