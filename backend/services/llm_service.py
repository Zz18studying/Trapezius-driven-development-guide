# -*- coding: utf-8 -*-
"""
大模型调用服务 - 使用 DeepSeek API + 对话记忆 + 用户画像 + 环境感知 + 情绪感知 + 路线规划
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
                "interests": [],
                "travel_context": {},
                "last_emotion": {"emotion": "neutral", "has_emotion": False}
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
        """判断是否为路线规划类问题"""
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

    def _detect_emotion(self, question: str, history: list = None) -> dict:
        """细粒度情绪检测"""
        strong_negative_patterns = [
            r'太差|极差|垃圾|后悔来|再也不|劝退|浪费时间|垃圾|烂'
        ]
        negative_patterns = [
            r'不好玩|一般般|失望|差评', r'不满意', r'坑', r'不值',
            r'累了?', r'太累', r'走不动', r'好累', r'疲惫',
            r'太热', r'太晒', r'太冷', r'难受', r'不舒服', r'不好'
        ]
        positive_patterns = [
            r'好玩', r'开心', r'满意', r'很棒', r'不错',
            r'值得', r'喜欢', r'推荐'
        ]
        strong_positive_patterns = [
            r'太震撼|震撼到了|太美|太漂亮|绝了|无敌|完美|特别值得|太棒了'
        ]
        
        triggered_negative = []
        triggered_positive = []
        triggered_strong_negative = []
        triggered_strong_positive = []
        
        for pattern in strong_negative_patterns:
            if re.search(pattern, question):
                triggered_strong_negative.append(pattern)
        for pattern in negative_patterns:
            if re.search(pattern, question):
                triggered_negative.append(pattern)
        for pattern in positive_patterns:
            if re.search(pattern, question):
                triggered_positive.append(pattern)
        for pattern in strong_positive_patterns:
            if re.search(pattern, question):
                triggered_strong_positive.append(pattern)
        
        if triggered_strong_negative:
            return {"emotion": "strong_negative", "has_emotion": True, "intensity": 0.9, "trigger_words": triggered_strong_negative}
        elif triggered_negative:
            return {"emotion": "negative", "has_emotion": True, "intensity": 0.6, "trigger_words": triggered_negative}
        elif triggered_strong_positive:
            return {"emotion": "strong_positive", "has_emotion": True, "intensity": 0.9, "trigger_words": triggered_strong_positive}
        elif triggered_positive:
            return {"emotion": "positive", "has_emotion": True, "intensity": 0.6, "trigger_words": triggered_positive}
        else:
            return {"emotion": "neutral", "has_emotion": False, "intensity": 0.0, "trigger_words": []}

    def _detect_interest(self, question: str, stored_interests: list = None) -> dict:
        """
        检测用户兴趣：区分"兴趣切换"和"约束叠加"
        - 如果用户说"带孩子/带老人"且没有切换信号，保持原有兴趣
        - 如果用户说"更喜欢/其实更/也喜欢"，切换兴趣
        """
        # ===== 检测是否为"补充信息"而非"兴趣切换" =====
        # 如果问题包含同行人信息（带孩子/带老人），且没有切换信号
        if re.search(r'孩子|小孩|带.*孩子|带.*老人|亲子|家庭', question):
            # 检查是否有切换信号
            has_switch_signal = re.search(r'也喜欢|还喜欢|其实更|更喜欢|但是.*喜欢|不过.*喜欢|更喜欢|更想', question)
            if not has_switch_signal:
                # 没有切换信号 → 保持原有兴趣
                if stored_interests and len(stored_interests) > 0:
                    route_key = stored_interests[-1]
                    route = config.ROUTES.get(route_key)
                    if route:
                        return {
                            "has_interest": True,
                            "route_key": route_key,
                            "route_name": route["name"],
                            "spots": route["spots"],
                            "description": route["description"],
                            "highlights": route["highlights"],
                            "matched_keywords": [route_key],
                            "from_memory": True,
                            "is_contextual_update": True  # 标记为补充信息
                        }

        # ===== 检查是否有明确的兴趣切换信号 =====
        matched_interests = []
        route_key = None
        for keyword, route in config.INTEREST_TO_ROUTE.items():
            if keyword in question:
                matched_interests.append(keyword)
                if route_key is None:
                    route_key = route

        # 如果没有检测到新兴趣
        if route_key is None:
            if stored_interests and len(stored_interests) > 0:
                route_key = stored_interests[-1]
                route = config.ROUTES.get(route_key)
                if route:
                    return {
                        "has_interest": True,
                        "route_key": route_key,
                        "route_name": route["name"],
                        "spots": route["spots"],
                        "description": route["description"],
                        "highlights": route["highlights"],
                        "matched_keywords": [route_key],
                        "from_memory": True
                    }
            return {"has_interest": False}

        route = config.ROUTES.get(route_key)
        if not route:
            return {"has_interest": False}

        return {
            "has_interest": True,
            "route_key": route_key,
            "route_name": route["name"],
            "spots": route["spots"],
            "description": route["description"],
            "highlights": route["highlights"],
            "matched_keywords": matched_interests,
            "from_memory": False
        }

    def chat(self, question: str, context: str = "", session_id: str = None, history: list = None) -> dict:
        if not self.is_ready():
            return {"success": False, "answer": "", "error": "LLM not ready"}

        if session_id:
            session_data = self.get_or_create_session(session_id)
            history = session_data.get("history", [])
            last_context = session_data.get("last_context", "")
            stored_interests = session_data.get("interests", [])
            stored_travel_context = session_data.get("travel_context", {})
            
            print(f"[LLM] 会话 {session_id} 当前状态:")
            print(f"   - interests: {stored_interests}")
            print(f"   - travel_context: {stored_travel_context}")
        else:
            session_data = None
            history = history or []
            last_context = ""
            stored_interests = []
            stored_travel_context = {}

        # ===== 社交问题直接回复 =====
        if self._is_social_question(question):
            answer = self._generate_social_response(question, history)
            if session_id and session_data:
                session_data["history"].append({"role": "user", "content": question})
                session_data["history"].append({"role": "assistant", "content": answer})
            return {"success": True, "answer": answer, "error": None}

        # ===== 复用上一轮 context =====
        if not context and last_context:
            print(f"[LLM] 复用上一轮 context")
            context = last_context

        env_context = self._extract_environment_context(question)
        if env_context.get("has_info"):
            print(f"[LLM] 检测到环境信息: {env_context}")

        # ===== 检测情绪 =====
        emotion_info = self._detect_emotion(question, history)
        if emotion_info.get("has_emotion"):
            print(f"[LLM] 检测到{emotion_info['emotion']}情绪，触发词: {emotion_info['trigger_words']}")
            if session_data:
                session_data["last_emotion"] = emotion_info

        # ===== 检测是否为路线类问题 =====
        is_route_question = self._is_route_question(question)

        # ===== 检测兴趣（区分切换/叠加） =====
        interest_info = self._detect_interest(question, stored_interests)
        print(f"[LLM] 兴趣检测结果: {interest_info.get('route_key') if interest_info.get('has_interest') else '无'}")
        if interest_info.get("is_contextual_update"):
            print(f"[LLM] 检测到补充信息（同行人），保持原有兴趣不变")

        # ===== 提取旅游上下文（增强版） =====
        travel_context = self._extract_travel_context_from_question(question)
        print(f"[LLM] 旅游上下文: {travel_context}")

        # ===== 保存新兴趣（仅当不是补充信息时） =====
        if interest_info.get("has_interest") and not interest_info.get("from_memory") and not interest_info.get("is_contextual_update"):
            new_interest = interest_info["route_key"]
            if new_interest not in stored_interests:
                stored_interests.append(new_interest)
                if session_data:
                    session_data["interests"] = stored_interests
                    print(f"[LLM] 保存兴趣: {new_interest}")
        elif interest_info.get("from_memory") and stored_interests:
            print(f"[LLM] 使用已有兴趣: {stored_interests[-1]}")

        # ===== 保存旅游上下文 =====
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

        # ===== 合并已存储的旅游上下文 =====
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

        # ===== 构建 System Prompt =====
        system_prompt = """
