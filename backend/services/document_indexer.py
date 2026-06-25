# -*- coding: utf-8 -*-
"""
文档索引服务：解析、分块、向量化并存入 Chroma
"""

import os
import re
from typing import List
from docx import Document as DocxDocument
import fitz  # PyMuPDF
import chromadb
from chromadb.utils import embedding_functions

# ===== 隐藏 Hugging Face 进度条 =====
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

# 配置
CHROMA_DB_PATH = "/var/www/Trapezius-driven-development-guide/backend/chroma_db"
COLLECTION_NAME = "lingshan_faq"
EMBEDDING_MODEL = "/home/ubuntu/.cache/sentence-transformers/local_model"

# ===== 懒加载：启动时不加载模型 =====
_embedding_fn = None

def get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
    return _embedding_fn

def get_collection():
    """获取已存在的 Chroma 集合（确保 embedding function 先加载）"""
    get_embedding_fn()  # 确保模型已加载
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client.get_collection(COLLECTION_NAME)

def extract_text_from_file(file_path: str, file_type: str) -> str:
    # ...（保持不变）...
    text = ""
    if file_type == "txt":
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    elif file_type == "docx":
        doc = DocxDocument(file_path)
        text = "\n".join([p.text for p in doc.paragraphs])
    elif file_type == "pdf":
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text() or ""
    else:
        raise ValueError(f"不支持的文件类型: {file_type}")
    return text

def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    # ...（保持不变）...
    paragraphs = [p for p in text.split("\n") if p.strip()]
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) <= chunk_size:
            current_chunk += para + "\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n"
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def index_document(doc_id: int, file_path: str, file_type: str, filename: str) -> int:
    """索引文档：提取文本 → 分块 → 向量化 → 存入 Chroma"""
    # 1. 获取 embedding function 和 collection（此时才真正加载模型）
    collection = get_collection()
    
    # 2. 提取文本
    raw_text = extract_text_from_file(file_path, file_type)
    if not raw_text.strip():
        print(f"[索引] 文档 {filename} 无文本内容，跳过")
        return 0

    # 3. 分块
    chunks = split_text(raw_text)
    print(f"[索引] 文档 {filename} 分 {len(chunks)} 块")

    # 4. 构造 metadata 和 ids
    metadatas = []
    ids = []
    documents = []
    for i, chunk in enumerate(chunks):
        question = chunk[:200] + ("..." if len(chunk) > 200 else "")
        metadata = {
            "type": "knowledge",
            "source_doc_id": str(doc_id),
            "source_file": filename,
            "chunk_index": i,
            "question": question,
            "answer": chunk
        }
        metadatas.append(metadata)
        documents.append(f"问题：{question}\n答案：{chunk}")
        ids.append(f"knowledge_{doc_id}_{i}")

    # 5. 分批添加
    batch_size = 50
    total = len(documents)
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        collection.add(
            documents=documents[start:end],
            metadatas=metadatas[start:end],
            ids=ids[start:end]
        )
        print(f"[索引] 已存入 {end}/{total} 块")

    return len(chunks)