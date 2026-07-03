# -*- coding: utf-8 -*-
"""
RAG 检索服务。
"""

import os
import sys
import time
import chromadb
from chromadb.utils import embedding_functions

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from services.knowledge_constants import extract_attraction_name
from services.local_embedding import SimpleChineseEmbeddingFunction
from services.retrieval_ranker import INTENT_KEYWORDS, detect_intents, rerank_candidates


class RAGService:
    """RAG 检索服务类。"""

    def __init__(self):
        self.client = None
        self.collection = None
        self._init_chroma()
        self._warmup()

    def _get_embedding_function(self):
        candidates = [
            "/home/ubuntu/.cache/sentence-transformers/local_model",
            os.path.join(os.path.expanduser("~"), ".cache", "sentence-transformers", "local_model"),
        ]
        for local_model_path in candidates:
            if os.path.exists(local_model_path):
                return embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=local_model_path
                )
        print("⚠️ 未找到本地 sentence-transformers 模型，使用离线中文 n-gram 向量兜底")
        return SimpleChineseEmbeddingFunction()

    def _init_chroma(self):
        try:
            if not os.path.exists(config.CHROMA_DB_PATH):
                print(f"⚠️ 向量数据库不存在: {config.CHROMA_DB_PATH}")
                print("   正在自动创建...")
                os.makedirs(config.CHROMA_DB_PATH, exist_ok=True)

            self.client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
            embedding_fn = self._get_embedding_function()

            self.collection = self._get_or_create_collection(embedding_fn)

            print("✅ RAG服务初始化成功")
            print(f"   数据库: {config.CHROMA_DB_PATH}")
            print(f"   集合: {config.COLLECTION_NAME}")
            print(f"   条目数: {self.collection.count()}")

            if self.collection.count() == 0:
                print("⚠️ 数据库为空，请运行以下脚本填充数据:")
                print("   1. python scripts/01_extract_and_merge_data.py")
                print("   2. python scripts/02_generate_faq.py")
                print("   3. python scripts/03_build_vector_db.py")
        except Exception as e:
            print(f"❌ RAG服务初始化失败: {e}")

    def _get_or_create_collection(self, embedding_fn):
        try:
            return self.client.get_collection(
                config.COLLECTION_NAME,
                embedding_function=embedding_fn
            )
        except Exception:
            print(f"⚠️ 集合 {config.COLLECTION_NAME} 不存在，正在创建...")

        try:
            return self.client.create_collection(
                name=config.COLLECTION_NAME,
                embedding_function=embedding_fn
            )
        except Exception as create_error:
            if "already exists" in str(create_error).lower():
                return self.client.get_collection(
                    config.COLLECTION_NAME,
                    embedding_function=embedding_fn
                )
            raise create_error

    def _warmup(self):
        if not self.collection:
            return
        print("🔥 预热模型中...")
        try:
            self.collection.query(query_texts=["测试"], n_results=1)
            print("✅ 模型预热完成")
        except Exception as e:
            print(f"⚠️ 模型预热失败: {e}")

    def is_ready(self):
        return self.collection is not None

    def _detect_intents(self, query: str) -> set:
        return detect_intents(query)

    def _expand_question(self, query: str) -> list:
        """生成少量高价值检索变体，避免过度扩展带来噪声。"""
        queries = [query.strip()]
        name = extract_attraction_name(query)
        intents = self._detect_intents(query)

        if name:
            templates = {
                "time": f"{name} 开放时间 营业时间",
                "price": f"{name} 门票 票价 价格",
                "route": f"{name} 怎么去 交通 路线",
                "feature": f"{name} 特色 看点 亮点",
                "size": f"{name} 高度 尺寸 面积",
                "performance": f"{name} 演出 表演 场次 时间",
            }
            for intent in intents:
                if intent in templates:
                    queries.append(templates[intent])
            queries.append(name)

        if "price" in intents:
            queries.extend(["灵山胜境门票多少钱", "票务价格 成人票 半价票 免票 观光车"])
        if "parent" in intents:
            queries.extend(["亲子游怎么玩", "亲子家庭路线 孩子 儿童"])
        if "rain" in intents:
            queries.extend(["雨天适合去哪", "室内景点 馆内 展厅"])
        if "elder" in intents:
            queries.extend(["老人游怎么玩", "观光车 体力有限 老人"])
        if "quick" in intents:
            queries.extend(["半天怎么玩", "快速游 轻松游 路线规划"])

        if "吗" in query and len(query) > 3:
            queries.append(query.replace("吗", ""))

        seen = set()
        result = []
        for q in queries:
            q = q.strip()
            if q and q not in seen:
                seen.add(q)
                result.append(q)
        return result[:4]

    def _rerank(self, candidates: list, query: str) -> list:
        results = rerank_candidates(candidates, query)

        if results:
            top = results[0]
            print(
                f"[RAG] top1: {top.get('question', '')} | "
                f"向量={top.get('vector_similarity', 0):.4f}, 关键词={top.get('keyword_score', 0):.2f}, 总分={top.get('final_score', 0):.2f}"
            )

        return results

    def search(self, query: str, n_results: int = None):
        if not self.is_ready():
            return {"success": False, "results": [], "total": 0, "error": "向量数据库未就绪"}

        if n_results is None:
            n_results = config.DEFAULT_N_RESULTS
        n_results = max(1, min(n_results, config.MAX_N_RESULTS))

        try:
            start = time.time()
            expanded_queries = self._expand_question(query)
            if len(expanded_queries) > 1:
                print(f"[RAG] 扩展检索({len(expanded_queries)}): {expanded_queries}")

            candidates = []
            per_query_count = min(max(n_results * 12, 30), 80)
            for q in expanded_queries:
                raw = self.collection.query(query_texts=[q], n_results=per_query_count)
                documents = raw.get("documents", [[]])[0] or []
                metadatas = raw.get("metadatas", [[]])[0] or []
                distances = raw.get("distances", [[]])[0] or []
                for doc, metadata, distance in zip(documents, metadatas, distances):
                    candidates.append({
                        "type": metadata.get("type", ""),
                        "question": metadata.get("question", ""),
                        "answer": metadata.get("answer", ""),
                        "category": metadata.get("category", ""),
                        "attraction_name": metadata.get("attraction_name", ""),
                        "source": metadata.get("source", ""),
                        "source_type": metadata.get("source_type", ""),
                        "source_attraction": metadata.get("source_attraction", ""),
                        "vector_similarity": 1 - distance,
                        "doc": doc
                    })

            candidates.extend(self._exact_attraction_candidates(query))
            reranked = self._rerank(candidates, query)
            elapsed = time.time() - start
            print(f"[RAG] 检索耗时: {elapsed:.2f}秒, 候选数: {len(candidates)}")

            threshold = config.MIN_SIMILARITY
            fallback_threshold = getattr(config, "FALLBACK_SIMILARITY", 0.25)
            filtered = [
                item for item in reranked
                if item.get("final_score", 0) >= threshold
            ]

            if not filtered and reranked:
                print(f"[RAG] 标准阈值无结果，使用宽松阈值({fallback_threshold})")
                filtered = [
                    item for item in reranked
                    if item.get("final_score", 0) >= fallback_threshold
                ]

            formatted_results = []
            for item in filtered[:n_results]:
                formatted_results.append({
                    "question": item["question"],
                    "answer": item["answer"],
                    "category": item["category"],
                    "source": item.get("source", ""),
                    "source_type": item.get("source_type", ""),
                    "attraction_name": item.get("attraction_name", ""),
                    "similarity": round(item.get("final_score", 0), 4),
                    "raw_similarity": round(item.get("vector_similarity", 0), 4),
                    "index": len(formatted_results) + 1
                })

            return {
                "success": True,
                "results": formatted_results,
                "total": len(formatted_results),
                "error": None
            }
        except Exception as e:
            print(f"[RAG] 检索失败: {e}")
            return {"success": False, "results": [], "total": 0, "error": str(e)}

    def _exact_attraction_candidates(self, query: str) -> list:
        """显式景点名兜底：向量召回不稳定时，按元数据精确取该景点资料。"""
        attraction_name = extract_attraction_name(query)
        if not attraction_name or not self.collection:
            return []

        try:
            raw = self.collection.get(
                where={"attraction_name": attraction_name},
                limit=40,
                include=["documents", "metadatas"]
            )
        except Exception as e:
            print(f"[RAG] 景点精确兜底失败: {e}")
            return []

        documents = raw.get("documents", []) or []
        metadatas = raw.get("metadatas", []) or []
        candidates = []
        for doc, metadata in zip(documents, metadatas):
            candidates.append({
                "type": metadata.get("type", ""),
                "question": metadata.get("question", ""),
                "answer": metadata.get("answer", ""),
                "category": metadata.get("category", ""),
                "attraction_name": metadata.get("attraction_name", ""),
                "source": metadata.get("source", ""),
                "source_type": metadata.get("source_type", ""),
                "source_attraction": metadata.get("source_attraction", ""),
                "vector_similarity": 0.0,
                "doc": doc
            })
        if candidates:
            print(f"[RAG] 景点精确兜底: {attraction_name} -> {len(candidates)} 条")
        return candidates

    def build_context(self, sources: list, n_results: int = 3) -> str:
        context_parts = []
        max_items = min(n_results or 3, 3)
        for i, item in enumerate(sources[:max_items], 1):
            answer = self._trim_context_text(item.get("answer", ""), 520)
            context_parts.append(
                f"【参考{i}】\n"
                f"景点：{item.get('attraction_name', '')}\n"
                f"来源：{item.get('source', '')}\n"
                f"问题：{item.get('question', '')}\n"
                f"答案：{answer}"
            )
        return "\n\n".join(context_parts)

    def _trim_context_text(self, text: str, max_len: int = 520) -> str:
        text = " ".join((text or "").split())
        if len(text) <= max_len:
            return text
        cut = text[:max_len]
        punct = max(cut.rfind("。"), cut.rfind("；"), cut.rfind("，"))
        if punct > max_len * 0.55:
            return cut[:punct + 1]
        return cut.rstrip() + "..."

    def get_context(self, query: str, n_results: int = 3) -> str:
        result = self.search(query, n_results)
        if not result["success"] or not result["results"]:
            return ""
        return self.build_context(result["results"], n_results)


_rag_service = None


def get_rag_service():
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
