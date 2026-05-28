# -*- coding: utf-8 -*-
"""
健康检查路由
"""

from fastapi import APIRouter
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, BACKEND_DIR)

from services.rag_service import get_rag_service
from services.llm_service import get_llm_service

router = APIRouter(tags=["健康检查"])


@router.get("/")
async def root():
    return {"name": "灵山胜境AI导游API", "version": "1.0.0", "status": "running"}


@router.get("/health")
async def health():
    rag_service = get_rag_service()
    llm_service = get_llm_service()

    rag_ready = rag_service.is_ready()
    llm_ready = llm_service.is_ready()

    return {
        "status": "ok" if (rag_ready and llm_ready) else "degraded",
        "services": {
            "rag": {"ready": rag_ready, "count": rag_service.collection.count() if rag_ready else 0},
            "llm": {"ready": llm_ready, "model": llm_service.model if llm_ready else None}
        }
    }