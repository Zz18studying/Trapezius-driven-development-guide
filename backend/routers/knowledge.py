# -*- coding: utf-8 -*-
"""
知识库管理路由 - 包含上传、列表、删除、测试检索
"""

import os
import chromadb
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import KnowledgeDocument, SessionLocal
from services.rag_service import get_rag_service

CHROMA_DB_PATH = "/var/www/Trapezius-driven-development-guide/backend/chroma_db"
COLLECTION_NAME = "lingshan_faq"

router = APIRouter(prefix="/api/admin/knowledge", tags=["知识库管理"])

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "knowledge")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class TestQueryRequest(BaseModel):
    question: str
    n_results: Optional[int] = 3


def allowed_file(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def update_document_status(doc_id: int, status: str, chunk_count: int = 0):
    """更新文档状态"""
    db = SessionLocal()
    try:
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
        if doc:
            doc.status = status
            doc.chunk_count = chunk_count
            db.commit()
    finally:
        db.close()


def background_index(doc_id: int, file_path: str, file_type: str, filename: str):
    """后台执行索引任务"""

    from services.document_indexer import index_document
    try:
        chunk_count = index_document(doc_id, file_path, file_type, filename)
        update_document_status(doc_id, "processed", chunk_count)
        print(f"[索引] 文档 {filename} 索引完成，共 {chunk_count} 块")
    except Exception as e:
        update_document_status(doc_id, "failed", 0)
        print(f"[索引] 文档 {filename} 索引失败: {e}")


@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型，仅支持: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    content = await file.read()
    file_size = len(content)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    db = SessionLocal()
    try:
        doc = KnowledgeDocument(
            filename=file.filename,
            file_path=file_path,
            file_type=os.path.splitext(file.filename)[1][1:],
            file_size=file_size,
            status="uploaded"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        if background_tasks:
            background_tasks.add_task(
                background_index,
                doc.id,
                file_path,
                doc.file_type,
                doc.filename
            )
            status_msg = "已加入索引队列"
        else:
            # 如果没有后台任务，同步处理（降级）
            try:
                chunk_count = index_document(doc.id, file_path, doc.file_type, doc.filename)
                doc.status = "processed"
                doc.chunk_count = chunk_count
                db.commit()
                status_msg = "上传并索引成功"
            except Exception as e:
                doc.status = "failed"
                db.commit()
                status_msg = f"索引失败: {str(e)}"

        return {
            "code": 0,
            "data": {
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "status": doc.status,
                "created_at": doc.created_at.isoformat()
            },
            "msg": status_msg
        }
    except Exception as e:
        db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
    finally:
        db.close()


@router.get("/list")
async def list_knowledge():
    """获取所有知识文档列表"""
    db = SessionLocal()
    try:
        docs = db.query(KnowledgeDocument).order_by(
            KnowledgeDocument.created_at.desc()
        ).all()
        result = []
        for doc in docs:
            result.append({
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "status": doc.status,
                "chunk_count": doc.chunk_count,
                "created_at": doc.created_at.isoformat()
            })
        return {
            "code": 0,
            "data": result,
            "msg": "success"
        }
    finally:
        db.close()


@router.delete("/{doc_id}")
async def delete_knowledge(doc_id: int):
    db = SessionLocal()
    try:
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 删除物理文件
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)

        # 删除 Chroma 中的向量
        try:
            client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            collection = client.get_collection(COLLECTION_NAME)
            collection.delete(where={"source_doc_id": str(doc_id)})
        except Exception as e:
            print(f"⚠️ 删除向量失败: {e}")

        db.delete(doc)
        db.commit()
        return {"code": 0, "data": None, "msg": "删除成功"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
    finally:
        db.close()


@router.post("/test")
async def test_knowledge_query(request: TestQueryRequest):
    """测试知识库问答检索"""
    rag_service = get_rag_service()
    if not rag_service.is_ready():
        return {
            "code": -1,
            "data": None,
            "msg": "RAG服务未就绪"
        }

    result = rag_service.search(request.question, request.n_results)
    if result["success"]:
        return {
            "code": 0,
            "data": {
                "question": request.question,
                "results": result["results"]
            },
            "msg": "success"
        }
    else:
        return {
            "code": -1,
            "data": None,
            "msg": result.get("error", "检索失败")
        }