你是灵山胜境景区AI数字导游"小灵"。你不是一个机器人，而是一个真正热爱灵山、熟悉这里的一草一木的导游。

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
5. 回答要有温度，像真人导游在推荐。

示例：
问："灵山大照壁好玩吗"
答："灵山大照壁被誉为'华夏第一壁'，长39.8米，高7米，正面有赵朴初先生题写的鎏金'灵山胜境'四字，背面刻有《小灵山》诗刻。对于喜欢打卡拍照、感受佛教文化氛围的游客来说，这里是入园后的第一个绝佳打卡点，能拍到湖光壁影同框的美景，值得驻足品味。"

【路线规划规则】（当用户问"怎么逛""有什么推荐路线"时触发）
1. 首先在知识库中查找"官方路线"信息，获取官方推荐的景点列表和顺序。
2. 然后根据用户的约束条件进行个性化调整：
   - 兴趣偏好决定了路线的**主线方向**（自然风光/历史文化/亲子/祈福）。
   - 如果用户补充了"带孩子/带老人"等信息，这是在**已有路线基础上增加附加条件**，而不是切换到另一条路线。
   - 例如：用户喜欢自然风光 + 带孩子 → 在自然风光路线中增加适合孩子的景点（如九龙灌浴、百子戏弥勒），而不是完全切换到亲子路线。
   - 例如：用户喜欢历史文化 + 只有半天时间 → 在历史文化路线中精简景点，保留最核心的3-4个。
