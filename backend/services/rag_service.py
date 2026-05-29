# -*- coding: utf-8 -*-
"""
RAG检索服务 - 带模型预热功能
"""

import os
import sys
import time
import chromadb
from chromadb.utils import embedding_functions

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class RAGService:
    """RAG检索服务类"""

    def __init__(self):
        self.client = None
        self.collection = None
        self._init_chroma()
        # 预热模型：在启动时就加载，避免第一次请求慢
        self._warmup()

    def _init_chroma(self):
        """初始化Chroma客户端"""
        try:
            if not os.path.exists(config.CHROMA_DB_PATH):
                print(f"⚠️ 向量数据库不存在: {config.CHROMA_DB_PATH}")
                return

            self.client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
            self.collection = self.client.get_collection(config.COLLECTION_NAME)
            print(f"✅ RAG服务初始化成功")
            print(f"   数据库: {config.CHROMA_DB_PATH}")
            print(f"   集合: {config.COLLECTION_NAME}")
            print(f"   条目数: {self.collection.count()}")
        except Exception as e:
            print(f"❌ RAG服务初始化失败: {e}")

    def _warmup(self):
        """预热模型：在启动时加载，避免第一次请求慢"""
        print("🔥 预热模型中...")
        try:
            # 执行一次空检索，让模型加载到内存
            self.collection.query(query_texts=["测试"], n_results=1)
            print("✅ 模型预热完成")
        except Exception as e:
            print(f"⚠️ 模型预热失败: {e}")

    def is_ready(self):
        return self.collection is not None

    def search(self, query: str, n_results: int = None):
        if not self.is_ready():
            return {"success": False, "results": [], "error": "向量数据库未就绪"}

        if n_results is None:
            n_results = config.DEFAULT_N_RESULTS
        n_results = min(n_results, config.MAX_N_RESULTS)

        try:
            start = time.time()
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            elapsed = time.time() - start
            print(f"[RAG] 检索耗时: {elapsed:.2f}秒")

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
            print(f"[RAG] 检索失败: {e}")
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
