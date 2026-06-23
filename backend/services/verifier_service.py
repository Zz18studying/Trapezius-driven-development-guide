# -*- coding: utf-8 -*-
"""
验证服务：支持 Ollama 本地验证 或 DeepSeek API 云端验证
"""

import sys
import os
import json
import re
from typing import Dict, Any
from openai import OpenAI

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, BACKEND_DIR)

import config


class VerifierService:
    def __init__(self):
        self.provider = config.VERIFIER_PROVIDER
        self.min_consistency_score = config.MIN_CONSISTENCY_SCORE
        self.client = None
        self.model = None

        try:
            if self.provider == "ollama":
                self.client = OpenAI(
                    base_url=config.OLLAMA_BASE_URL,
                    api_key="ollama"
                )
                self.model = config.OLLAMA_VERIFIER_MODEL
                print(f"✅ 验证服务初始化成功 (提供商: Ollama, 模型: {self.model})")
                
            elif self.provider == "deepseek":
                api_key = os.environ.get("DEEPSEEK_API_KEY", config.DEEPSEEK_API_KEY)
                if not api_key:
                    raise ValueError("DeepSeek API Key 未设置，请设置 DEEPSEEK_API_KEY 环境变量")
                self.client = OpenAI(
                    base_url="https://api.deepseek.com",
                    api_key=api_key
                )
                self.model = config.DEEPSEEK_VERIFIER_MODEL
                print(f"✅ 验证服务初始化成功 (提供商: DeepSeek API, 模型: {self.model})")
            else:
                raise ValueError(f"未知的验证提供商: {self.provider}")

        except Exception as e:
            print(f"❌ 验证服务初始化失败: {e}")
            self.client = None

    def is_ready(self):
        return self.client is not None

    def _is_social_sentence(self, sentence: str) -> bool:
        """
        判断是否为社交性句子（问候、自我介绍、礼貌用语等）
        这类句子不涉及事实性知识，直接放行
        """
        # 先转为小写，增强鲁棒性（但中文通常不区分大小写，保留原样也可）
        social_patterns = [
            r'你好',
            r'您好',
            r'我叫',
            r'我是.*(?:游客|客人|朋友|导游|小灵|数字人|AI)',
            r'欢迎',
            r'很高兴',
            r'谢谢',
            r'感谢',
            r'再见',
            r'拜拜',
            r'请问',
            r'可以.*吗',
            r'帮我',
            r'请',
            r'嗯',
            r'哦',
            r'好的',
            r'知道',
            r'明白'
        ]
        for pattern in social_patterns:
            if re.search(pattern, sentence):
                print(f"[DEBUG] 匹配到社交关键词: {pattern}")
                return True
        return False

    async def verify(self, question: str, context: str, sentence: str) -> Dict[str, Any]:
        if not self.is_ready():
            return {"verified": False, "confidence": 0.0, "reason": "Verifier service not ready"}

        # 调试输出
        print(f"[DEBUG] 验证句子: '{sentence}'")
        print(f"[DEBUG] 句子长度: {len(sentence)} 字符")

        # ===== 社交性句子直接放行 =====
        if self._is_social_sentence(sentence):
            print("[DEBUG] ✅ 判定为社交句子，放行")
            return {
                "verified": True,
                "confidence": 1.0,
                "reason": "社交性句子，跳过验证"
            }

        print("[DEBUG] ❌ 未匹配社交关键词，进入正常验证流程")

        # ===== 无上下文或上下文过短时直接放行 =====
        if not context or len(context.strip()) < 10:
            print("[DEBUG] 无足够上下文，放行")
            return {
                "verified": True,
                "confidence": 0.5,
                "reason": "无足够参考上下文，跳过验证"
            }

        # 构建严格的验证 Prompt（与之前一致）
        system_prompt = """
你是一个严格的事实核查员。你的任务是判断【待验证句子】中的信息是否完全包含在【参考上下文】中，且没有矛盾。

规则：
1. 如果【待验证句子】中的所有事实都能在【参考上下文】中找到依据，且无冲突，则判定为"一致"。
2. 如果【待验证句子】包含了【参考上下文】中不存在的信息、推测或矛盾信息，则判定为"不一致"。
3. 忽略礼貌用语、连接词等无关内容，只关注事实性信息。
4. 输出必须是一个合法的 JSON 对象，格式如下：
   {
     "consistent": true/false,
     "confidence": 0.0-1.0之间的浮点数,
     "reason": "简短说明理由"
   }
"""

        user_prompt = f"""
【参考上下文】：
{context}

【待验证句子】：
{sentence}

请输出 JSON 结果：
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            
            try:
                result_json = json.loads(content)
                is_consistent = result_json.get("consistent", False)
                confidence = float(result_json.get("confidence", 0.0))
                reason = result_json.get("reason", "")
                
                passed = is_consistent and confidence >= self.min_consistency_score
                
                print(f"[DEBUG] 验证结果: {'通过' if passed else '未通过'}")
                return {
                    "verified": passed,
                    "confidence": confidence,
                    "reason": reason
                }
            except json.JSONDecodeError:
                match = re.search(r'"consistent"\s*:\s*(true|false)', content, re.IGNORECASE)
                if match:
                    is_consistent = match.group(1).lower() == 'true'
                    return {
                        "verified": is_consistent,
                        "confidence": 0.5 if is_consistent else 0.0,
                        "reason": "Parsed from non-standard JSON"
                    }
                return {"verified": False, "confidence": 0.0, "reason": "Invalid JSON response"}

        except Exception as e:
            print(f"⚠️ 验证调用异常 (提供商: {self.provider}): {e}")
            return {"verified": False, "confidence": 0.0, "reason": str(e)}


_verifier_service = None

def get_verifier_service():
    global _verifier_service
    if _verifier_service is None:
        _verifier_service = VerifierService()
    return _verifier_service