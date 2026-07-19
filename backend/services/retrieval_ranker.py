# -*- coding: utf-8 -*-
"""
检索重排工具。
"""

import re
from services.knowledge_constants import extract_attraction_name


INTENT_KEYWORDS = {
    "time": ["开放时间", "几点", "营业时间", "开门", "关门", "时间", "表演", "演出", "场次", "开始"],
    "price": ["门票", "票价", "价格", "多少钱", "收费", "优惠", "免费", "半价"],
    "route": [
        "怎么去", "怎么走", "路线", "交通", "停车", "公交", "自驾", "安排",
        "怎么玩", "怎么逛", "怎么游", "推荐", "建议", "适合", "攻略",
        "行程", "游览", "游玩", "先去哪里", "双人", "双人游", "两个人",
        "一个人", "情侣", "约会", "朋友", "同学", "闺蜜", "家庭", "第一次"
    ],
    "feature": ["特色", "看点", "亮点", "好玩", "值得", "介绍", "是什么"],
    "size": ["多高", "高度", "多大", "尺寸", "面积", "规模", "重量"],
    "culture": ["历史", "文化", "寓意", "意义", "典故", "佛教", "禅"],
    "service": ["轮椅", "婴儿车", "寄存", "洗手间", "厕所", "母婴", "WiFi"],
    "style": ["风格", "建筑风格", "藏式", "汉传", "南传", "藏传"],
    "parent": ["孩子", "儿童", "亲子", "带娃", "小孩"],
    "rain": ["雨天", "下雨", "室内", "馆内", "展厅", "避雨"],
    "elder": ["老人", "长辈", "体力", "观光车", "少走路"],
    "quick": ["半天", "快速", "一小时", "两小时", "轻松游"],
}

INTENT_CATEGORY = {
    "time": "开放时间",
    "price": "票务价格",
    "route": "游玩建议",
    "feature": "景点介绍",
    "size": "景点数据",
    "culture": "历史文化",
    "service": "便民服务",
    "style": "景点介绍",
    "parent": "游玩建议",
    "rain": "游玩建议",
    "elder": "游玩建议",
    "quick": "游玩建议",
}


def detect_intents(query: str) -> set:
    intents = set()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in query for keyword in keywords):
            intents.add(intent)
    return intents


def query_terms(query: str) -> set:
    query = re.sub(r"\s+", "", query or "")
    terms = set()
    for size in (2, 3, 4):
        if len(query) < size:
            continue
        terms.update(query[i:i + size] for i in range(len(query) - size + 1))
    terms.update(re.findall(r"[a-zA-Z0-9]+", query))
    return {term for term in terms if term}


def keyword_score(item: dict, query: str) -> float:
    question = item.get("question", "")
    answer = item.get("answer", "")
    category = item.get("category", "")
    attraction_name = item.get("attraction_name", "")
    text = f"{question}\n{answer}\n{category}\n{attraction_name}"

    score = 0.0
    query_name = extract_attraction_name(query)
    if query_name:
        if attraction_name:
            if attraction_name == query_name:
                score += 10.0
            else:
                score -= 12.0
        elif query_name in question:
            score += 7.0
        elif query_name in text:
            score += 1.0
        else:
            score -= 6.0

    if query and query in question:
        score += 4.0
    if question and question in query:
        score += 2.0

    intents = detect_intents(query)
    for intent in intents:
        if category == INTENT_CATEGORY.get(intent):
            score += 2.0
        if any(keyword in text for keyword in INTENT_KEYWORDS[intent]):
            score += 1.2

    scenario_terms = {
        "parent": ["亲子", "孩子", "儿童", "百子戏弥勒", "家庭路线"],
        "rain": ["雨天", "室内", "馆内", "展厅", "闭馆", "梵宫", "博览馆", "无尽意斋"],
        "elder": ["老人", "观光车", "体力有限", "休息", "半价票", "免票"],
        "quick": ["半天", "快速", "轻松游", "路线规划"],
        "style": ["风格", "藏式", "藏传", "汉传", "南传", "建筑"],
    }
    for intent, keywords in scenario_terms.items():
        if intent in intents and any(keyword in text for keyword in keywords):
            score += 2.5

    if "feature" in intents:
        if any(keyword in question for keyword in ["详细介绍", "特色", "看点", "是什么地方", "介绍"]):
            score += 2.4
        if question.endswith("在哪里？") or question.endswith("在哪里?") or "在哪里" in question:
            score -= 2.2

    terms = query_terms(query)
    if terms:
        hit_count = sum(1 for term in terms if term in text)
        score += min(hit_count * 0.18, 4.0)

    if re.search(r"\d+[\.\d]*\s*(米|m|M|元|年|吨|小时|分钟|场|点|:|：)", answer):
        if intents.intersection({"size", "price", "time"}):
            score += 0.8

    if item.get("type") == "faq":
        score += 0.2

    return score


def rerank_candidates(candidates: list, query: str) -> list:
    deduped = {}
    for item in candidates:
        key = item.get("question") or item.get("doc") or item.get("answer")
        if not key:
            continue
        existing = deduped.get(key)
        if existing is None or item.get("vector_similarity", -999) > existing.get("vector_similarity", -999):
            deduped[key] = item

    results = list(deduped.values())
    for item in results:
        vector_similarity = item.get("vector_similarity", item.get("similarity", 0.0))
        vector_bonus = max(0.0, min(float(vector_similarity), 1.0)) * 0.3
        item["keyword_score"] = keyword_score(item, query)
        item["final_score"] = item["keyword_score"] + vector_bonus

    results.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
    return results
