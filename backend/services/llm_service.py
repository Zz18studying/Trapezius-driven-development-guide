# -*- coding: utf-8 -*-
"""
大模型调用服务 - 精简优化版（仅负面情绪反馈 + 指代词替换修复）
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
        self.sessions = {}

        if not self.api_key:
            print("⚠️ 未设置 DEEPSEEK_API_KEY")
            self.client = None
            return

        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com",
            timeout=10.0
        )
        self.model = getattr(config, 'DEEPSEEK_MODEL', 'deepseek-v4-flash')
        print(f"✅ LLM服务初始化成功（DeepSeek API + 对话记忆 + 用户画像 + 环境感知 + 情绪感知精简版）")
        print(f"   模型: {self.model}")

    def is_ready(self):
        return self.client is not None

    def get_or_create_session(self, session_id: str) -> dict:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": [],
                "last_context": "",
                "last_question": "",
                "interests": [],
                "travel_context": {},
                "last_emotion": {"emotion": "neutral", "has_emotion": False, "intensity": 0},
                "emotion_history": []
            }
        return self.sessions[session_id]

    def _is_social_question(self, question: str) -> bool:
        social_patterns = [
            r'^你好[呀么啊嘛~!！]?$',  # 只匹配纯问候
            r'^您好[呀么啊嘛~!！]?$',
            r'^hi', r'^hello',  # 英文问候
            r'我叫[\u4e00-\u9fa5]{1,4}$',  # 自我介绍（不含问句）
            r'^我是(?:游客|客人|朋友)$',  # 纯自我介绍
            r'你叫什么名字[？?]?',  # 问机器人名字
            r'你是谁[？?]?', r'你叫什么[？?]?', r'你的名字[？?]?',
            r'还记得我叫什么[吗？]?', r'知道我叫什么[吗？]?',
            r'很高兴[认识你|见到你|服务你]',  # 纯情感表达
            r'^[谢感谢]+[你呀]?[！～]*$',  # 纯感谢
            r'^[再见拜拜]+[～！]*$',  # 纯告别
            r'^请问(你|你是)',  # 询问机器人身份
        ]
        for pattern in social_patterns:
            if re.search(pattern, question):
                return True
        return False

    def _is_route_question(self, question: str) -> bool:
        route_patterns = [
            r'怎么逛', r'怎么玩', r'路线', r'推荐.*路线', r'应该怎么走',
            r'游览顺序', r'先去哪里', r'怎么安排', r'行程', r'怎么游',
            r'逛完.*需要多久', r'路线规划', r'怎么走比较顺'
        ]
        for pattern in route_patterns:
            if re.search(pattern, question):
                return True
        return False

    def _extract_name_from_history(self, history: list) -> str:
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
        if re.search(r'我叫什么|我叫什么名字|还记得我叫什么|知道我叫什么', question):
            if history:
                name = self._extract_name_from_history(history)
                if name:
                    return f"你叫{name}呀！我记得呢~"
            return "我还不知道你的名字呢，可以告诉我吗？"
        if re.search(r'你叫什么|你是谁|你的名字', question):
            return "我是灵山胜境景区的AI数字导游小灵，专门为游客提供景点讲解和游览建议！"
        if re.search(r'你好|您好', question):
            if history:
                name = self._extract_name_from_history(history)
                if name:
                    return f"你好{name}！欢迎回来~有什么问题随时问我哦！"
            return "你好呀！我是灵山胜境景区的AI数字导游小灵，很高兴为你服务！有关于灵山胜境的问题尽管问我哦~"
        if re.search(r'我叫', question):
            name_match = re.search(r'我叫([\u4e00-\u9fa5]{1,4})', question)
            if name_match:
                name = name_match.group(1)
                return f"你好{name}！我是灵山胜境景区的AI数字导游小灵，很高兴认识你！有什么关于灵山胜境的问题，随时问我哦~"
            return "你好呀！我是灵山胜境景区的AI数字导游小灵，很高兴认识你！"
        if re.search(r'谢谢|感谢', question):
            return "不客气！祝你游玩愉快，有任何问题随时问我~"
        if re.search(r'再见|拜拜', question):
            return "再见！祝你旅途愉快，期待下次相遇~"
        return "你好！我是灵山胜境景区的AI数字导游小灵，有什么可以帮你的吗？"

    def _extract_environment_context(self, question: str) -> dict:
        env = {
            "weather": "unknown",
            "time": "unknown",
            "has_info": False
        }
        if re.search(r'下雨|雨|淋雨|雨天', question):
            env["weather"] = "rainy"
            env["has_info"] = True
        elif re.search(r'晴天|出太阳|晒|大太阳', question):
            env["weather"] = "sunny"
            env["has_info"] = True
        elif re.search(r'阴天|多云', question):
            env["weather"] = "cloudy"
            env["has_info"] = True
        if re.search(r'傍晚|夕阳|日落|黄昏', question):
            env["time"] = "evening"
            env["has_info"] = True
        elif re.search(r'上午|早上|早晨', question):
            env["time"] = "morning"
            env["has_info"] = True
        elif re.search(r'下午|午后', question):
            env["time"] = "afternoon"
            env["has_info"] = True
        elif re.search(r'晚上|夜晚', question):
            env["time"] = "night"
            env["has_info"] = True
        if env["has_info"]:
            print(f"[LLM] 检测到环境信息: 天气={env['weather']}, 时间={env['time']}")
        return env

    def _get_weather_adjustment(self, weather: str) -> str:
        adjustments = {
            "rainy": "【天气】下雨→推荐室内景点（梵宫、博览馆、五印坛城）。",
            "sunny": "【天气】晴天→早晚游室外，中午进梵宫避暑，防晒补水。",
            "cloudy": "【天气】阴天→适宜全天户外活动。"
        }
        return adjustments.get(weather, "")

    def _get_time_adjustment(self, time: str) -> str:
        adjustments = {
            "evening": "【时段】傍晚→大佛平台看日落，拍照最佳。",
            "morning": "【时段】上午→九龙灌浴10:00场，光线好游客少。",
            "afternoon": "【时段】下午→逛室内景点，14:00吉祥颂演出。",
            "night": "【时段】夜晚→拈花湾灯光秀。"
        }
        return adjustments.get(time, "")

    def _extract_travel_context_from_question(self, question: str) -> dict:
        context = {
            "with_children": False,
            "with_elderly": False,
            "time_constraint": "full_day",
            "weather": "normal",
            "energy_level": "normal",
            "has_constraint": False
        }
        if re.search(r'孩子|小孩|小朋友|宝宝|亲子|带娃', question):
            context["with_children"] = True
            context["has_constraint"] = True
        if re.search(r'老人|长辈|父母|爸妈|带父母', question):
            context["with_elderly"] = True
            context["has_constraint"] = True
        if re.search(r'半天|半日|只有.*小时', question):
            context["time_constraint"] = "half_day"
            context["has_constraint"] = True
        elif re.search(r'快速|简单逛|打个卡|2.*小时', question):
            context["time_constraint"] = "quick"
            context["has_constraint"] = True
        if re.search(r'下雨|雨|雨天', question):
            context["weather"] = "rainy"
            context["has_constraint"] = True
        elif re.search(r'晒|大太阳|暴晒', question):
            context["weather"] = "sunny"
            context["has_constraint"] = True
        if re.search(r'累了|走不动|体力|太累', question):
            context["energy_level"] = "low"
            context["has_constraint"] = True
        return context

    def _detect_emotion(self, question: str, history: list = None, emotion_history: list = None) -> dict:
        """
        精简情绪检测：只检测负面情绪（投诉/不满/疲惫）
        """
        complaint_patterns = [
            r'太差|极差|垃圾|后悔来|再也不来|劝退|浪费时间|浪费钱|坑人|被骗|太失望',
            r'投诉|差评|服务差|态度差|体验极差|强烈不满|简直无语|太过分了|真受不了',
            r'白来了|不如不来|毫无意义|后悔死了|不值票价'
        ]
        dissatisfaction_patterns = [
            r'不好玩|一般般|失望|不满意', r'不值', r'真没意思|没意思|真一般|很一般',
            r'太热|太晒|太冷|太挤|人太多|排队太久|太贵|性价比低',
            r'体验不好|有点失望|比想象差|落差大'
        ]
        fatigue_patterns = [
            r'累了?', r'太累', r'走不动', r'好累', r'疲惫', r'脚痛|腿酸|腰酸',
            r'体力不支|走不动了|歇一会|休息一下|坐一下'
        ]

        is_complaint = False
        is_fatigue = False
        is_dissatisfied = False

        for pattern in complaint_patterns:
            if re.search(pattern, question):
                is_complaint = True
                break
        for pattern in fatigue_patterns:
            if re.search(pattern, question):
                is_fatigue = True
                break
        if not is_complaint:
            for pattern in dissatisfaction_patterns:
                if re.search(pattern, question):
                    is_dissatisfied = True
                    break

        if is_complaint:
            return {
                "emotion": "complaint",
                "has_emotion": True,
                "intensity": 9,
                "weight": 2.0,
                "trigger_words": ["投诉"],
                "is_complaint": True,
                "is_fatigue": False
            }
        elif is_fatigue:
            return {
                "emotion": "fatigue",
                "has_emotion": True,
                "intensity": 7,
                "weight": 1.5,
                "trigger_words": ["累了"],
                "is_complaint": False,
                "is_fatigue": True
            }
        elif is_dissatisfied:
            return {
                "emotion": "dissatisfied",
                "has_emotion": True,
                "intensity": 5,
                "weight": 1.3,
                "trigger_words": ["不满"],
                "is_complaint": False,
                "is_fatigue": False
            }
        else:
            return {
                "emotion": "neutral",
                "has_emotion": False,
                "intensity": 0,
                "weight": 1.0,
                "trigger_words": [],
                "is_complaint": False,
                "is_fatigue": False
            }

    def _detect_interest(self, question: str, stored_interests: list = None) -> dict:
        if re.search(r'孩子|小孩|带.*孩子|带.*老人|亲子|家庭', question):
            has_switch_signal = re.search(r'也喜欢|还喜欢|其实更|更喜欢|但是.*喜欢|不过.*喜欢|更喜欢|更想', question)
            if not has_switch_signal:
                if stored_interests and len(stored_interests) > 0:
                    route_key = stored_interests[-1]
                    route = config.ROUTES.get(route_key)
                    if route:
                        return {"has_interest": True, "route_key": route_key, "route_name": route["name"], "spots": route["spots"], "description": route["description"], "highlights": route["highlights"], "matched_keywords": [route_key], "from_memory": True, "is_contextual_update": True}
        matched_interests = []
        route_key = None
        for keyword, route in config.INTEREST_TO_ROUTE.items():
            if keyword in question:
                matched_interests.append(keyword)
                if route_key is None:
                    route_key = route
        if route_key is None:
            if stored_interests and len(stored_interests) > 0:
                route_key = stored_interests[-1]
                route = config.ROUTES.get(route_key)
                if route:
                    return {"has_interest": True, "route_key": route_key, "route_name": route["name"], "spots": route["spots"], "description": route["description"], "highlights": route["highlights"], "matched_keywords": [route_key], "from_memory": True}
            return {"has_interest": False}
        route = config.ROUTES.get(route_key)
        if not route:
            return {"has_interest": False}
        return {"has_interest": True, "route_key": route_key, "route_name": route["name"], "spots": route["spots"], "description": route["description"], "highlights": route["highlights"], "matched_keywords": matched_interests, "from_memory": False}

    def _is_follow_up_question(self, question: str, last_question: str) -> bool:
        if not last_question:
            return False
        if re.search(r'^(它|这个|那个|这|那|有.*吗|什么|怎么样|如何|好玩吗|值得去吗)', question):
            return True
        attraction_names = ["灵山大佛", "九龙灌浴", "灵山梵宫", "五印坛城", "祥符禅寺", "拈花广场", "梵天花海", "香月花街", "五灯湖", "灵山大照壁", "阿育王柱", "百子戏弥勒", "曼飞龙塔", "无尽意斋"]
        has_attraction_in_current = any(name in question for name in attraction_names)
        has_attraction_in_last = any(name in last_question for name in attraction_names)
        if has_attraction_in_last and not has_attraction_in_current:
            return True
        return False

    def _get_last_attraction_from_history(self, history: list) -> str:
        """从对话历史中提取上一轮提到的景点名称（从user消息中提取）"""
        if not history:
            return None
        attraction_names = ["灵山大佛", "九龙灌浴", "灵山梵宫", "五印坛城", "祥符禅寺", 
                            "拈花广场", "梵天花海", "香月花街", "五灯湖", "灵山大照壁", 
                            "阿育王柱", "百子戏弥勒", "曼飞龙塔", "无尽意斋", "鹿鸣谷",
                            "灵山精舍", "菩提大道", "五明桥", "佛足坛", "五智门",
                            "降魔浮雕", "佛教文化博览馆"]
        for msg in reversed(history):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                for name in attraction_names:
                    if name in content:
                        return name
        return None

    # ==================== 新增：公开方法，供 API 层调用 ====================
    def resolve_pronoun(self, question: str, session_id: str) -> str:
        """将问题中的指代词（它/这个/那个等）替换为上一轮提到的景点名称"""
        if not session_id or not question:
            return question

        session_data = self.get_or_create_session(session_id)
        last_question = session_data.get("last_question", "")
        history = session_data.get("history", [])

        if not self._is_follow_up_question(question, last_question):
            return question

        if re.search(r'^(它|这个|那个|这|那)', question):
            last_attraction = None
            # 优先从 last_question 提取
            if last_question:
                attraction_names = [
                    "灵山大佛", "九龙灌浴", "灵山梵宫", "五印坛城", "祥符禅寺",
                    "拈花广场", "梵天花海", "香月花街", "五灯湖", "灵山大照壁",
                    "阿育王柱", "百子戏弥勒", "曼飞龙塔", "无尽意斋", "鹿鸣谷",
                    "灵山精舍", "菩提大道", "五明桥", "佛足坛", "五智门",
                    "降魔浮雕", "佛教文化博览馆"
                ]
                for name in attraction_names:
                    if name in last_question:
                        last_attraction = name
                        break
            if not last_attraction:
                last_attraction = self._get_last_attraction_from_history(history)

            if last_attraction:
                new_q = re.sub(r'^(它|这个|那个|这|那)', last_attraction, question)
                print(f"[LLM] 指代词替换: '{question}' → '{new_q}'")
                return new_q
        return question
    # ========================================================================

    def chat(self, question: str, context: str = "", session_id: str = None, history: list = None) -> dict:
        if not self.is_ready():
            return {"success": False, "answer": "", "error": "LLM not ready"}

        if session_id:
            session_data = self.get_or_create_session(session_id)
            history = session_data.get("history", [])
            last_context = session_data.get("last_context", "")
            last_question = session_data.get("last_question", "")
            stored_interests = session_data.get("interests", [])
            stored_travel_context = session_data.get("travel_context", {})
            emotion_history = session_data.get("emotion_history", [])
            print(f"[LLM] session: interests={stored_interests}")
        else:
            session_data = None
            history = history or []
            last_context = ""
            last_question = ""
            stored_interests = []
            stored_travel_context = {}
            emotion_history = []

        # 社交问题直接回复
        if self._is_social_question(question):
            answer = self._generate_social_response(question, history)
            if session_id and session_data:
                session_data["history"].append({"role": "user", "content": question})
                session_data["history"].append({"role": "assistant", "content": answer})
                session_data["last_question"] = question
            return {"success": True, "answer": answer, "error": None}

        # ===== 判断是否为追问，替换指代词（注意：现在 API 层已经提前处理了，这里保留作为备用） =====
        is_follow_up = self._is_follow_up_question(question, last_question)
        original_question = question
        if is_follow_up:
            if re.search(r'^(它|这个|那个|这|那)', question):
                last_attraction = None
                if last_question:
                    attraction_names = ["灵山大佛", "九龙灌浴", "灵山梵宫", "五印坛城", "祥符禅寺", 
                                        "拈花广场", "梵天花海", "香月花街", "五灯湖", "灵山大照壁", 
                                        "阿育王柱", "百子戏弥勒", "曼飞龙塔", "无尽意斋", "鹿鸣谷",
                                        "灵山精舍", "菩提大道", "五明桥", "佛足坛", "五智门",
                                        "降魔浮雕", "佛教文化博览馆"]
                    for name in attraction_names:
                        if name in last_question:
                            last_attraction = name
                            break
                if not last_attraction:
                    last_attraction = self._get_last_attraction_from_history(history)
                if last_attraction:
                    question = re.sub(r'^(它|这个|那个|这|那)', last_attraction, question)
                    print(f"[LLM] 指代词替换: '{original_question}' → '{question}'")
            
            if not context and last_context:
                print(f"[LLM] 检测到追问，复用上一轮 context")
                if ("特色" in question or "看点" in question or "亮点" in question) and "特色" not in last_context:
                    print(f"[LLM] 追问主题变化，强制重新检索")
                    context = ""
                else:
                    context = last_context

        # 复用context（非追问场景）
        if not context and last_context:
            context = last_context

        # ===== 精简情绪检测（仅检测负面） =====
        emotion_info = self._detect_emotion(question, history, emotion_history)
        if emotion_info.get("has_emotion"):
            print(f"[LLM] 情绪: {emotion_info['emotion']} (权重: {emotion_info['weight']}×)")
            if session_data:
                session_data["last_emotion"] = emotion_info
                emotion_history.append({
                    "emotion": emotion_info["emotion"],
                    "intensity": emotion_info["intensity"],
                    "weight": emotion_info["weight"],
                    "is_complaint": emotion_info.get("is_complaint", False)
                })
                if len(emotion_history) > 5:
                    emotion_history = emotion_history[-5:]
                session_data["emotion_history"] = emotion_history

        # 检测兴趣
        is_route_question = self._is_route_question(question)
        interest_info = self._detect_interest(question, stored_interests)
        print(f"[LLM] 兴趣: {interest_info.get('route_key') if interest_info.get('has_interest') else '无'}")

        # 提取旅游上下文
        travel_context = self._extract_travel_context_from_question(question)

        # 保存兴趣
        if interest_info.get("has_interest") and not interest_info.get("from_memory"):
            new_interest = interest_info["route_key"]
            if new_interest not in stored_interests:
                stored_interests.append(new_interest)
                if session_data:
                    session_data["interests"] = stored_interests

        # 保存旅游上下文
        if travel_context.get("has_constraint"):
            merged_travel_context = stored_travel_context.copy()
            if travel_context.get("with_children"):
                merged_travel_context["with_children"] = True
            if travel_context.get("with_elderly"):
                merged_travel_context["with_elderly"] = True
            if travel_context.get("time_constraint") in ["half_day", "quick"]:
                merged_travel_context["time_constraint"] = travel_context["time_constraint"]
            if session_data:
                session_data["travel_context"] = merged_travel_context

        final_travel_context = stored_travel_context.copy()
        if travel_context.get("has_constraint"):
            if travel_context.get("with_children"):
                final_travel_context["with_children"] = True
            if travel_context.get("with_elderly"):
                final_travel_context["with_elderly"] = True
            if travel_context.get("time_constraint") in ["half_day", "quick"]:
                final_travel_context["time_constraint"] = travel_context["time_constraint"]

        if context and session_data:
            session_data["last_context"] = context
        if session_data:
            session_data["last_question"] = original_question

        # ===== 精简版 System Prompt =====
        system_prompt = """
