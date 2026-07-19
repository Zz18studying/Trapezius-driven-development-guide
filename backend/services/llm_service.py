# -*- coding: utf-8 -*-
"""
大模型调用服务。
"""

import os
import sys
import re
import json
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from services.knowledge_constants import extract_attraction_name


class LLMService:
    def __init__(self):
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", getattr(config, "DEEPSEEK_API_KEY", ""))
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
        self.model = getattr(config, "DEEPSEEK_MODEL", "deepseek-v4-flash")
        self.verifier_model = getattr(config, "DEEPSEEK_VERIFIER_MODEL", self.model)
        print("✅ LLM服务初始化成功（DeepSeek API + RAG 约束生成）")
        print(f"   模型: {self.model}")
        print(f"   核验模型: {self.verifier_model}")

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

    def _append_history(self, session_data: dict, question: str, answer: str):
        session_data["history"].append({"role": "user", "content": question})
        session_data["history"].append({"role": "assistant", "content": answer})
        if len(session_data["history"]) > 12:
            session_data["history"] = session_data["history"][-12:]
        session_data["last_question"] = question

    def remember_turn(self, session_id: str, question: str, answer: str):
        if not session_id:
            return
        session_data = self.get_or_create_session(session_id)
        self._append_history(session_data, question, answer)

    def _is_social_question(self, question: str) -> bool:
        if self.needs_knowledge_base(question):
            return False
        social_patterns = [
            r"^(你好|您好|哈喽|在吗|在不在|有人吗)[呀么啊嘛~!！。]*$",
            r"^hi[!！。]*$",
            r"^hello[!！。]*$",
            r"^(你好|您好)?[，,\s]*(我叫|我的名字叫)[\u4e00-\u9fa5]{1,8}[。!！]*$",
            r"^我是(?:游客|客人|朋友)[。!！]*$",
            r"你叫什么名字[？?]?$",
            r"你是谁[？?]?$",
            r"你的名字[？?]?$",
            r"你能做什么[？?]?$",
            r"你可以帮我什么[？?]?$",
            r"有什么可以帮我[？?]?$",
            r"还记得我叫什么[吗？?]?$",
            r"知道我叫什么[吗？?]?$",
            r"^[谢感谢]+[你呀]?[！～。]*$",
            r"^[再见拜拜]+[～！。]*$",
        ]
        return any(re.search(pattern, question, re.IGNORECASE) for pattern in social_patterns)

    def is_social_question(self, question: str) -> bool:
        return self._is_social_question(question)

    def needs_knowledge_base(self, question: str) -> bool:
        """判断是否需要进入景区知识库链路。普通寒暄、身份介绍不走 RAG/核验。"""
        if not question:
            return False
        if extract_attraction_name(question):
            return True
        knowledge_keywords = [
            "灵山", "胜境", "景区", "景点", "大佛", "梵宫", "九龙", "坛城", "禅寺",
            "拈花", "门票", "票价", "多少钱", "开放", "几点", "时间", "表演", "演出",
            "路线", "怎么玩", "怎么逛", "怎么去", "停车", "观光车", "雨天", "下雨",
            "孩子", "亲子", "老人", "半天", "推荐", "好玩", "特色", "看点", "历史",
            "文化", "高度", "多高", "在哪里", "介绍一下","开发团队"
        ]
        return any(keyword in question for keyword in knowledge_keywords)

    def _extract_name_from_history(self, history: list) -> str:
        for msg in reversed(history[-10:]):
            if msg.get("role") != "user":
                continue
            content = msg.get("content", "")
            for pattern in [r"我叫([\u4e00-\u9fa5]{1,8})", r"名字叫([\u4e00-\u9fa5]{1,8})"]:
                match = re.search(pattern, content)
                if match:
                    return match.group(1)
        return ""

    def _generate_social_response(self, question: str, history: list = None) -> str:
        history = history or []
        if re.search(r"我叫什么|还记得我叫什么|知道我叫什么", question):
            name = self._extract_name_from_history(history)
            return f"你叫{name}呀，我记得。" if name else "我还不知道你的名字，可以告诉我吗？"
        if re.search(r"你叫什么|你是谁|你的名字", question):
            return "我是灵山胜境景区的 AI 数字导游小灵，负责景点讲解和游览建议。"
        if re.search(r"你能做什么|你可以帮我什么|有什么可以帮我", question):
            return "我可以帮你介绍灵山胜境的景点、门票、开放时间、演出场次和游览路线，也可以根据亲子、老人、雨天、半天游等情况给你安排建议。"
        if re.search(r"我叫|名字叫", question):
            match = re.search(r"(?:我叫|名字叫)([\u4e00-\u9fa5]{1,8})", question)
            name = match.group(1) if match else ""
            return f"你好{name}！我是灵山胜境景区的 AI 数字导游小灵，很高兴认识你。" if name else "你好，很高兴认识你。"
        if re.search(r"你好|您好|hi|hello", question, re.IGNORECASE):
            name = self._extract_name_from_history(history)
            prefix = f"你好{name}！" if name else "你好呀！"
            return f"{prefix}我是灵山胜境景区的 AI 数字导游小灵，有关于景点、路线、开放时间等问题都可以问我。"
        if re.search(r"谢谢|感谢", question):
            return "不客气，祝你游玩愉快。"
        if re.search(r"再见|拜拜", question):
            return "再见，祝你旅途愉快。"
        return "你好，我是灵山胜境景区的 AI 数字导游小灵。"

    def _is_route_question(self, question: str) -> bool:
        patterns = [
            r"怎么逛", r"怎么玩", r"路线", r"推荐.*路线", r"应该怎么走",
            r"游览顺序", r"先去哪里", r"怎么安排", r"行程", r"怎么游",
            r"逛完.*需要多久", r"路线规划", r"怎么走比较顺", r"攻略"
        ]
        return any(re.search(pattern, question) for pattern in patterns)

    def _is_advice_question(self, question: str) -> bool:
        """识别可给导游式建议的问题，避免把推荐/路线类问题当成强事实问答卡死。"""
        advice_patterns = [
            r"推荐", r"建议", r"适合", r"攻略", r"怎么玩", r"怎么逛", r"怎么游",
            r"怎么安排", r"行程", r"路线", r"游览", r"游玩", r"先去哪里",
            r"值得去", r"好玩吗", r"轻松", r"省力", r"少走路", r"打卡",
            r"拍照", r"亲子", r"孩子", r"老人", r"父母", r"情侣", r"朋友",
            r"同学", r"闺蜜", r"双人", r"两个人", r"一个人", r"家庭",
            r"雨天", r"下雨", r"半天", r"半日", r"一天", r"首次|第一次"
        ]
        return self._is_route_question(question) or any(re.search(pattern, question) for pattern in advice_patterns)

    def _is_strict_fact_question(self, question: str) -> bool:
        """价格、时间、场次、交通等需要严格依据资料的事实类问题。"""
        strict_patterns = [
            r"多少钱", r"票价", r"门票", r"免费", r"半价", r"优惠",
            r"开放", r"几点", r"时间", r"场次", r"演出", r"表演",
            r"多高", r"高度", r"怎么去", r"怎么走", r"交通", r"停车",
            r"公交", r"自驾", r"观光车"
        ]
        return any(re.search(pattern, question) for pattern in strict_patterns)

    def _extract_travel_context_from_question(self, question: str) -> dict:
        context = {
            "with_children": False,
            "with_elderly": False,
            "with_partner": False,
            "time_constraint": "",
            "weather": "",
            "energy_level": "",
            "has_constraint": False
        }
        if re.search(r"孩子|小孩|小朋友|宝宝|亲子|带娃", question):
            context["with_children"] = True
            context["has_constraint"] = True
        if re.search(r"老人|长辈|父母|爸妈|带父母", question):
            context["with_elderly"] = True
            context["has_constraint"] = True
        if re.search(r"双人|两个人|2个人|情侣|约会|朋友两人", question):
            context["with_partner"] = True
            context["has_constraint"] = True
        if re.search(r"半天|半日|只有.*小时", question):
            context["time_constraint"] = "half_day"
            context["has_constraint"] = True
        elif re.search(r"快速|简单逛|打个卡|2.*小时", question):
            context["time_constraint"] = "quick"
            context["has_constraint"] = True
        if re.search(r"下雨|雨天|淋雨", question):
            context["weather"] = "rainy"
            context["has_constraint"] = True
        elif re.search(r"晒|大太阳|暴晒", question):
            context["weather"] = "sunny"
            context["has_constraint"] = True
        if re.search(r"累了|走不动|体力|太累|脚痛|腿酸", question):
            context["energy_level"] = "low"
            context["has_constraint"] = True
        return context

    def _detect_emotion(self, question: str) -> dict:
        patterns = {
            "complaint": r"太差|极差|垃圾|后悔来|再也不来|劝退|浪费时间|浪费钱|坑人|被骗|投诉|差评|服务差|态度差|体验极差|强烈不满|不值票价",
            "fatigue": r"累了?|太累|走不动|好累|疲惫|脚痛|腿酸|腰酸|体力不支|休息一下|坐一下",
            "dissatisfied": r"不好玩|一般般|失望|不满意|不值|没意思|太热|太晒|太冷|太挤|人太多|排队太久|太贵|性价比低|体验不好"
        }
        for emotion, pattern in patterns.items():
            if re.search(pattern, question):
                return {"emotion": emotion, "has_emotion": True}
        return {"emotion": "neutral", "has_emotion": False}

    def _detect_interest(self, question: str, stored_interests: list = None) -> dict:
        matched = []
        route_key = None
        for keyword, route in config.INTEREST_TO_ROUTE.items():
            if keyword in question:
                matched.append(keyword)
                route_key = route_key or route

        if not route_key and stored_interests:
            route_key = stored_interests[-1]
            matched = [route_key]

        route = config.ROUTES.get(route_key) if route_key else None
        if not route:
            return {"has_interest": False}

        return {
            "has_interest": True,
            "route_key": route_key,
            "route_name": route["name"],
            "spots": route["spots"],
            "highlights": route["highlights"],
            "matched_keywords": matched,
            "from_memory": route_key not in config.INTEREST_TO_ROUTE.values() or not any(k in question for k in matched)
        }

    def _is_follow_up_question(self, question: str, last_question: str) -> bool:
        if not last_question:
            return False
        if re.search(r"^(它|这个|那个|这|那|这里|那里)", question):
            return True
        has_current_attraction = bool(extract_attraction_name(question))
        has_last_attraction = bool(extract_attraction_name(last_question))
        return has_last_attraction and not has_current_attraction and re.search(
            r"^(有.*吗|什么|怎么样|如何|好玩吗|值得去吗|多高|多大|几点|门票|特色|看点)",
            question
        )

    def _get_last_attraction_from_history(self, history: list) -> str:
        for msg in reversed(history[-10:]):
            if msg.get("role") != "user":
                continue
            name = extract_attraction_name(msg.get("content", ""))
            if name:
                return name
        return ""

    def resolve_pronoun(self, question: str, session_id: str) -> str:
        """将追问中的指代词补全为上一轮景点名。"""
        if not session_id or not question:
            return question

        session_data = self.get_or_create_session(session_id)
        last_question = session_data.get("last_question", "")
        history = session_data.get("history", [])
        if not self._is_follow_up_question(question, last_question):
            return question

        last_attraction = extract_attraction_name(last_question) or self._get_last_attraction_from_history(history)
        if not last_attraction:
            return question

        if re.search(r"^(它|这个|那个|这|那|这里|那里)", question):
            new_question = re.sub(r"^(它|这个|那个|这|那|这里|那里)", last_attraction, question)
        else:
            new_question = f"{last_attraction}{question}"

        print(f"[LLM] 指代词补全: '{question}' → '{new_question}'")
        return new_question

    def _merge_travel_context(self, stored: dict, current: dict) -> dict:
        merged = stored.copy() if stored else {}
        if current.get("with_children"):
            merged["with_children"] = True
        if current.get("with_elderly"):
            merged["with_elderly"] = True
        if current.get("with_partner"):
            merged["with_partner"] = True
        if current.get("time_constraint"):
            merged["time_constraint"] = current["time_constraint"]
        if current.get("weather"):
            merged["weather"] = current["weather"]
        if current.get("energy_level"):
            merged["energy_level"] = current["energy_level"]
        return merged

    def _build_user_notes(self, question: str, session_data: dict) -> str:
        stored_interests = session_data.get("interests", []) if session_data else []
        stored_travel_context = session_data.get("travel_context", {}) if session_data else {}

        interest = self._detect_interest(question, stored_interests)
        travel_context = self._extract_travel_context_from_question(question)
        final_travel_context = self._merge_travel_context(stored_travel_context, travel_context)

        if session_data:
            if interest.get("has_interest") and not interest.get("from_memory"):
                route_key = interest["route_key"]
                if route_key not in stored_interests:
                    stored_interests.append(route_key)
                    session_data["interests"] = stored_interests
            if travel_context.get("has_constraint"):
                session_data["travel_context"] = final_travel_context

        notes = []
        if interest.get("has_interest"):
            route_name = interest["route_name"]
            spots = " → ".join(interest["spots"])
            highlights = interest["highlights"]
            keywords = "、".join(interest.get("matched_keywords") or [interest["route_key"]])
            if self._is_route_question(question):
                notes.append(f"用户对「{keywords}」感兴趣。可推荐「{route_name}」：{spots}。亮点：{highlights}。")
            else:
                notes.append(f"用户偏好「{keywords}」。如自然，可简短提示可继续咨询「{route_name}」。")

        if final_travel_context.get("with_children"):
            notes.append("同行有孩子，优先互动性强、动线轻松的景点。")
        if final_travel_context.get("with_elderly"):
            notes.append("同行有老人，优先平缓易行、休息方便的安排。")
        if final_travel_context.get("with_partner"):
            notes.append("用户是双人同行，优先风景体验、拍照打卡和节奏舒适的路线。")
        if final_travel_context.get("time_constraint") == "half_day":
            notes.append("用户只有半天，建议控制在3-4个核心点。")
        elif final_travel_context.get("time_constraint") == "quick":
            notes.append("用户时间紧张，建议控制在2-3个核心点。")
        if final_travel_context.get("weather") == "rainy":
            notes.append("雨天优先室内景点。")
        if final_travel_context.get("weather") == "sunny":
            notes.append("晴晒时提醒防晒补水，室外点避开正午。")
        if final_travel_context.get("energy_level") == "low":
            notes.append("用户体力一般，建议休息点或观光车。")

        emotion = self._detect_emotion(question)
        if emotion.get("has_emotion"):
            session_data["last_emotion"] = emotion if session_data else emotion
            if emotion["emotion"] == "complaint":
                notes.append("用户在投诉或强烈不满，先道歉，再给可执行替代方案。")
            elif emotion["emotion"] == "fatigue":
                notes.append("用户疲惫，先关心状态，再推荐休息点和轻松路线。")
            elif emotion["emotion"] == "dissatisfied":
                notes.append("用户不满，先共情，再调整推荐方向。")

        return "\n".join(f"- {note}" for note in notes)

    def _build_system_prompt(self, has_context: bool, user_notes: str = "") -> str:
        prompt = """
你是灵山胜境景区的 AI 数字导游“小灵”。请用中文回答，像现场导游一样亲切、自然、可靠，不要官腔。

硬性规则：
1. 有【参考资料】时，只能依据参考资料回答事实，不要编造、不要推测。
2. 参考资料没有的信息，不要用常识补齐；请自然说明“我这边资料里暂时没查到这部分”，并引导用户换个更具体的问法。
3. 涉及高度、价格、时间、场次、路线时，必须以参考资料里的具体信息为准。
4. 用户问“好玩吗、值不值得”时，先给事实依据，再给建议。
5. 用户没有问路线时，不主动展开完整路线。
6. 不使用 Markdown 标题、加粗符号或编号堆砌；答案分段即可。
7. 不要重复同一句信息，答案不要半截结束。
8. 回答尽量控制在120-220字；如果用户要求详细介绍，再适度展开。
9. 可以用“你可以先看…”“比较适合…”“我建议…”这类平易近人的说法，但事实必须来自参考资料。
"""
        if not has_context:
            prompt += "\n当前没有可用参考资料。除问候、自我介绍等社交问题外，应拒绝编造事实。\n"
        if user_notes:
            prompt += f"\n用户上下文：\n{user_notes}\n"
        return prompt.strip()

    def _build_general_prompt(self) -> str:
        return """
你是灵山胜境景区的 AI 数字导游“小灵”。用户当前是在普通沟通，不需要查询知识库。

请自然、友好、简洁地回应：
1. 可以寒暄、记住用户名字、介绍你能提供的景区服务。
2. 不要编造景区事实、价格、时间、路线、历史等知识库内容。
3. 如果用户问到具体景区事实，请提示他可以直接问景点、门票、开放时间、演出或路线问题。
4. 不使用 Markdown 标题、加粗符号或编号堆砌。
""".strip()

    def chat_general(self, question: str, session_id: str = None, history: list = None) -> dict:
        """普通沟通入口，不走 RAG，也不触发知识库核验。"""
        if not self.is_ready():
            return {"success": False, "answer": "", "error": "LLM not ready"}

        if session_id:
            session_data = self.get_or_create_session(session_id)
            history = session_data.get("history", [])
        else:
            session_data = None
            history = history or []

        if self._is_social_question(question):
            answer = self._generate_social_response(question, history)
            if session_data:
                self._append_history(session_data, question, answer)
            return {"success": True, "answer": answer, "error": None}

        messages = [{"role": "system", "content": self._build_general_prompt()}]
        if history:
            messages.extend(history[-6:])
        messages.append({"role": "user", "content": question})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=260
            )
            answer = self._clean_answer(response.choices[0].message.content or "")
            if not answer:
                answer = "我在的，可以继续问我灵山胜境的景点、路线、开放时间或门票信息。"
            if session_data:
                self._append_history(session_data, question, answer)
            return {"success": True, "answer": answer, "error": None}
        except Exception as e:
            print(f"❌ 普通对话调用失败: {e}")
            return {"success": False, "answer": "", "error": str(e)}

    def chat(self, question: str, context: str = "", session_id: str = None, history: list = None, remember: bool = True) -> dict:
        if not self.is_ready():
            return {"success": False, "answer": "", "error": "LLM not ready"}

        if session_id:
            session_data = self.get_or_create_session(session_id)
            history = session_data.get("history", [])
        else:
            session_data = None
            history = history or []

        original_question = question

        if self._is_social_question(question):
            answer = self._generate_social_response(question, history)
            if session_data:
                self._append_history(session_data, original_question, answer)
            return {"success": True, "answer": answer, "error": None}

        user_notes = self._build_user_notes(question, session_data) if session_data else self._build_user_notes(question, {})
        if context and session_data:
            session_data["last_context"] = context

        messages = [{"role": "system", "content": self._build_system_prompt(bool(context), user_notes)}]
        if history:
            messages.extend(history[-6:])

        if context:
            user_message = f"【参考资料】\n{context}\n\n【用户问题】\n{question}"
        else:
            user_message = f"【用户问题】\n{question}"
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.15,
                max_tokens=420
            )
            answer = self._clean_answer(response.choices[0].message.content or "")
            if not answer:
                answer = "我这边刚刚没组织好答案，你可以换个问法再问我一次。"

            if remember and session_data:
                self._append_history(session_data, original_question, answer)

            return {"success": True, "answer": answer, "error": None}
        except Exception as e:
            print(f"❌ API调用失败: {e}")
            return {"success": False, "answer": "", "error": str(e)}

    def should_verify_answer(self, question: str, context: str, answer: str, sources: list = None) -> tuple:
        """本地判断是否需要二次 LLM 核验，尽量把常规问题控制在一次调用内。"""
        if not context:
            return False, "无参考资料，已由路由拒答"

        answer = answer or ""
        sources = sources or []
        top_score = sources[0].get("similarity", 0) if sources else 0

        if ("暂无相关信息" in answer or "暂时没查到" in answer) and self._context_relevant_to_question(question, context):
            return True, "答案拒答但参考资料相关"

        is_advice_question = self._is_advice_question(question)
        is_strict_fact_question = self._is_strict_fact_question(question)

        if is_advice_question and not is_strict_fact_question:
            unsupported_numbers = self._unsupported_numeric_facts(answer, context)
            if unsupported_numbers:
                return True, f"路线建议含参考资料外数字: {unsupported_numbers[:3]}"
            if top_score and top_score < 3.5:
                return True, f"游玩建议检索置信度偏低({top_score:.2f})"
            return False, "游玩建议已有参考资料，允许直接生成"

        if is_strict_fact_question:
            unsupported_numbers = self._unsupported_numeric_facts(answer, context)
            if unsupported_numbers:
                return True, f"答案含参考资料外数字: {unsupported_numbers[:3]}"
            if top_score and top_score < 7.0:
                return True, f"高风险问题检索置信度不足({top_score:.2f})"
            return False, "高风险问题已通过本地数字一致性检查"

        if top_score and top_score < 5.0:
            return True, f"检索置信度偏低({top_score:.2f})"

        attraction_name = extract_attraction_name(question)
        if attraction_name and attraction_name not in context:
            return True, "问题景点与参考资料不一致"

        if len(answer) > 650:
            return True, "答案过长，需检查是否发散"

        return False, "高置信常规问题，跳过二次核验"

    def _unsupported_numeric_facts(self, answer: str, context: str) -> list:
        number_pattern = r"\d+(?:\.\d+)?\s*(?:元|米|m|M|吨|年|小时|分钟|场|点|:|：|㎡|公里|岁|周岁)?"
        answer_numbers = {item.strip() for item in re.findall(number_pattern, answer or "") if item.strip()}
        context_text = context or ""
        unsupported = []
        for item in answer_numbers:
            compact = re.sub(r"\s+", "", item)
            if item not in context_text and compact not in re.sub(r"\s+", "", context_text):
                unsupported.append(item)
        return unsupported

    def _extract_json_object(self, text: str) -> dict:
        text = (text or "").strip()
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except Exception:
            return {}

    def _build_verifier_prompt(self) -> str:
        return """
你是灵山胜境问答系统的事实核验员。你的任务是检查候选回答是否严格依据【参考资料】、是否回答了【用户问题】。

核验规则：
1. 只允许使用【参考资料】中的事实，不能补充常识、猜测或外部信息。
2. 如果候选回答包含参考资料没有的高度、价格、时间、路线、特色、评价等事实，必须修正。
3. 如果候选回答跑题或没有回答用户问题，必须基于参考资料重写。
4. 如果【参考资料】里有用户所问景点的内容，即使候选回答不好，也必须提取资料重写，不能回答“暂无相关信息”或“没查到”。
5. 只有【参考资料】完全没有相关内容时，answer 才能自然说明：“我这边资料里暂时没查到这部分。你可以问我具体景点、门票、开放时间、演出或路线，我再帮你查。”
6. 用户问“介绍”“是什么”“有什么特色/看点”时，优先概括位置、核心功能、文化内涵、游玩亮点。
7. 输出必须是 JSON，不要 Markdown，不要解释 JSON 外的内容。

JSON 格式：
{
  "verdict": "pass 或 revise 或 reject",
  "answer": "最终可返回给用户的中文答案",
  "reason": "一句话说明核验原因"
}
""".strip()

    def verify_answer(self, question: str, context: str, answer: str) -> dict:
        """用第二次 LLM 调用核验并必要时修正答案。"""
        if not self.is_ready():
            return {"success": False, "answer": answer, "verdict": "skip", "reason": "LLM not ready"}

        if not context:
            return {
                "success": True,
                "answer": "我这边资料里暂时没查到这部分。你可以问我具体景点、门票、开放时间、演出或路线，我再帮你查。",
                "verdict": "reject",
                "reason": "无参考资料"
            }

        user_message = (
            f"【参考资料】\n{context}\n\n"
            f"【用户问题】\n{question}\n\n"
            f"【候选回答】\n{answer}"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.verifier_model,
                messages=[
                    {"role": "system", "content": self._build_verifier_prompt()},
                    {"role": "user", "content": user_message}
                ],
                temperature=0,
                max_tokens=520
            )
            raw = response.choices[0].message.content or ""
            data = self._extract_json_object(raw)
            verdict = data.get("verdict", "revise")
            final_answer = self._clean_answer(data.get("answer", "") or answer)
            reason = data.get("reason", "")

            if verdict not in {"pass", "revise", "reject"}:
                verdict = "revise"
            if verdict == "reject" and self._context_relevant_to_question(question, context):
                verdict = "revise"
                reason = reason or "参考资料包含相关内容，拒答已改为修正"
                if "暂无相关信息" in final_answer or "暂时没查到" in final_answer:
                    final_answer = self._fallback_answer_from_context(question, context) or answer
            if not final_answer:
                final_answer = "我这边资料里暂时没查到这部分。你可以问我具体景点、门票、开放时间、演出或路线，我再帮你查。" if verdict == "reject" else answer

            return {
                "success": True,
                "answer": final_answer,
                "verdict": verdict,
                "reason": reason
            }
        except Exception as e:
            print(f"❌ 答案核验失败: {e}")
            return {"success": False, "answer": answer, "verdict": "error", "reason": str(e)}

    def _context_relevant_to_question(self, question: str, context: str) -> bool:
        if not question or not context:
            return False
        attraction_name = extract_attraction_name(question)
        if attraction_name and attraction_name in context:
            return True
        key_terms = [
            "门票", "票价", "开放", "时间", "路线", "怎么去", "怎么玩", "雨天",
            "亲子", "老人", "介绍", "特色", "看点", "历史", "文化", "多高"
        ]
        return any(term in question and term in context for term in key_terms)

    def _fallback_answer_from_context(self, question: str, context: str) -> str:
        """当核验模型误拒答时，从参考资料中抽取一个保守答案。"""
        blocks = re.split(r"【参考\d+】", context or "")
        attraction_name = extract_attraction_name(question)
        answers = []

        for block in blocks:
            if "答案：" not in block:
                continue
            if attraction_name and attraction_name not in block:
                continue
            answer = block.split("答案：", 1)[1].strip()
            answer = re.sub(r"\n{2,}", "\n", answer)
            if answer:
                answers.append(answer)

        if not answers:
            for block in blocks:
                if "答案：" in block:
                    answer = block.split("答案：", 1)[1].strip()
                    if answer:
                        answers.append(answer)
                        break

        if not answers:
            return ""

        combined = "\n".join(answers[:2])
        if len(combined) > 520:
            cut = combined[:520]
            punct = max(cut.rfind("。"), cut.rfind("；"), cut.rfind("，"))
            combined = cut[:punct + 1] if punct > 260 else cut.rstrip() + "..."
        return self._clean_answer(combined)

    def _clean_answer(self, answer: str) -> str:
        answer = re.sub(r"\*\*([^*]+)\*\*", r"\1", answer)
        answer = re.sub(r"(^|\s)\*\s+", r"\1· ", answer, flags=re.MULTILINE)
        answer = re.sub(r"#+\s*", "", answer)
        answer = re.sub(r"\n{3,}", "\n\n", answer)

        lines = []
        seen = set()
        for line in answer.splitlines():
            clean = line.strip()
            if not clean:
                if lines and lines[-1] != "":
                    lines.append("")
                continue
            if clean in seen:
                continue
            seen.add(clean)
            lines.append(clean)

        return "\n".join(lines).strip()

    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]


_llm_service = None


def get_llm_service():
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
