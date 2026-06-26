# -*- coding: utf-8 -*-
"""
大模型调用服务 - 使用 DeepSeek API + 对话记忆 + 用户画像 + 环境感知 + 情绪感知（精简版）+ 路线规划
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
            base_url="https://api.deepseek.com"
        )
        self.model = getattr(config, 'DEEPSEEK_MODEL', 'deepseek-v4-flash')
        print(f"✅ LLM服务初始化成功（DeepSeek API + 对话记忆 + 用户画像 + 环境感知 + 情绪感知 + 路线规划）")
        print(f"   模型: {self.model}")

    def is_ready(self):
        return self.client is not None

    def get_or_create_session(self, session_id: str) -> dict:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": [],
                "last_context": "",
                "last_question": "",  # 新增：记录上一轮问题
                "interests": [],
                "travel_context": {},
                "last_emotion": {"emotion": "neutral", "has_emotion": False, "intensity": 0},
                "emotion_history": []
            }
        return self.sessions[session_id]

    def _is_social_question(self, question: str) -> bool:
        social_patterns = [
            r'你好', r'您好', r'我叫', r'我是.*(?:游客|客人|朋友)',
            r'你叫什么', r'你是谁', r'你的名字', r'我叫什么', r'我叫什么名字',
            r'还记得我叫什么', r'知道我叫什么', r'很高兴', r'谢谢', r'感谢',
            r'再见', r'拜拜', r'请问', r'可以.*吗', r'帮我', r'知道', r'明白'
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
            "rainy": """
【天气提醒】当前下雨，建议：
优先推荐室内景点：灵山梵宫、佛教文化博览馆、五印坛城、无尽意斋。
避雨路线：灵山梵宫 → 佛教文化博览馆 → 五印坛城（全部室内）。
提醒游客携带雨具，注意防滑。""",
            "sunny": """
【天气提醒】晴天，建议：
上午9点前或下午4点后游览室外景点（九龙灌浴、灵山大佛平台）。
中午时段推荐室内景点（灵山梵宫）避暑。
提醒游客做好防晒、多喝水。""",
            "cloudy": """
【天气提醒】阴天，适宜户外活动：
所有景点正常开放。
体感舒适，适合全天游览。"""
        }
        return adjustments.get(weather, "")

    def _get_time_adjustment(self, time: str) -> str:
        adjustments = {
            "evening": """
【时间提醒】傍晚时分：
推荐前往灵山大佛平台观赏日落，俯瞰太湖金色波光。
夕阳西下时佛光普照，是拍照最佳时机。
灵山梵宫夜间有灯光，夜景同样值得一看。""",
            "morning": """
【时间提醒】上午：
建议先前往九龙灌浴观看10:00场表演。
上午光线柔和，适合拍摄大佛全景。
游客较少，游览体验更佳。""",
            "afternoon": """
【时间提醒】下午：
建议安排室内景点（灵山梵宫、五印坛城）。
下午14:00可观看梵宫《吉祥颂》演出。
如时间充裕，下午16:00前可登顶大佛平台。""",
            "night": """