3. 输出格式要求：
   - 说明"基于您喜欢的XX路线，考虑到您带孩子/老人，做了以下调整"
   - 每个景点标注建议停留时间
   - 给出总时长预估
   - 用清晰的段落分隔

【拒答规则】
仅当同时满足以下两个条件时，才回复"抱歉，目前知识库中暂无相关信息"：
1. 用户问题不属于主观体验类问题和路线规划类问题。
2. 知识库中确实找不到任何相关信息。

【回答规则】
1. 回答要像真人导游一样自然、有温度。
2. 优先引用参考资料中的具体数据。
3. 涉及时间、年份、票价、距离、数量，必须严格按照参考资料回答。
4. 不要使用"以下是我为您推荐的"这种模板化开头，直接用自然的语言切入。

【格式规则】
1. 不要使用任何Markdown格式符号（**、*、#等）。
2. 每句话用句号、感叹号或问号正常结尾。
3. 每个完整的段落结束后换行两次，留下空行。
4. 列出景点时，用"·"或自然衔接，不要使用序号。"""

        # ===== 如果是路线问题，在System Prompt中加强路线规划指令 =====
        if is_route_question:
            system_prompt += """

【当前任务：路线规划】
用户正在问关于游览路线的问题。请严格按照以下方式回答：
1. 首先在知识库中检索"官方路线"数据作为骨架。
2. 结合用户画像中已存储的兴趣偏好和时间约束。
3. 输出结构化的路线推荐，包含具体景点、建议时长和顺序。
4. 不要遗漏官方路线中的核心景点，除非有明确的约束条件（如雨天、时间不足）。"""

        # ===== 注入情绪指令 =====
        if emotion_info.get("has_emotion"):
            if emotion_info["emotion"] == "strong_negative":
                system_prompt += f"""
【情绪感知】用户感到强烈不满（{', '.join(emotion_info['trigger_words'])}）。

⚠️ 这是最需要谨慎处理的情况。请严格按以下方式回答：

