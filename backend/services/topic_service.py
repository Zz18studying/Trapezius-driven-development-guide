# -*- coding: utf-8 -*-
"""
话题聚类服务 - 使用 LLM 对用户问题归类
"""

import json
import re
from datetime import datetime, timedelta  # ← 关键修复
from services.llm_service import get_llm_service
from services.db_service import get_db_session
from models.database import Conversation


async def get_hot_topics(limit: int = 5) -> list:
    """
    获取热门话题 TOP N
    从数据库获取最近30天的用户问题，用 LLM 进行聚类
    """
    # 1. 从数据库获取最近30天的问题
    db = get_db_session()
    try:
        results = db.query(Conversation.user_question).filter(
            Conversation.created_at >= datetime.now() - timedelta(days=30)
        ).all()
        questions = [r[0] for r in results if r[0]]
        print(f"[话题聚类] 获取到 {len(questions)} 个问题")
    finally:
        db.close()
    
    if not questions:
        return []
    
    # 2. 如果问题数量较少，直接返回
    if len(questions) < 5:
        return await simple_group(questions)
    
    # 3. 用 LLM 进行聚类
    topics = await classify_with_llm(questions[:100])  # 最多取100个问题
    return topics[:limit]


async def classify_with_llm(questions: list) -> list:
    """
    使用 LLM 对问题进行聚类分析
    """
    llm = get_llm_service()
    
    prompt = f"""
你是一个数据分析专家，请对以下游客提问进行话题归类。

用户问题列表：
{json.dumps(questions, ensure_ascii=False)[:3000]}

【要求】
1. 将相似的问题归为同一话题（如"景区几点开门"和"开放时间"归为"开放时间"）
2. 每个话题用3-6个字概括
3. 统计每个话题被提及的次数
4. 返回 TOP 5 个话题

【输出格式】（只输出JSON，不要其他内容）：
[
  {{"topic": "开放时间", "keywords": ["几点开门", "开放时间", "营业时间"], "count": 15}},
  {{"topic": "门票价格", "keywords": ["门票", "票价", "多少钱"], "count": 12}}
]
"""
    
    try:
        result = llm.chat(prompt, "")
        if result['success']:
            content = result['answer']
            # 清理 markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            topics = json.loads(content.strip())
            return topics
    except Exception as e:
        print(f"[话题聚类] LLM 调用失败: {e}")
    
    # 降级：简单分组
    return await simple_group(questions)


async def simple_group(questions: list) -> list:
    """
    降级方案：简单的关键词匹配
    """
    topic_map = {
        "开放时间": ["开放时间", "几点开门", "什么时候开", "营业时间", "关门"],
        "门票价格": ["门票", "票价", "多少钱", "价格", "收费"],
        "交通路线": ["怎么去", "公交", "自驾", "停车", "路线"],
        "景点介绍": ["有什么", "景点", "特色", "看点", "介绍"],
        "祈福体验": ["祈福", "抱佛脚", "许愿", "烧香", "拜佛"],
        "游览建议": ["怎么玩", "推荐", "路线", "攻略"],
        "历史故事": ["历史", "故事", "由来", "传说", "典故"],
        "餐饮住宿": ["吃", "住", "餐厅", "酒店", "素斋"],
    }
    
    topic_counts = {}
    for q in questions:
        matched = False
        for topic, keywords in topic_map.items():
            if any(kw in q for kw in keywords):
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
                matched = True
                break
        if not matched:
            topic_counts["其他"] = topic_counts.get("其他", 0) + 1
    
    sorted_topics = sorted(
        topic_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    return [
        {"topic": t[0], "count": t[1], "keywords": []}
        for t in sorted_topics
    ]