【时间提醒】夜晚：
拈花湾禅意小镇夜间灯光秀是亮点。
灵山胜境主要景点已关闭，建议安排夜间休闲活动。"""
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

    def _analyze_emotion_trend(self, emotion_history: list) -> dict:
        if not emotion_history or len(emotion_history) < 2:
            return {"trend": "stable", "last_emotions": [e.get("emotion", "neutral") for e in emotion_history[-3:]], "alert": False, "message": "情绪状态稳定"}
        emotion_weights = {"severe_negative": 10, "moderate_negative": 7, "fatigue": 6, "confusion": 5, "mild_negative": 4, "mild_positive": 3, "neutral": 0, "positive": -7, "strong_positive": -10}
        recent = emotion_history[-5:]
        recent_emotions = [e.get("emotion", "neutral") for e in recent]
        recent_scores = [emotion_weights.get(e, 0) for e in recent_emotions]
        if len(recent_scores) >= 3:
            if recent_scores[-1] > recent_scores[-2] and recent_scores[-2] > recent_scores[-3]:
                return {"trend": "deteriorating", "last_emotions": recent_emotions[-3:], "alert": True, "message": "情绪持续恶化，需要重点关注"}
            elif recent_scores[-1] < recent_scores[-2] and recent_scores[-2] < recent_scores[-3]:
                return {"trend": "improving", "last_emotions": recent_emotions[-3:], "alert": False, "message": "情绪正在好转"}
            else:
                if recent_scores[-1] > recent_scores[-2] and recent_scores[-2] > 3:
                    return {"trend": "deteriorating", "last_emotions": recent_emotions[-3:], "alert": True, "message": "情绪有恶化趋势"}
                elif recent_scores[-1] < recent_scores[-2] and recent_scores[-2] < -3:
                    return {"trend": "improving", "last_emotions": recent_emotions[-3:], "alert": False, "message": "情绪在好转"}
                else:
                    return {"trend": "fluctuating", "last_emotions": recent_emotions[-3:], "alert": False, "message": "情绪有波动"}
        else:
            if recent_scores[-1] > recent_scores[-2] and recent_scores[-1] > 3:
                return {"trend": "deteriorating", "last_emotions": recent_emotions[-3:], "alert": True, "message": "情绪出现恶化"}
            elif recent_scores[-1] < recent_scores[-2] and recent_scores[-1] < -3:
                return {"trend": "improving", "last_emotions": recent_emotions[-3:], "alert": False, "message": "情绪明显好转"}
            else:
                return {"trend": "stable", "last_emotions": recent_emotions[-3:], "alert": False, "message": "情绪稳定"}

    def _detect_emotion(self, question: str, history: list = None, emotion_history: list = None) -> dict:
        severe_negative_patterns = [r'太差|极差|垃圾|后悔来|再也不来|劝退|浪费时间|浪费钱|坑人|被骗|太失望', r'投诉|差评|服务差|态度差|体验极差|强烈不满|简直无语|太过分了|真受不了', r'白来了|不如不来|毫无意义|后悔死了|不值票价']
        moderate_negative_patterns = [r'不好玩|一般般|失望|不满意', r'不值', r'真没意思|没意思|真一般|很一般', r'太热|太晒|太冷|太挤|人太多|排队太久|太贵|性价比低', r'体验不好|有点失望|比想象差|落差大']
        mild_negative_patterns = [r'还行吧|也还好|不算太差|马马虎虎|将就|凑合', r'有点累|一般般吧|还可以吧|中等|差强人意']
        fatigue_patterns = [r'累了?', r'太累', r'走不动', r'好累', r'疲惫', r'脚痛|腿酸|腰酸', r'体力不支|走不动了|歇一会|休息一下|坐一下']
        confusion_patterns = [r'不清楚|不知道|怎么走|迷路了|找不到|在哪|这里在哪', r'我该去哪|怎么去|怎么走|困惑|不明白|什么意思']
        mild_positive_patterns = [r'还可以|还行|不错|还可以吧|挺好的|蛮好|还行吧', r'值得|还好|没那么差|算可以|过得去']
        positive_patterns = [r'好玩', r'开心', r'满意', r'很棒', r'不错', r'值得', r'喜欢', r'推荐', r'美丽', r'好看']
        strong_positive_patterns = [r'太震撼|震撼到了|太美|太漂亮|绝了|无敌|完美', r'特别值得|太棒了|真绝|非常满意|超级好']

        triggered_severe_negative = []
        triggered_moderate_negative = []
        triggered_mild_negative = []
        triggered_fatigue = []
        triggered_confusion = []
        triggered_mild_positive = []
        triggered_positive = []
        triggered_strong_positive = []
        is_complaint = False

        for pattern in severe_negative_patterns:
            if re.search(pattern, question):
                triggered_severe_negative.append(pattern)
                is_complaint = True
        for pattern in moderate_negative_patterns:
            if re.search(pattern, question):
                triggered_moderate_negative.append(pattern)
        for pattern in mild_negative_patterns:
            if re.search(pattern, question):
                triggered_mild_negative.append(pattern)
        for pattern in fatigue_patterns:
            if re.search(pattern, question):
                triggered_fatigue.append(pattern)
        for pattern in confusion_patterns:
            if re.search(pattern, question):
                triggered_confusion.append(pattern)
        for pattern in mild_positive_patterns:
            if re.search(pattern, question):
                triggered_mild_positive.append(pattern)
        for pattern in positive_patterns:
            if re.search(pattern, question):
                triggered_positive.append(pattern)
        for pattern in strong_positive_patterns:
            if re.search(pattern, question):
                triggered_strong_positive.append(pattern)

        if is_complaint or triggered_severe_negative:
            emotion = "severe_negative"
            intensity = 10
            weight = 2.0
            trigger_words = triggered_severe_negative
        elif triggered_moderate_negative:
            emotion = "moderate_negative"
            intensity = 7
            weight = 1.8
            trigger_words = triggered_moderate_negative
        elif triggered_fatigue:
            emotion = "fatigue"
            intensity = 6
            weight = 1.5
            trigger_words = triggered_fatigue
        elif triggered_confusion:
            emotion = "confusion"
            intensity = 5
            weight = 1.3
            trigger_words = triggered_confusion
        elif triggered_mild_negative:
            emotion = "mild_negative"
            intensity = 4
            weight = 1.3
            trigger_words = triggered_mild_negative
        elif triggered_strong_positive:
            emotion = "strong_positive"
            intensity = 9
            weight = 1.0
            trigger_words = triggered_strong_positive
        elif triggered_positive:
            emotion = "positive"
            intensity = 7
            weight = 1.0
            trigger_words = triggered_positive
        elif triggered_mild_positive:
            emotion = "mild_positive"
            intensity = 5
            weight = 1.0
            trigger_words = triggered_mild_positive
        else:
            if emotion_history and len(emotion_history) > 0:
                recent_negatives = [e for e in emotion_history[-3:] if e.get("emotion") in ["severe_negative", "moderate_negative", "mild_negative", "fatigue", "confusion"]]
                if recent_negatives:
                    return {"emotion": "neutral", "has_emotion": False, "intensity": 1, "weight": 0.8, "trigger_words": [], "is_complaint": False, "trend": "recovering", "residual": True}
            return {"emotion": "neutral", "has_emotion": False, "intensity": 0, "weight": 1.0, "trigger_words": [], "is_complaint": False, "trend": "stable"}

        trend_info = self._analyze_emotion_trend(emotion_history)
        adjusted_weight = weight
        if trend_info.get("trend") == "deteriorating" and emotion in ["severe_negative", "moderate_negative", "mild_negative", "fatigue", "confusion"]:
            adjusted_weight = weight * 1.2
            print(f"[LLM] 情绪累积：检测到恶化趋势，权重从 {weight} 提升至 {adjusted_weight}")
        if trend_info.get("alert") and emotion in ["severe_negative", "moderate_negative", "mild_negative", "fatigue", "confusion"]:
            adjusted_weight = adjusted_weight * 1.15
            print(f"[LLM] 情绪累积：连续负面情绪，触发预警，权重提升至 {adjusted_weight}")

        return {
            "emotion": emotion,
            "has_emotion": True,
            "intensity": intensity,
            "weight": min(adjusted_weight, 3.0),
            "trigger_words": trigger_words,
            "is_complaint": is_complaint,
            "trend": trend_info.get("trend", "new"),
            "trend_message": trend_info.get("message", ""),
            "trend_alert": trend_info.get("alert", False),
            "last_emotions": trend_info.get("last_emotions", [])
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
        """
        判断当前问题是否为追问（指代上一轮主题）
        """
        if not last_question:
            return False
        # 如果是“它”“这个”“那个”等指代词，或者问题很短，很可能是追问
        if re.search(r'^(它|这个|那个|这|那|有.*吗|什么|怎么样|如何|好玩吗|值得去吗)', question):
            return True
        # 如果问题中不包含景点名称（且上一轮包含），也可能是追问
        # 这里简单判断：当前问题不含任何已知景点名称，而上一轮包含
        attraction_names = ["灵山大佛", "九龙灌浴", "灵山梵宫", "五印坛城", "祥符禅寺", "拈花广场", "梵天花海", "香月花街", "五灯湖", "灵山大照壁", "阿育王柱", "百子戏弥勒", "曼飞龙塔", "无尽意斋"]
        has_attraction_in_current = any(name in question for name in attraction_names)
        has_attraction_in_last = any(name in last_question for name in attraction_names)
        if has_attraction_in_last and not has_attraction_in_current:
            return True
        return False

    def chat(self, question: str, context: str = "", session_id: str = None, history: list = None) -> dict:
        if not self.is_ready():
            return {"success": False, "answer": "", "error": "LLM not ready"}

        if session_id:
            session_data = self.get_or_create_session(session_id)
            history = session_data.get("history", [])
            last_context = session_data.get("last_context", "")
            last_question = session_data.get("last_question", "")  # 新增
            stored_interests = session_data.get("interests", [])
            stored_travel_context = session_data.get("travel_context", {})
            emotion_history = session_data.get("emotion_history", [])
            print(f"[LLM] 会话 {session_id} 当前状态:")
            print(f"   - interests: {stored_interests}")
            print(f"   - travel_context: {stored_travel_context}")
            print(f"   - emotion_history: {len(emotion_history)} 条记录")
            print(f"   - last_question: {last_question}")
        else:
            session_data = None
            history = history or []
            last_context = ""
            last_question = ""
            stored_interests = []
            stored_travel_context = {}
            emotion_history = []

        if self._is_social_question(question):
            answer = self._generate_social_response(question, history)
            if session_id and session_data:
                session_data["history"].append({"role": "user", "content": question})
                session_data["history"].append({"role": "assistant", "content": answer})
                session_data["last_question"] = question
            return {"success": True, "answer": answer, "error": None}

        # ===== 判断是否为追问，决定是否复用context =====
        is_follow_up = self._is_follow_up_question(question, last_question)
        if is_follow_up and not context and last_context:
            print(f"[LLM] 检测到追问，复用上一轮 context（但可能主题不符，需要重新检索）")
            # 追问时，如果上一轮context与当前问题主题不符（比如上一轮是高度，这一轮是特色），应该重新检索
            # 简单的做法：如果当前问题是“特色”类，且上一轮context不包含“特色”相关，则视为无效，需要重新检索
            if ("特色" in question or "看点" in question or "亮点" in question) and "特色" not in last_context:
                print(f"[LLM] 追问主题变化（特色），强制重新检索")
                context = ""  # 清空context，强制重新检索
            else:
                context = last_context

        # 如果context为空，则使用RAG检索
        if not context:
            # 实际上，RAG检索在路由层已经做过，但这里为了安全，如果context为空则尝试重新检索
            # 但路由层已经有RAG逻辑，这里不会再检索，所以我们需要在路由层处理。
            # 但为了修复，我们可以让路由层传入context，如果context为空，说明没有检索到，这时我们可以在chat内部调用RAG？
            # 更好的方式是在路由层已经做了，但我们可以在这里如果context为空且是追问，则尝试改进检索。
            # 但为了不破坏结构，我们只能依赖路由层传入的context。
            # 所以我们修改路由层逻辑，让它在context为空时，针对追问进行重试。
            # 但由于路由层不在这里，我只能在chat中加上补充逻辑。
            # 先简单处理：打印日志，提示RAG未检索到。
            print(f"[LLM] context为空，将尝试使用已有知识或拒答")

        # ===== 检测情绪、兴趣等（与之前相同） =====
        env_context = self._extract_environment_context(question)
        if env_context.get("has_info"):
            print(f"[LLM] 检测到环境信息: {env_context}")

        emotion_info = self._detect_emotion(question, history, emotion_history)
        if emotion_info.get("has_emotion"):
            print(f"[LLM] 检测到{emotion_info['emotion']}情绪")
            print(f"   - 强度: {emotion_info['intensity']}/10")
            print(f"   - 权重: {emotion_info['weight']}×")
            print(f"   - 触发词: {emotion_info['trigger_words']}")
            if emotion_info.get("is_complaint"):
                print(f"   ⚠️ 检测到投诉！权重提升至 {emotion_info['weight']}×")
            if emotion_info.get("trend") != "new":
                print(f"   - 趋势: {emotion_info.get('trend')} ({emotion_info.get('trend_message', '')})")
            if emotion_info.get("trend_alert"):
                print(f"   🚨 预警：连续负面情绪，触发安抚模式！")
            if session_data:
                session_data["last_emotion"] = emotion_info
                emotion_history.append({"emotion": emotion_info["emotion"], "intensity": emotion_info["intensity"], "weight": emotion_info["weight"], "is_complaint": emotion_info.get("is_complaint", False), "timestamp": len(emotion_history)})
                if len(emotion_history) > 5:
                    emotion_history = emotion_history[-5:]
                session_data["emotion_history"] = emotion_history

        is_route_question = self._is_route_question(question)
        interest_info = self._detect_interest(question, stored_interests)
        print(f"[LLM] 兴趣检测结果: {interest_info.get('route_key') if interest_info.get('has_interest') else '无'}")
        if interest_info.get("is_contextual_update"):
            print(f"[LLM] 检测到补充信息（同行人），保持原有兴趣不变")

        travel_context = self._extract_travel_context_from_question(question)
        print(f"[LLM] 旅游上下文: {travel_context}")

        if interest_info.get("has_interest") and not interest_info.get("from_memory") and not interest_info.get("is_contextual_update"):
            new_interest = interest_info["route_key"]
            if new_interest not in stored_interests:
                stored_interests.append(new_interest)
                if session_data:
                    session_data["interests"] = stored_interests
                    print(f"[LLM] 保存兴趣: {new_interest}")
        elif interest_info.get("from_memory") and stored_interests:
            print(f"[LLM] 使用已有兴趣: {stored_interests[-1]}")

        if travel_context.get("has_constraint"):
            merged_travel_context = stored_travel_context.copy()
            if travel_context.get("with_children"):
                merged_travel_context["with_children"] = True
            if travel_context.get("with_elderly"):
                merged_travel_context["with_elderly"] = True
            if travel_context.get("time_constraint") in ["half_day", "quick"]:
                merged_travel_context["time_constraint"] = travel_context["time_constraint"]
            if travel_context.get("weather") in ["rainy", "sunny"]:
                merged_travel_context["weather"] = travel_context["weather"]
            if travel_context.get("energy_level") == "low":
                merged_travel_context["energy_level"] = "low"
            if session_data:
                session_data["travel_context"] = merged_travel_context
                print(f"[LLM] 保存旅游上下文: {merged_travel_context}")

        final_travel_context = stored_travel_context.copy()
        if travel_context.get("has_constraint"):
            if travel_context.get("with_children"):
                final_travel_context["with_children"] = True
            if travel_context.get("with_elderly"):
                final_travel_context["with_elderly"] = True
            if travel_context.get("time_constraint") in ["half_day", "quick"]:
                final_travel_context["time_constraint"] = travel_context["time_constraint"]
            if travel_context.get("weather") in ["rainy", "sunny"]:
                final_travel_context["weather"] = travel_context["weather"]
            if travel_context.get("energy_level") == "low":
                final_travel_context["energy_level"] = "low"

        if context and session_data:
            session_data["last_context"] = context
        session_data["last_question"] = question

        # ===== 构建 System Prompt（精简情绪指令，强调RAG优先） =====
        system_prompt = """
