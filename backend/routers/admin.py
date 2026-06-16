# -*- coding: utf-8 -*-
"""
管理后台路由
"""

import os
import json
import time
import shutil
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body
from pydantic import BaseModel
from typing import Optional, List
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db_service import (
    get_dashboard_stats, get_hot_questions, get_conversations,
    save_document, get_documents, delete_document, update_document_status,
    get_config, set_config, get_all_configs, save_conversation
)
from services.rag_service import get_rag_service
from services.llm_service import get_llm_service

router = APIRouter(prefix="/api/admin", tags=["管理后台"])

# ==================== 请求/响应模型 ====================
class ConfigUpdateRequest(BaseModel):
    model_path: Optional[str] = None
    voice_type: Optional[int] = None
    model_scale: Optional[float] = None
    background_color: Optional[str] = None


class TestQARequest(BaseModel):
    question: str


class SentimentStatsRequest(BaseModel):
    days: Optional[int] = 7


# ==================== 1. 数据大屏概览 ====================
@router.get("/dashboard/stats")
async def get_stats(days: int = 7):
    """获取仪表盘统计数据"""
    stats = get_dashboard_stats(days)
    hot_questions = get_hot_questions(10)
    
    return {
        "code": 0,
        "data": {
            "stats": stats,
            "hot_questions": hot_questions
        },
        "msg": "success"
    }


@router.get("/dashboard/daily")
async def get_daily_stats(days: int = 7):
    """获取每日统计数据"""
    stats = get_dashboard_stats(days)
    return {
        "code": 0,
        "data": {
            "daily_stats": stats.get("daily_stats", [])
        },
        "msg": "success"
    }


@router.get("/dashboard/hot-questions")
async def get_hot_questions_api(limit: int = 10):
    """获取热门问题"""
    questions = get_hot_questions(limit)
    return {
        "code": 0,
        "data": questions,
        "msg": "success"
    }


@router.get("/conversations")
async def get_conversations_api(limit: int = 100, offset: int = 0):
    """获取对话记录列表"""
    data = get_conversations(limit, offset)
    return {
        "code": 0,
        "data": data,
        "msg": "success"
    }


# ==================== 2. 知识库管理 ====================
@router.post("/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    auto_process: bool = Form(True)
):
    """上传知识文档"""
    try:
        # 检查文件类型
        allowed_types = [".pdf", ".docx", ".txt", ".md"]
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_types:
            return {
                "code": -1,
                "data": None,
                "msg": f"不支持的文件类型，请上传: {', '.join(allowed_types)}"
            }
        
        # 保存文件
        upload_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "uploads", "knowledge"
        )
        os.makedirs(upload_dir, exist_ok=True)
        
        timestamp = int(time.time())
        saved_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, saved_filename)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            file_size = len(content)
        
        # 保存记录
        doc_id = save_document(
            filename=file.filename,
            file_path=file_path,
            file_type=file_ext[1:],
            file_size=file_size
        )
        
        # TODO: 自动处理文档（分割 + 向量化）
        # 这里可以调用异步任务处理
        
        return {
            "code": 0,
            "data": {
                "id": doc_id,
                "filename": file.filename,
                "file_type": file_ext[1:],
                "file_size": file_size,
                "status": "uploaded"
            },
            "msg": "上传成功"
        }
    except Exception as e:
        return {
            "code": -1,
            "data": None,
            "msg": f"上传失败: {str(e)}"
        }


@router.get("/knowledge/list")
async def get_knowledge_list():
    """获取知识文档列表"""
    docs = get_documents()
    return {
        "code": 0,
        "data": docs,
        "msg": "success"
    }


@router.delete("/knowledge/{doc_id}")
async def delete_knowledge(doc_id: int):
    """删除知识文档"""
    success = delete_document(doc_id)
    if success:
        return {
            "code": 0,
            "data": None,
            "msg": "删除成功"
        }
    else:
        return {
            "code": -1,
            "data": None,
            "msg": "文档不存在"
        }


@router.post("/knowledge/rebuild")
async def rebuild_vector_store():
    """重新构建向量库"""
    try:
        # 这里调用 rag_service 的重新构建方法
        # 实际项目中可能需要调用 scripts/03_build_vector_db.py
        return {
            "code": 0,
            "data": {"status": "started"},
            "msg": "向量库重建任务已启动，请稍后查看结果"
        }
    except Exception as e:
        return {
            "code": -1,
            "data": None,
            "msg": f"重建失败: {str(e)}"
        }


@router.post("/knowledge/test")
async def test_knowledge_search(request: TestQARequest):
    """测试知识检索"""
    rag_service = get_rag_service()
    
    if not rag_service.is_ready():
        return {
            "code": -1,
            "data": None,
            "msg": "RAG服务未就绪"
        }
    
    result = rag_service.search(request.question, 5)
    
    if result['success']:
        return {
            "code": 0,
            "data": {
                "question": request.question,
                "results": result['results']
            },
            "msg": "success"
        }
    else:
        return {
            "code": -1,
            "data": None,
            "msg": result.get('error', '检索失败')
        }


# ==================== 3. 游客感受度报告 ====================
@router.get("/sentiment/overview")
async def get_sentiment_overview(days: int = 7):
    """获取情感分析总览"""
    stats = get_dashboard_stats(days)
    
    return {
        "code": 0,
        "data": {
            "sentiment_stats": stats.get("sentiment_stats", {}),
            "total_conversations": stats.get("total_conversations", 0),
            "daily_stats": stats.get("daily_stats", [])
        },
        "msg": "success"
    }


