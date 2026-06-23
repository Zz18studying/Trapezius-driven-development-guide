# -*- coding: utf-8 -*-
"""
大模型调用服务 - 使用 DeepSeek API + 对话记忆
"""

import os
import sys
import json
import re
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

    def get_or_create_session(self, session_id: str):
        """获取或创建会话历史"""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    def _is_social_question(self, question: str) -> bool:
        """判断是否为社交性问题（不需要知识库）"""
        social_patterns = [
            r'你好',
            r'您好',
            r'我叫',
            r'我是.*(?:游客|客人|朋友)',
            r'你叫什么',
            r'你是谁',
            r'你的名字',
            r'我叫什么',
            r'我叫什么名字',
            r'还记得我叫什么',
            r'知道我叫什么',
            r'很高兴',
            r'谢谢',
            r'感谢',
            r'再见',
            r'拜拜',
            r'请问',
            r'可以.*吗',
            r'帮我',
            r'知道',
            r'明白'
        ]
        for pattern in social_patterns:
            if re.search(pattern, question):
                return True
        return False

    def _extract_name_from_history(self, history: list) -> str:
        """从对话历史中提取用户的名字"""
        if not history:
            return None
        
        user_messages = []
        for msg in history:
            if msg.get("role") == "user":
                user_messages.append(msg.get("content", ""))
        
        for msg in reversed(user_messages[-10:]):
            match = re.search(r'我叫([\u4e00-\u9fa5]{1,4})', msg)
            if match:
                return match.group(1)
            match = re.search(r'我是([\u4e00-\u9fa5]{1,4})', msg)
            if match:
                return match.group(1)
            match = re.search(r'名字叫([\u4e00-\u9fa5]{1,4})', msg)
            if match:
                return match.group(1)
        
        return None

    def _generate_social_response(self, question: str, history: list = None) -> str:
        """生成社交回复（不依赖知识库），支持从历史中提取名字"""
        
        # 处理"我叫什么"类问题
        if re.search(r'我叫什么|我叫什么名字|还记得我叫什么|知道我叫什么', question):
            if history:
                name = self._extract_name_from_history(history)
                if name:
                    return f"你叫{name}呀！我记得呢~"
            return "我还不知道你的名字呢，可以告诉我吗？"
        
        # 处理"你是谁/你叫什么"类问题
        if re.search(r'你叫什么|你是谁|你的名字', question):
            return "我是灵山胜境景区的AI数字导游小灵，专门为游客提供景点讲解和游览建议！"
        
        # 处理"你好"类问题
        if re.search(r'你好|您好', question):
            if history:
                name = self._extract_name_from_history(history)
                if name:
                    return f"你好{name}！欢迎回来~有什么问题随时问我哦！"
            return "你好呀！我是灵山胜境景区的AI数字导游小灵，很高兴为你服务！有关于灵山胜境的问题尽管问我哦~"
        
        # 处理"我叫XXX"类问题
        if re.search(r'我叫', question):
            name_match = re.search(r'我叫([\u4e00-\u9fa5]{1,4})', question)
            if name_match:
                name = name_match.group(1)
                return f"你好{name}！我是灵山胜境景区的AI数字导游小灵，很高兴认识你！有什么关于灵山胜境的问题，随时问我哦~"
            return "你好呀！我是灵山胜境景区的AI数字导游小灵，很高兴认识你！"
        
        # 处理"谢谢/感谢"
        if re.search(r'谢谢|感谢', question):
            return "不客气！祝你游玩愉快，有任何问题随时问我~"
        
        # 处理"再见/拜拜"
        if re.search(r'再见|拜拜', question):
            return "再见！祝你旅途愉快，期待下次相遇~"
        
        # 默认回复
        return "你好！我是灵山胜境景区的AI数字导游小灵，有什么可以帮你的吗？"

    def chat(self, question: str, context: str = "", session_id: str = None, history: list = None) -> dict:
        if not self.is_ready():
            return {"success": False, "answer": "", "error": "LLM not ready"}

        # 获取会话历史
        if session_id:
            history = self.get_or_create_session(session_id)
        elif history is None:
            history = []

        # ===== 社交问题直接回复，不经过 RAG =====
        if self._is_social_question(question):
            answer = self._generate_social_response(question, history)
            if session_id:
                hist = self.get_or_create_session(session_id)
                hist.append({"role": "user", "content": question})
                hist.append({"role": "assistant", "content": answer})
            return {"success": True, "answer": answer, "error": None}

        # ===== 知识性问题：严格防幻觉 System Prompt =====
        system_prompt = """
你是灵山胜境景区AI数字导游"小灵"。

你必须严格遵守以下规则：

【事实规则】

1. 只能依据系统提供的参考资料回答问题。

2. 不允许使用你自身已有知识。

3. 不允许推测。

4. 不允许编造事实。

5. 不允许补充参考资料中不存在的信息。

【拒答规则】

如果参考资料中找不到问题答案，

必须回复：

"抱歉，目前知识库中暂无相关信息。"

不得自行猜测答案。

【回答规则】

1. 回答自然、友好。

2. 回答简洁。

3. 优先引用参考资料中的具体数据。

4. 如果涉及：

- 时间
- 年份
- 票价
- 距离
- 数量

必须严格按照参考资料回答。

不得修改数字。

5. 可以结合对话历史理解用户问题的上下文，但所有事实性信息仍必须源自参考资料。
"""

        messages = [{"role": "system", "content": system_prompt}]

        if history:
            messages.extend(history[-10:])

        user_message = question
        if context:
            user_message = f"""请根据以下参考资料回答用户问题。

【参考资料】
{context}

【用户问题】
{question}

请严格依据参考资料回答。

要求：

1. 只能使用参考资料中的内容。
2. 不允许使用外部知识。
3. 不允许猜测。
4. 若参考资料无法回答问题，回复：

抱歉，目前知识库中暂无相关信息。
"""

        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1024
            )
            answer = response.choices[0].message.content
            answer = self._clean_answer(answer)

            if session_id:
                history.append({"role": "user", "content": question})
                history.append({"role": "assistant", "content": answer})
                if len(history) > 20:
                    self.sessions[session_id] = history[-20:]

            return {"success": True, "answer": answer, "error": None}
        except Exception as e:
            print(f"❌ API调用失败: {e}")
            return {"success": False, "answer": "", "error": str(e)}

    def _clean_answer(self, answer):
        answer = re.sub(r'^Assistant:\s*', '', answer)
        answer = re.sub(r'^助手：\s*', '', answer)
        return answer.strip()

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