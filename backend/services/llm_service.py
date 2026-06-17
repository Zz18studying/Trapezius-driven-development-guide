# -*- coding: utf-8 -*-
"""
大模型调用服务 - 支持对话记忆
"""

import os
import sys
import json
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class LLMService:
    def __init__(self):
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", getattr(config, 'DEEPSEEK_API_KEY', ''))
        # 会话存储：session_id -> [{"role": "user", "content": "..."}, ...]
        self.sessions = {}

        if not self.api_key:
            print("⚠️ 未设置 DEEPSEEK_API_KEY")
            self.client = None
            return

        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )
        self.model = getattr(config, 'DEEPSEEK_MODEL', 'deepseek-v4-flash')
        print(f"✅ LLM服务初始化成功（DeepSeek API + 对话记忆）")
        print(f"   模型: {self.model}")

    def is_ready(self):
        return self.client is not None

    def get_or_create_session(self, session_id):
        """获取或创建会话历史"""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    def chat(self, question: str, context: str = "", session_id: str = None) -> dict:
        if not self.is_ready():
            return {"success": False, "answer": "", "error": "LLM not ready"}

        # 获取会话历史
        if session_id:
            history = self.get_or_create_session(session_id)
        else:
            history = []

        system_prompt = """你是灵山胜境景区的AI导游，名叫"小灵"。
你的职责是热情、耐心地回答游客关于灵山胜境的问题。
你可以参考对话历史中的上下文来回答。
如果用户没有明确说明，不要假设上下文。
不要编造答案，如果不知道就说不知道。
回答要简洁亲切，30字左右。"""

        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]

        # 添加历史对话（最多保留最近10条，避免超长）
        if history:
            messages.extend(history[-10:])

        # 如果有RAG检索结果，添加为上下文
        if context:
            messages.append({
                "role": "user",
                "content": f"【参考资料】\n{context}\n\n【用户问题】\n{question}"
            })
        else:
            messages.append({
                "role": "user",
                "content": question
            })

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=512
            )
            answer = response.choices[0].message.content

            # 存储对话历史
            if session_id:
                history.append({"role": "user", "content": question})
                history.append({"role": "assistant", "content": answer})
                # 限制历史长度，避免上下文过长
                if len(history) > 20:
                    self.sessions[session_id] = history[-20:]

            return {"success": True, "answer": answer, "error": None}
        except Exception as e:
            print(f"❌ API调用失败: {e}")
            return {"success": False, "answer": "", "error": str(e)}

    def clear_session(self, session_id: str):
        """清空会话历史"""
        if session_id in self.sessions:
            del self.sessions[session_id]


_llm_service = None

def get_llm_service():
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service