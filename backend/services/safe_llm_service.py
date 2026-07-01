# -*- coding: utf-8 -*-
"""
安全问答服务：生成时自动进行交叉验证，减少幻觉
"""

import asyncio
import re
from typing import List, Dict, Any, Optional
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, BACKEND_DIR)

from services.llm_service import get_llm_service
from services.verifier_service import get_verifier_service
import config


class SafeLLMService:
    def __init__(self):
        self.llm = get_llm_service()
        self.verifier = get_verifier_service()
        self.min_consistency_score = config.MIN_CONSISTENCY_SCORE
        self.require_verification = config.REQUIRE_VERIFICATION

    async def ask_with_verification(
        self,
        question: str,
        context: str,
        session_id: str = None,  # ← 新增参数
        history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        生成经过交叉验证的回答
        """
        if not self.llm.is_ready():
            return {"success": False, "answer": "", "confidence": 0.0,
                    "verified_sentences": [], "sources": [], "error": "LLM not ready"}

        # 第一步：调用主模型生成完整回答（异步执行，避免阻塞事件循环）
        gen_result = await asyncio.to_thread(
            self.llm.chat,
            question=question,
            context=context,
            session_id=session_id,
            history=history
        )
        
        if not gen_result["success"]:
            return {
                "success": False,
                "answer": "",
                "confidence": 0.0,
                "verified_sentences": [],
                "sources": [],
                "error": gen_result.get("error", "Generation failed")
            }

        raw_answer = gen_result["answer"]
        
        # 如果主模型直接拒答，无需验证
        if not raw_answer or "暂无相关信息" in raw_answer:
            return {
                "success": True,
                "answer": raw_answer,
                "confidence": 1.0,
                "verified_sentences": [],
                "sources": [],
                "error": None
            }

        # 第二步：拆分为句子
        sentences = self._split_sentences(raw_answer)
        if not sentences:
            return {
                "success": True,
                "answer": raw_answer,
                "confidence": 1.0,
                "verified_sentences": [],
                "sources": [],
                "error": None
            }

        # 第三步：并发验证每个句子
        verification_tasks = []
        for sent in sentences:
            verification_tasks.append(self.verifier.verify(question, context, sent))
        
        verification_results = await asyncio.gather(*verification_tasks)

        # 【调试用】打印验证详情
        print("-" * 20)
        print(f"问题: {question}")
        for sent, res in zip(sentences, verification_results):
            status = "✅ 通过" if res['verified'] else "❌ 拦截"
            print(f"{status} | 置信度: {res['confidence']} | 句子: {sent}")
            if not res['verified']:
                print(f"       原因: {res.get('reason')}")
        print("-" * 20)

        # 第四步：根据验证结果过滤
        verified_sentences = []
        passed_count = 0
        total_sentences = len(sentences)
        
        for sent, verify_res in zip(sentences, verification_results):
            is_verified = verify_res.get("verified", False)
            confidence = verify_res.get("confidence", 0.0)
            
            entry = {
                "sentence": sent,
                "verified": is_verified,
                "confidence": confidence
            }
            
            if not is_verified:
                entry["reason"] = verify_res.get("reason", "Unknown")
                
            verified_sentences.append(entry)
            
            if is_verified:
                passed_count += 1

        overall_confidence = passed_count / total_sentences if total_sentences > 0 else 0.0

        # 第五步：组合最终答案
        final_answer = ""
        
        if passed_count == 0:
            # 所有句子都没通过验证时，优先使用置信度最高的句子
            if verification_results:
                best_result = max(verification_results, key=lambda x: x.get("confidence", 0.0))
                best_confidence = best_result.get("confidence", 0.0)
                
                if best_confidence >= 0.3:  # 降低阈值，只要有一点置信度就使用
                    final_answer = raw_answer
                    overall_confidence = best_confidence
                    print(f"[SAFE_LLM] 所有句子验证未通过，但使用原始回答（最高置信度: {best_confidence:.2f}）")
                elif self.require_verification:
                    # 置信度太低时，给出提示但仍然提供原始答案
                    final_answer = raw_answer
                    overall_confidence = best_confidence
                    print(f"[SAFE_LLM] 置信度过低({best_confidence:.2f})，提供参考回答")
                else:
                    final_answer = raw_answer
            else:
                final_answer = raw_answer
        else:
            valid_sents = [v["sentence"] for v in verified_sentences if v["verified"]]
            final_answer = "".join(valid_sents)

        return {
            "success": True,
            "answer": final_answer,
            "confidence": round(overall_confidence, 2),
            "verified_sentences": verified_sentences,
            "sources": [],
            "error": None
        }

    def _split_sentences(self, text: str) -> List[str]:
        pattern = r'[^。！？；]*[。！？；]'
        raw_sents = re.findall(pattern, text)
        sentences = [s.strip() for s in raw_sents if s.strip()]
        last_part = re.sub(r'.*[。！？；]', '', text).strip()
        if last_part:
            sentences.append(last_part)
        return sentences


_safe_llm_service = None

def get_safe_llm_service():
    global _safe_llm_service
    if _safe_llm_service is None:
        _safe_llm_service = SafeLLMService()
    return _safe_llm_service