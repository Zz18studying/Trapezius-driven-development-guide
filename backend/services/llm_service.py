# -*- coding: utf-8 -*-
"""
大模型调用服务
"""

import sys
import os
import json
import re
import requests

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, BACKEND_DIR)

import config


class LLMService:
    def __init__(self):
        self.url = config.OLLAMA_URL
        self.model = config.OLLAMA_MODEL
        self._check_ollama()

    def _check_ollama(self):
        try:
            response = requests.post(
                self.url,
                json={"model": self.model, "prompt": "test", "stream": False},
                timeout=5
            )
            if response.status_code == 200:
                print(f"✅ LLM服务初始化成功")
                print(f"   模型: {self.model}")
            else:
                print(f"⚠️ Ollama服务异常: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Ollama服务连接失败: {e}")

    def is_ready(self):
        try:
            response = requests.post(
                self.url,
                json={"model": self.model, "prompt": "test", "stream": False},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

    def chat(self, question: str, context: str = "", history: list = None) -> dict:
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

        prompt = self._build_prompt(messages)

        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "top_p": 0.95, "num_predict": 1024}
                },
                timeout=60
            )

            if response.status_code == 200:
                answer = response.json().get('response', '')
                answer = self._clean_answer(answer)
                return {"success": True, "answer": answer, "error": None}
            else:
                return {"success": False, "answer": "", "error": f"API错误: {response.status_code}"}
        except Exception as e:
            return {"success": False, "answer": "", "error": str(e)}

    def _build_prompt(self, messages):
        prompt_parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        prompt_parts.append("Assistant: ")
        return "\n\n".join(prompt_parts)

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