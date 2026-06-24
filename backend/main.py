# -*- coding: utf-8 -*-
"""
FastAPI主入口
灵山胜境AI导游后端服务
"""

import os
import sys
import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from routers import chat, health, voice,admin
from models.database import init_db                    # 添加数据库初始化
from services.rag_service import get_rag_service
from services.llm_service import get_llm_service


# ==================== 生命周期管理 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    启动时：预热模型 + 清理旧音频
    关闭时：清理资源
    """
    print("=" * 60)
    print(f"🚀 {config.API_TITLE} 启动中...")
    print(f"   版本: {config.API_VERSION}")
    print(f"   文档: http://{config.API_HOST}:{config.API_PORT}/docs")
    print("=" * 60)

    # ====== 1. 清理旧音频文件 ======
    print("\n🗑️ 清理旧音频文件...")
    audio_dir = "/var/www/Trapezius-driven-development-guide/backend/audio"
    if os.path.exists(audio_dir):
        now = time.time()
        deleted = 0
        for filename in os.listdir(audio_dir):
            filepath = os.path.join(audio_dir, filename)
            if os.path.isfile(filepath) and filename.endswith('.mp3'):
                # 删除1小时以上的旧文件
                if now - os.path.getmtime(filepath) > 3600:
                    try:
                        os.remove(filepath)
                        deleted += 1
                    except Exception as e:
                        print(f"   ⚠️ 删除失败: {filename} - {e}")
        print(f"   ✅ 清理了 {deleted} 个旧音频文件")
    else:
        print(f"   ℹ️ 音频目录不存在，跳过清理")

    # ====== 2. 预热 RAG 服务 ======
    print("\n🔥 预热 RAG 服务...")
    try:
        rag = get_rag_service()
        if rag.is_ready():
            print(f"   ✅ RAG 服务预热完成 (共 {rag.collection.count()} 条知识)")
        else:
            print("   ⚠️ RAG 服务未就绪")
    except Exception as e:
        print(f"   ❌ RAG 预热失败: {e}")

    # ====== 3. 预热 LLM 服务 ======
    print("\n🔥 预热 LLM 服务...")
    try:
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
 # ====== 4. 初始化数据库 ======
    print("\n🗄️ 初始化数据库...")
    try:
        init_db()
        print("   ✅ 数据库初始化完成")
    except Exception as e:
        print(f"   ❌ 数据库初始化失败: {e}")

    # ====== 5. 启动话题缓存定时任务 ======
    print("\n🔄 启动话题缓存定时任务...")
    asyncio.create_task(background_topic_updater())
    print("   ✅ 话题缓存任务已启动（每30分钟更新一次）")

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


# ==================== CORS 配置 ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "https://lingshanai.cn",
        "http://lingshanai.cn",
        "https://www.lingshanai.cn",
        "http://www.lingshanai.cn",
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
app.include_router(admin.router)

# ==================== 根路径 ====================
@app.get("/")
async def root():
    return {
        "name": config.API_TITLE,
        "version": config.API_VERSION,
        "status": "running",
        "docs": "/docs"
    }

# ==================== 后台定时任务 ====================
async def background_topic_updater():
    from services.topic_service import update_hot_topics_cache
    # 首次启动后立即更新一次
    await update_hot_topics_cache()
    # 之后每30分钟更新一次
    while True:
        await asyncio.sleep(1800)  # 30分钟
        await update_hot_topics_cache()

# ==================== 启动入口 ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True
    )