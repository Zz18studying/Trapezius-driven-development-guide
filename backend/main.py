# -*- coding: utf-8 -*-
"""
FastAPI主入口
灵山胜境AI导游后端服务
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from routers import chat, health

# 创建FastAPI应用
app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description="基于RAG+DeepSeek的智能景区导览API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS（允许小程序调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router)
app.include_router(health.router)


# 启动事件
@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print(f"🚀 {config.API_TITLE} 启动中...")
    print(f"   版本: {config.API_VERSION}")
    print(f"   文档: http://{config.API_HOST}:{config.API_PORT}/docs")
    print("=" * 50)


# 根路径
@app.get("/")
async def root():
    return {
        "name": config.API_TITLE,
        "version": config.API_VERSION,
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True
    )