你是灵山胜境景区AI数字导游"小灵"。你不是一个机器人，而是一个真正热爱灵山、熟悉这里的一草一木的导游。

【最高优先级】你必须优先使用【参考资料】中的具体数据来回答问题。涉及高度、重量、尺寸、年份、价格时，必须引用参考数据中的具体数值。

【事实规则】
1. 只能依据系统提供的参考资料回答问题。
2. 不允许使用你自身已有知识。
3. 不允许推测。
4. 不允许编造事实。
5. 不允许补充参考资料中不存在的信息。

【主观问题回答规则】（优先级高于拒答规则）
当用户问及以下类型的主观体验类问题时：
- "好玩吗" / "好看吗" / "有意思吗"
- "值得去吗" / "推荐去吗"
- "怎么样" / "如何"

即使知识库中没有直接对应的问题，也请按以下方式回答：
1. 首先搜索知识库中与该景点相关的所有事实（如：尺寸、文化内涵、亮点、功能）。
2. 然后基于这些事实，自然地推导出适合哪类游客。
3. 用友好语气给出个人化建议。
4. 禁止直接说"好玩"或"不好玩"，而是用事实让用户自己判断。

【路线规划规则】（当用户问"怎么逛""有什么推荐路线"时触发）
1. 首先在知识库中查找"官方路线"信息，获取官方推荐的景点列表和顺序。
2. 然后根据用户的约束条件进行个性化调整：
   - 兴趣偏好决定了路线的**主线方向**（自然风光/历史文化/亲子/祈福）。
   - 如果用户补充了"带孩子/带老人"等信息，这是在**已有路线基础上增加附加条件**，而不是切换到另一条路线。