你是灵山AI导游"小灵"，依据【参考资料】回答问题。

【规则】
1. 只用参考资料数据，不编造、不推测。
2. 涉及高度/价格/时间必须引用具体数值。
3. 问"好玩吗"→先引用事实，再建议。
4. 用户问路线时才提供详细路线。
5. 不用**、*、#。句号结尾。段落空行。
6. 答案必须完整，不能以"建议到"、"例如"等词结尾而不给出具体内容。
7. 避免重复内容，同一段信息只说一次。
8. 组织答案结构清晰，逻辑连贯，不要机械拼接。
"""

        # ===== 仅负面情绪指令 =====
        if emotion_info.get("has_emotion"):
            emotion = emotion_info["emotion"]
            if emotion == "complaint":
                system_prompt += """
【情绪】用户投诉。→ 先道歉，询问原因，提供替代方案，表达解决诚意。
"""
            elif emotion == "fatigue":
                system_prompt += """
【情绪】用户疲惫。→ 关心状态；推荐休息点（灵山精舍、菩提大道、鹿鸣谷、梵宫内休息区）；主动询问是否调整路线。
"""
            elif emotion == "dissatisfied":
                system_prompt += """
【情绪】用户不满。→ 共情回应，主动调整推荐方向。
"""

        # ===== 精简用户画像 =====
        user_profile_parts = []
        if interest_info.get("has_interest"):
            route_name = interest_info["route_name"]
            spots = " → ".join(interest_info["spots"])
            highlights = interest_info["highlights"]
            keywords = "、".join(interest_info.get("matched_keywords", [interest_info["route_key"]]))

            if is_route_question:
                user_profile_parts.append(f"【路线】用户对「{keywords}」感兴趣。推荐「{route_name}」：{spots}。亮点：{highlights}。给停留时间和总时长。")
            else:
                user_profile_parts.append(f"【偏好】用户喜欢「{keywords}」。回答末尾简短提一句：需要「{route_name}」具体路线可以问我。")

        if final_travel_context.get("with_children"):
            user_profile_parts.append("【同行】带孩子，选互动性强的景点。")
        if final_travel_context.get("with_elderly"):
            user_profile_parts.append("【同行】有老人，选平缓易行的景点。")
        if final_travel_context.get("time_constraint") == "half_day":
            user_profile_parts.append("【时间】半天，控制在3-4个景点。")
        elif final_travel_context.get("time_constraint") == "quick":
            user_profile_parts.append("【时间】紧张，控制在2-3个景点。")
        if final_travel_context.get("weather") == "rainy":
            user_profile_parts.append("【天气】下雨，优先室内景点。")
        if final_travel_context.get("energy_level") == "low":
            user_profile_parts.append("【体力】一般，建议全程观光车。")

        if user_profile_parts:
            system_prompt += "\n\n" + "\n".join(user_profile_parts)

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history[-5:])

        user_message = question
        if context:
            user_message = f"【参考资料】\n{context}\n\n【问题】\n{question}"

        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=768
            )
            answer = response.choices[0].message.content
            answer = self._clean_answer(answer)

            if session_data:
                session_data["history"].append({"role": "user", "content": original_question})
                session_data["history"].append({"role": "assistant", "content": answer})
                if len(session_data["history"]) > 20:
                    session_data["history"] = session_data["history"][-20:]

            return {"success": True, "answer": answer, "error": None}
        except Exception as e:
            print(f"❌ API调用失败: {e}")
            return {"success": False, "answer": "", "error": str(e)}

    def _clean_answer(self, answer):
        answer = re.sub(r'\*\*([^*]+)\*\*', r'\1', answer)
        answer = re.sub(r'(^|\s)\*\s+', r'\1· ', answer, flags=re.MULTILINE)
        answer = re.sub(r'#', '', answer)
        answer = re.sub(r'\n{3,}', '\n', answer)
        answer = re.sub(r'([。！？])(?!\n)', r'\1\n', answer)
        answer = re.sub(r'\n{2,}', '\n\n', answer)
        
        sentences = answer.split('\n')
        seen = set()
        deduped = []
        for s in sentences:
            s_clean = s.strip()
            if s_clean and s_clean not in seen:
                seen.add(s_clean)
                deduped.append(s_clean)
        answer = '\n\n'.join(deduped)
        
        return answer.strip()

    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]


_llm_service = None

def get_llm_service():
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service