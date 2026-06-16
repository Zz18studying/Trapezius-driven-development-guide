# -*- coding: utf-8 -*-
"""
FastAPI主入口
灵山胜境AI导游后端服务
"""

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from routers import chat, health, voice
from services.rag_service import get_rag_service
from services.llm_service import get_llm_service


# ==================== 生命周期管理（启动预热） ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    启动时自动预热模型，避免首次请求卡顿
    """
    print("=" * 60)
    print(f"🚀 {config.API_TITLE} 启动中...")
    print(f"   版本: {config.API_VERSION}")
    print(f"   文档: http://{config.API_HOST}:{config.API_PORT}/docs")
    print("=" * 60)

    # ====== 预热模型 ======
    print("\n🔥 正在预热模型，首次访问将不再卡顿...")

    # 1. 预热 RAG 服务
    try:
        print("   📚 加载 RAG 知识库...")
        rag = get_rag_service()
        if rag.is_ready():
            print(f"   ✅ RAG 服务预热完成 (共 {rag.collection.count()} 条知识)")
        else:
            print("   ⚠️ RAG 服务未就绪")
    except Exception as e:
        print(f"   ❌ RAG 预热失败: {e}")

    # 2. 预热 LLM 服务
    try:
        print("   🤖 加载 LLM 模型...")
        llm = get_llm_service()
        if llm.is_ready():
            print("   🔄 发送预热请求...")
            result = llm.chat("你好", context="")
            if result.get("success"):
                print("   ✅ LLM 服务预热完成")
            else:
                print(f"   ⚠️ LLM 预热异常: {result.get('error', '未知错误')}")
        else:
            print("   ⚠️ LLM 服务未就绪")
    except Exception as e:
        print(f"   ❌ LLM 预热失败: {e}")

    print("\n✅ 服务已完全启动，可以处理请求了！")
    print("=" * 60)

    yield  # 服务运行中

    # ====== 关闭时执行 ======
    print("\n🛑 服务正在关闭...")


# ==================== 创建 FastAPI 应用 ====================
app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description="基于RAG+DeepSeek的智能景区导览API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# ==================== CORS 配置（允许域名访问） ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://lingshanai.cn",
        "http://lingshanai.cn",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 静态文件目录（音频） ====================
audio_dir = "/var/www/Trapezius-driven-development-guide/backend/audio"
os.makedirs(audio_dir, exist_ok=True)
app.mount("/audio", StaticFiles(directory=audio_dir), name="audio")


# ==================== 注册路由 ====================
app.include_router(chat.router)
app.include_router(health.router)
app.include_router(voice.router)


# ==================== 根路径 ====================
@app.get("/")
async def root():
    return {
        "name": config.API_TITLE,
        "version": config.API_VERSION,
        "status": "running",
        "docs": "/docs"
    }


# ==================== 启动入口 ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True
    )