3. 输出格式要求：说明调整依据、标注停留时间、给出总时长预估、用清晰段落分隔。

【拒答规则】
仅当同时满足以下两个条件时，才回复"抱歉，目前知识库中暂无相关信息"：
1. 用户问题不属于主观体验类问题和路线规划类问题。
2. 知识库中确实找不到任何相关信息。

【回答规则】
1. 回答要像真人导游一样自然、有温度。
2. 优先引用参考资料中的具体数据。
3. 涉及时间、年份、票价、距离、数量，必须严格按照参考资料回答。
4. 不要使用"以下是我为您推荐的"这种模板化开头。

【格式规则】
1. 不要使用任何Markdown格式符号（**、*、#等）。
2. 每句话用句号、感叹号或问号正常结尾。
3. 每个完整的段落结束后换行两次，留下空行。
4. 列出景点时，用"·"或自然衔接。"""

        if is_route_question:
            system_prompt += """

【当前任务：路线规划】
用户正在问关于游览路线的问题。请严格按照以下方式回答：
1. 首先在知识库中检索"官方路线"数据作为骨架。
2. 结合用户画像中已存储的兴趣偏好和时间约束。
3. 输出结构化的路线推荐，包含具体景点、建议时长和顺序。
4. 不要遗漏官方路线中的核心景点，除非有明确的约束条件。"""

        # ===== 精简情绪指令 =====
        if emotion_info.get("has_emotion"):
            emotion = emotion_info["emotion"]
            intensity = emotion_info["intensity"]
            weight = emotion_info["weight"]
            trend_alert = emotion_info.get("trend_alert", False)

            if emotion_info.get("residual"):
                system_prompt += "\n【情绪】用户情绪正在恢复，仍有轻微负面残留。→ 语气温和，正常推荐，适当询问是否需要进一步帮助。"

            elif emotion == "severe_negative" or emotion_info.get("is_complaint"):
                system_prompt += f"\n【情绪】强烈不满/投诉（强度{intensity}/10，权重{weight}×）。"
                if trend_alert:
                    system_prompt += "\n⚠️ 连续负面反馈，需加倍重视！"
                system_prompt += "\n→ 真诚道歉，不用'理解您的感受'模板"
                system_prompt += "\n→ 主动询问不满原因"
                system_prompt += "\n→ 提供替代方案"
                system_prompt += "\n→ 表达愿意解决问题的诚意"

            elif emotion == "moderate_negative":
                system_prompt += f"\n【情绪】明显不满意（强度{intensity}/10）。"
                if trend_alert:
                    system_prompt += "\n⚠️ 情绪有恶化趋势，需重点关注。"
                system_prompt += "\n→ 共情回应：'确实有时候期望和实际会有落差...'"
                system_prompt += "\n→ 主动调整推荐方向"
                system_prompt += "\n→ 语气温和耐心"

            elif emotion == "fatigue":
                system_prompt += f"\n【情绪】疲惫（强度{intensity}/10）。"
                if trend_alert:
                    system_prompt += "\n⚠️ 用户情绪不稳定，需特别关怀。"
                system_prompt += "\n→ 关心用户状态：'走了这么久辛苦了...'"
                system_prompt += "\n→ 推荐具体休息点（灵山精舍茶室、菩提大道树荫长椅、鹿鸣谷林间空地、梵宫内休息区、五明桥、拈花广场）"
                system_prompt += "\n→ 主动询问是否需要调整路线或乘坐观光车"

            elif emotion == "confusion":
                system_prompt += f"\n【情绪】困惑/迷茫（强度{intensity}/10）。"
                system_prompt += "\n→ 清晰指引，不要绕弯子"
                system_prompt += "\n→ 给出具体路线描述或地标参照物"
                system_prompt += "\n→ 语气耐心确定"

            elif emotion == "mild_negative":
                system_prompt += f"\n【情绪】轻微失望（强度{intensity}/10）。"
                if trend_alert:
                    system_prompt += f"\n⚠️ 情绪有下滑趋势，建议温和引导。"
                system_prompt += "\n→ 轻松回应：'可能确实不太对胃口，我给您换个推荐...'"
                system_prompt += "\n→ 提供风格不同的替代方案"

            elif emotion == "strong_positive":
                system_prompt += f"\n【情绪】非常兴奋/震撼（强度{intensity}/10）。"
                system_prompt += "\n→ 热情回应：'是吧！我第一次去也是这种感觉！'"
                system_prompt += "\n→ 推荐同类或升级体验"
                system_prompt += "\n→ 语气热情活泼，像朋友分享"

            elif emotion == "positive":
                system_prompt += f"\n【情绪】满意/开心（强度{intensity}/10）。"
                system_prompt += "\n→ 自然回应：'太好了！您喜欢就好。'"
                system_prompt += "\n→ 推荐1-2个风格相似的景点"

            elif emotion == "mild_positive":
                system_prompt += "\n【情绪】情绪不错。"
                system_prompt += "\n→ 保持亲切自然语气"
                system_prompt += "\n→ 正常推荐"

        # ===== 精简自检与补救 =====
        if emotion_info.get("has_emotion"):
            emotion = emotion_info.get("emotion", "")
            if emotion in ["severe_negative", "moderate_negative", "mild_negative", "fatigue", "confusion"]:
                system_prompt += """