@router.get("/sentiment/trend")
async def get_sentiment_trend(days: int = 7):
    """获取情感趋势数据"""
    # 实际项目需要从数据库查询每日情感分布
    # 这里返回模拟数据供前端展示
    from datetime import timedelta
    
    trend = []
    for i in range(days - 1, -1, -1):
        date = datetime.now() - timedelta(days=i)
        trend.append({
            "date": date.strftime("%Y-%m-%d"),
            "positive": 5 + i % 3,
            "neutral": 10 + i % 2,
            "negative": 2 + i % 2
        })
    
    return {
        "code": 0,
        "data": trend,
        "msg": "success"
    }


@router.get("/sentiment/hot-topics")
async def get_hot_topics(limit: int = 10):
    """获取热门话题"""
    questions = get_hot_questions(limit)
    return {
        "code": 0,
        "data": questions,
        "msg": "success"
    }


@router.get("/sentiment/suggestions")
async def get_service_suggestions():
    """获取服务建议"""
    # 基于情感分析生成建议
    stats = get_dashboard_stats(7)
    sentiment = stats.get("sentiment_stats", {})
    negative_rate = sentiment.get("negative", 0) / max(stats.get("total_conversations", 1), 1)
    
    suggestions = []
    
    if negative_rate > 0.2:
        suggestions.append({
            "level": "high",
            "title": "游客满意度偏低",
            "description": f"近7天负面反馈占比 {negative_rate*100:.1f}%，建议检查知识库完整性并优化回答质量",
            "action": "更新FAQ知识库"
        })
    
    # 热门问题分析
    hot = get_hot_questions(3)
    if hot:
        suggestions.append({
            "level": "medium",
            "title": f"高频问题: {hot[0].get('question', '')[:20]}...",
            "description": f"该问题被提问 {hot[0].get('count', 0)} 次，建议优化相关回答",
            "action": "优化知识库条目"
        })
    
    if stats.get("total_conversations", 0) < 10:
        suggestions.append({
            "level": "low",
            "title": "数据量较少",
            "description": "当前对话数据较少，建议增加测试数据以获得更准确的分析",
            "action": "增加测试数据"
        })
    
    return {
        "code": 0,
        "data": suggestions,
        "msg": "success"
    }


@router.get("/sentiment/export")
async def export_sentiment_report():
    """导出情感报告（CSV格式）"""
    # 实际项目中生成 CSV 文件
    # 这里返回模拟数据
    return {
        "code": 0,
        "data": {
            "url": "/api/admin/sentiment/report.csv",
            "message": "报告生成中，请稍后下载"
        },
        "msg": "success"
    }


# ==================== 4. 数字人形象管理 ====================
@router.get("/dh/config")
async def get_dh_config():
    """获取数字人配置"""
    configs = get_all_configs()
    
    default_config = {
        "model_path": configs.get("dh_model_path", "/models/shizuku/runtime/shizuku.model3.json"),
        "voice_type": int(configs.get("dh_voice_type", "0")),
        "model_scale": float(configs.get("dh_model_scale", "0.35")),
        "background_color": configs.get("dh_background_color", "#2d4a1e")
    }
    
    return {
        "code": 0,
        "data": default_config,
        "msg": "success"
    }


@router.put("/dh/config")
async def update_dh_config(request: ConfigUpdateRequest):
    """更新数字人配置"""
    if request.model_path is not None:
        set_config("dh_model_path", request.model_path)
    if request.voice_type is not None:
        set_config("dh_voice_type", str(request.voice_type))
    if request.model_scale is not None:
        set_config("dh_model_scale", str(request.model_scale))
    if request.background_color is not None:
        set_config("dh_background_color", request.background_color)
    
    return {
        "code": 0,
        "data": None,
        "msg": "配置更新成功"
    }


@router.get("/dh/models")
async def get_available_models():
    """获取可用的模型列表"""
    models_dir = "/var/www/Trapezius-driven-development-guide/models"
    models = []
    
    if os.path.exists(models_dir):
        for item in os.listdir(models_dir):
            model_path = os.path.join(models_dir, item)
            if os.path.isdir(model_path):
                # 查找 .model3.json 文件
                for root, dirs, files in os.walk(model_path):
                    for f in files:
                        if f.endswith(".model3.json"):
                            models.append({
                                "name": item,
                                "path": f"/models/{item}/{f}",
                                "display_name": item.capitalize()
                            })
                            break
    
    if not models:
        # 如果找不到，返回默认选项
        models = [
            {"name": "Shizuku", "path": "/models/shizuku/runtime/shizuku.model3.json", "display_name": "雫 (Shizuku)"},
            {"name": "Haru", "path": "/models/haru/haru.model3.json", "display_name": "Haru"},
            {"name": "Hiyori", "path": "/models/hiyori/hiyori.model3.json", "display_name": "Hiyori"}
        ]
    
    return {
        "code": 0,
        "data": models,
        "msg": "success"
    }


@router.get("/dh/voices")
async def get_available_voices():
    """获取可用的语音列表"""
    voices = [
        {"id": 0, "name": "普通女声", "description": "温柔清晰的女声"},
        {"id": 1, "name": "普通男声", "description": "沉稳男声"},
        {"id": 3, "name": "情感女声", "description": "富有感情的女声"}
    ]
    
    return {
        "code": 0,
        "data": voices,
        "msg": "success"
    }