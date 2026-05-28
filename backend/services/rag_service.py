# -*- coding: utf-8 -*-
"""
RAG检索服务
负责从向量数据库检索相关知识
"""

import os
import sys
import chromadb

# 获取当前文件所在目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)

# 添加 backend 目录到路径
sys.path.insert(0, BACKEND_DIR)

# 使用绝对导入（从 backend 开始）
import config


class RAGService:
    """RAG检索服务类"""

    def __init__(self):
        self.client = None
        self.collection = None
        self._init_chroma()

    def _init_chroma(self):
        """初始化Chroma客户端"""
        try:
            if not os.path.exists(config.CHROMA_DB_PATH):
                print(f"⚠️ 向量数据库不存在: {config.CHROMA_DB_PATH}")
                print("   请先运行 scripts/03_build_vector_db.py")
                return

            self.client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
            self.collection = self.client.get_collection(config.COLLECTION_NAME)
            print(f"✅ RAG服务初始化成功")
            print(f"   数据库: {config.CHROMA_DB_PATH}")
            print(f"   集合: {config.COLLECTION_NAME}")
            print(f"   条目数: {self.collection.count()}")
        except Exception as e:
            print(f"❌ RAG服务初始化失败: {e}")

    def is_ready(self):
        return self.collection is not None

    def search(self, query: str, n_results: int = None):
        if not self.is_ready():
            return {"success": False, "results": [], "error": "向量数据库未就绪"}

        if n_results is None:
            n_results = config.DEFAULT_N_RESULTS
        n_results = min(n_results, config.MAX_N_RESULTS)

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )

            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                        results['documents'][0],
                        results['metadatas'][0],
                        results['distances'][0]
                )):
                    similarity = 1 - distance
                    if similarity >= config.MIN_SIMILARITY:
                        formatted_results.append({
                            "question": metadata.get('question', ''),
                            "answer": metadata.get('answer', ''),
                            "category": metadata.get('category', ''),
                            "similarity": round(similarity, 4),
                            "index": i + 1
                        })

            return {
                "success": True,
                "results": formatted_results,
                "total": len(formatted_results),
                "error": None
            }
        except Exception as e:
            return {"success": False, "results": [], "error": str(e)}

    def get_context(self, query: str, n_results: int = 3) -> str:
        result = self.search(query, n_results)
        if not result['success'] or not result['results']:
            return ""

        context_parts = []
        for i, r in enumerate(result['results'][:n_results], 1):
            context_parts.append(f"【参考{i}】\n问题：{r['question']}\n答案：{r['answer']}")

        return "\n\n".join(context_parts)


_rag_service = None


def get_rag_service():
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service