【自检与补救】
回答后自我检查：
1. 是否真诚回应了用户情绪？
2. 用户问题是否得到圆满解决？如未解决，主动提出补救方案。
3. 负面情绪时结尾加关怀语，正面时加鼓励语。"""
                if emotion == "fatigue":
                    system_prompt += "\n【特别提醒】用户疲惫，必须推荐具体休息点（不可说'知识库暂无'），主动询问是否调整路线，结尾加关怀语。"
                if emotion == "severe_negative" or emotion_info.get("is_complaint"):
                    system_prompt += "\n【投诉处理】确保道歉、询问原因、提供替代方案、表达持续帮助态度。"

        # ===== 注入用户画像 =====
        user_profile_parts = []
        if interest_info.get("has_interest"):
            route_name = interest_info["route_name"]
            spots = " → ".join(interest_info["spots"])
            description = interest_info["description"]
            highlights = interest_info["highlights"]
            keywords = "、".join(interest_info.get("matched_keywords", [interest_info["route_key"]]))
            user_profile_parts.append(f"""
【用户偏好】
用户对「{keywords}」感兴趣。
推荐路线：「{route_name}」
路线：{spots}
简介：{description}
亮点：{highlights}""")
        if final_travel_context.get("time_constraint") == "half_day":
            user_profile_parts.append("用户只有半天时间，推荐路线控制在3-4个景点以内。")
        elif final_travel_context.get("time_constraint") == "quick":
            user_profile_parts.append("用户时间紧张，推荐路线控制在2-3个核心景点以内。")
        if final_travel_context.get("with_children"):
            user_profile_parts.append("用户带孩子出行，请在已有路线基础上增加互动性强、适合孩子的景点。")
        if final_travel_context.get("with_elderly"):
            user_profile_parts.append("用户有老人同行，请在已有路线基础上选择平缓易行、有休息设施的景点。")
        if final_travel_context.get("weather") == "rainy":
            user_profile_parts.append("当前下雨，请将室外景点替换为室内景点。")
        if final_travel_context.get("energy_level") == "low":
            user_profile_parts.append("用户体力一般，建议全程乘坐观光车。")
        if user_profile_parts:
            system_prompt += f"\n\n【用户画像】\n{''.join(user_profile_parts)}"

        # ===== 注入环境信息 =====
        env_parts = []
        if env_context.get("has_info"):
            if env_context.get("weather") != "unknown":
                env_parts.append(self._get_weather_adjustment(env_context["weather"]))
            if env_context.get("time") != "unknown":
                env_parts.append(self._get_time_adjustment(env_context["time"]))
        if env_parts:
            system_prompt += f"\n\n{''.join(env_parts)}"

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

请严格依据参考资料回答。"""

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

            if session_data:
                session_data["history"].append({"role": "user", "content": question})
                session_data["history"].append({"role": "assistant", "content": answer})
                if len(session_data["history"]) > 30:
                    session_data["history"] = session_data["history"][-30:]

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