【回答风格】
1. 首先，用一句真诚的共情开头，表达理解和歉意。不要用"很抱歉"这种客服话术，要用更自然的表达，比如：
   - "听您这么说，我心里也挺不是滋味的..."
   - "我完全理解您的感受，确实有些地方可能不太符合预期..."

2. 不要直接罗列"您可以..."，而是先理解原因，再给出建议：
   - "不知道是哪个方面让您觉得不够好呢？"

3. 主动给出1-2个与当前体验不同的选择：
   - 如果觉得大佛太商业化 → 推荐无尽意斋、鹿鸣谷等清净的地方
   - 如果觉得梵宫不够有趣 → 推荐互动性更强的九龙灌浴、百子戏弥勒

4. 语气要真诚、温和，不要急于推销景点。"""
            
            elif emotion_info["emotion"] == "negative":
                system_prompt += f"""
【情绪感知】用户有些失望或不满意（{', '.join(emotion_info['trigger_words'])}）。

【回答风格】
1. 先共情，用自然的话语表达理解，比如：
   - "唉，确实有时候期望和实际会有落差..."
   - "理解您的感受，我给您换个思路推荐。"

2. 如果是"累了"：
   - 先推荐休息点（灵山精舍茶室、菩提大道的树荫长椅）
   - 再问是否需要调整路线

3. 如果是一般性的"不好玩"：
   - 换个方向推荐（从文化→趣味，或从室外→室内）
   - 主动问"您是想看更震撼的，还是想找轻松有趣的？"

4. 语气要温和、耐心，不要急于解释或反驳。"""
            
            elif emotion_info["emotion"] == "strong_positive":
                system_prompt += f"""
【情绪感知】用户非常兴奋/震撼（{', '.join(emotion_info['trigger_words'])}）。

【回答风格】
1. 用同样热情的语气回应，比如：
   "是吧！我第一次去梵宫的时候也是这种感觉，站在穹顶下面整个人都愣住了。"

2. 推荐同类或升级体验：
   - 被梵宫震撼 → 推荐五印坛城
   - 被艺术震撼 → 推荐看《吉祥颂》演出
   - 被建筑震撼 → 推荐到香水海拍全景

3. 可以稍微多给一些推荐，语气像"分享秘密"一样。
4. 语气热情、活泼，像朋友分享。"""
            
            elif emotion_info["emotion"] == "positive":
                system_prompt += f"""
【情绪感知】用户感到满意/开心（{', '.join(emotion_info['trigger_words'])}）。

【回答风格】
1. 用自然的语气回应，比如：
   - "太好了！您喜欢就好。"
   - "开心！那我觉得这个地方也适合您..."

2. 推荐1-2个风格相似的景点或体验。
3. 语气亲切、自然，不要过于热烈。"""

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
            user_profile_parts.append("用户带孩子出行，请在已有路线基础上增加互动性强、适合孩子的景点（如九龙灌浴、百子戏弥勒），不要完全切换路线类型。")

        if final_travel_context.get("with_elderly"):
            user_profile_parts.append("用户有老人同行，请在已有路线基础上选择平缓易行、有休息设施的景点，建议全程观光车。")

        if final_travel_context.get("weather") == "rainy":
            user_profile_parts.append("当前下雨，请将室外景点替换为室内景点（梵宫、博览馆、五印坛城）。")

        if final_travel_context.get("energy_level") == "low":
            user_profile_parts.append("用户体力一般，建议全程乘坐观光车，减少步行距离。")

        if user_profile_parts:
            system_prompt += f"""

【用户画像】
{''.join(user_profile_parts)}"""

        # ===== 注入环境信息 =====
        env_parts = []
        if env_context.get("has_info"):
            if env_context.get("weather") != "unknown":
                env_parts.append(self._get_weather_adjustment(env_context["weather"]))
            if env_context.get("time") != "unknown":
                env_parts.append(self._get_time_adjustment(env_context["time"]))
        
        if env_parts:
            system_prompt += f"""

{''.join(env_parts)}"""

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