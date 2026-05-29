# -*- coding: utf-8 -*-
"""
大模型调用服务 - 使用 DeepSeek API
"""

import sys
import os
import re
from openai import OpenAI

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, BACKEND_DIR)

import config


class LLMService:
    def __init__(self):
        # 从环境变量或 config 获取 API Key
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", getattr(config, 'DEEPSEEK_API_KEY', ''))

        if not self.api_key:
            print("⚠️ 未设置 DEEPSEEK_API_KEY，LLM 服务将不可用")
            print("   请设置环境变量: set DEEPSEEK_API_KEY=你的API-Key")
            self.client = None
            return

        # 初始化 DeepSeek 客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )
        self.model = getattr(config, 'DEEPSEEK_MODEL', 'deepseek-v4-flash')
        print(f"✅ LLM服务初始化成功（DeepSeek API）")
        print(f"   模型: {self.model}")

    def is_ready(self):
        return self.client is not None

    def chat(self, question: str, context: str = "", history: list = None) -> dict:
        if not self.is_ready():
            return {"success": False, "answer": "AI服务未就绪", "error": "LLM not ready"}

        system_prompt = """你是灵山胜境景区的AI导游，名叫"小灵"。
你的职责是热情、耐心地回答游客关于灵山胜境的问题，答案要准确简洁。"""

        user_message = question
        if context:
            user_message = f"""请根据以下参考资料回答用户问题。

【参考资料】
{context}

【用户问题】
{question}

请基于参考资料给出准确、简洁的回答。"""

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history[-6:])
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024
            )
            answer = response.choices[0].message.content
            answer = self._clean_answer(answer)
            return {"success": True, "answer": answer, "error": None}
        except Exception as e:
            print(f"❌ API调用失败: {e}")
            return {"success": False, "answer": "", "error": str(e)}

    def _clean_answer(self, answer):
        answer = re.sub(r'^Assistant:\s*', '', answer)
        answer = re.sub(r'^助手：\s*', '', answer)
        return answer.strip()


_llm_service = None


def get_llm_service():
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service