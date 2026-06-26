# -*- coding: utf-8 -*-
"""
RAG检索服务 - 带模型预热 + 宽松重试 + 问题扩展 + 最佳匹配重排序
"""

import os
import sys
import time
import re
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
        self._warmup()

    def _init_chroma(self):
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
        print("🔥 预热模型中...")
        try:
            self.collection.query(query_texts=["测试"], n_results=1)
            print("✅ 模型预热完成")
        except Exception as e:
            print(f"⚠️ 模型预热失败: {e}")

    def is_ready(self):
        return self.collection is not None

    def _expand_question(self, query: str) -> list:
        """扩展问题为多个变体"""
        queries = [query]
        name_match = re.search(r'([\u4e00-\u9fa5]{2,6})(.*)', query)
        name = name_match.group(1) if name_match else None
        
        if name:
            if '有什么特色' in query or '有什么看点' in query:
                queries.append(f"{name}有什么主要特色")
                queries.append(f"{name}值得看吗")
                queries.append(f"{name}的亮点")
            if '好玩吗' in query or '值得去吗' in query:
                queries.append(f"{name}有什么特色")
                queries.append(f"{name}值得去吗")
            if '多高' in query:
                queries.append(f"{name}高度")
            if '多大' in query:
                queries.append(f"{name}尺寸")
            if '怎么去' in query:
                queries.append(query.replace('怎么去', '怎么走'))
            if '几点' in query or '开放时间' in query:
                queries.append(f"{name}开放时间")
            if '门票' in query or '价格' in query:
                queries.append('门票价格')
        if '吗' in query:
            queries.append(query.replace('吗', ''))
        
        seen = set()
        result = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                result.append(q)
        return result

    def _reorder_by_relevance(self, results: list, query: str) -> list:
        """
        对检索结果进行重排序，优先选择最匹配的条目
        """
        if not results:
            return results
        
        # 提取查询中的景点名称
        query_name_match = re.search(r'([\u4e00-\u9fa5]{2,6})', query)
        query_name = query_name_match.group(1) if query_name_match else ""
        
        for r in results:
            base_score = r['similarity']
            boost = 0.0
            
            # 1. 精确景点名称匹配加分（+0.15）
            if query_name and query_name in r['question']:
                boost += 0.15
            
            # 2. 答案包含具体数字加分（+0.10）
            if re.search(r'\d+[\.\d]*\s*(米|元|年|吨|天|小时)', r['answer']):
                boost += 0.10
            
            # 3. 答案包含核心体验词加分（+0.05）
            if any(kw in r['answer'] for kw in ['抱佛脚', '祈福', '俯瞰', '全景', '壮观', '震撼']):
                boost += 0.05
            
            # 4. 问题完全匹配加分（+0.08）
            if r['question'] == query or r['question'] == query + '？':
                boost += 0.08
            
            # 5. 答案长度加分（长度>100字符 +0.03）
            if len(r['answer']) > 100:
                boost += 0.03
            
            r['final_score'] = base_score + boost
            r['boost'] = boost
        
        # 按最终得分降序排列
        sorted_results = sorted(results, key=lambda x: x['final_score'], reverse=True)
        
        # 打印重排序日志
        if len(sorted_results) > 0:
            top = sorted_results[0]
            print(f"[RAG] 重排序后top1: {top['question']}")
            print(f"[RAG]   相似度: {top['similarity']:.4f}, 加分: {top.get('boost', 0):.2f}, 总分: {top.get('final_score', 0):.4f}")
        
        return sorted_results

    def search(self, query: str, n_results: int = None):
        if not self.is_ready():
            return {"success": False, "results": [], "error": "向量数据库未就绪"}

        if n_results is None:
            n_results = config.DEFAULT_N_RESULTS
        n_results = min(n_results, config.MAX_N_RESULTS)

        try:
            start = time.time()
            
            expanded_queries = self._expand_question(query)
            if len(expanded_queries) > 1:
                print(f"[RAG] 扩展检索 ({len(expanded_queries)}个变体): {expanded_queries}")
            
            all_candidates = []
            for q in expanded_queries:
                results = self.collection.query(
                    query_texts=[q],
                    n_results=n_results * 2
                )
                if results['documents'] and results['documents'][0]:
                    for doc, metadata, distance in zip(
                        results['documents'][0],
                        results['metadatas'][0],
                        results['distances'][0]
                    ):
                        similarity = 1 - distance
                        all_candidates.append({
                            "question": metadata.get('question', ''),
                            "answer": metadata.get('answer', ''),
                            "category": metadata.get('category', ''),
                            "similarity": similarity,
                            "doc": doc
                        })
            
            elapsed = time.time() - start
            print(f"[RAG] 检索耗时: {elapsed:.2f}秒, 候选数: {len(all_candidates)}")
            
            # 去重
            seen = {}
            for r in all_candidates:
                q = r['question']
                if q not in seen or r['similarity'] > seen[q]['similarity']:
                    seen[q] = r
            sorted_results = sorted(seen.values(), key=lambda x: x['similarity'], reverse=True)
            
            # ===== 最佳匹配重排序 =====
            sorted_results = self._reorder_by_relevance(sorted_results, query)
            
            # ===== 阈值过滤 =====
            formatted_results = []
            for r in sorted_results[:n_results * 2]:
                if r.get('final_score', r['similarity']) >= config.MIN_SIMILARITY:
                    formatted_results.append({
                        "question": r['question'],
                        "answer": r['answer'],
                        "category": r['category'],
                        "similarity": round(r.get('final_score', r['similarity']), 4),
                        "index": len(formatted_results) + 1
                    })

            # 宽松重试
            if len(formatted_results) == 0:
                fallback_threshold = getattr(config, 'FALLBACK_SIMILARITY', 0.3)
                print(f"[RAG] 标准阈值无结果，使用宽松阈值 ({fallback_threshold}) 重试...")
                for r in sorted_results[:n_results * 3]:
                    if r.get('final_score', r['similarity']) >= fallback_threshold:
                        formatted_results.append({
                            "question": r['question'],
                            "answer": r['answer'],
                            "category": r['category'],
                            "similarity": round(r.get('final_score', r['similarity']), 4),
                            "index": len(formatted_results) + 1
                        })
                print(f"[RAG] 宽松重试找到 {len(formatted_results)} 条")

            formatted_results = formatted_results[:n_results]

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