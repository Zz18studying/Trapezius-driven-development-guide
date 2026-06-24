# -*- coding: utf-8 -*-
"""
话题聚类服务 - LLM 聚类 + 关键词匹配降级
"""

import json
import os
from datetime import datetime, timedelta
from openai import OpenAI
from models.database import SessionLocal, Conversation, HotTopicCache

# ==================== DeepSeek API 客户端 ====================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    print("⚠️ 警告: DEEPSEEK_API_KEY 未设置，将直接使用关键词匹配")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)


# ==================== LLM 聚类函数 ====================
async def classify_with_llm(questions: list) -> list:
    """
    调用 DeepSeek API 进行话题聚类，返回 TOP 10
    """
    if not questions:
        return []

    if not DEEPSEEK_API_KEY:
        print("[话题聚类] API Key 未设置，跳过 LLM")
        return []

    predefined_categories = [
        "开放时间", "门票价格", "交通路线", "景点介绍",
        "祈福体验", "游览建议", "历史故事", "餐饮住宿"
    ]

    # 取前 200 个问题，避免提示词过长
    sample = questions[:200]

    prompt = f"""
你是一个数据分析专家，请对以下游客提问进行话题归类。

【固定话题类别】
{json.dumps(predefined_categories, ensure_ascii=False)}

【用户问题列表】
{json.dumps(sample, ensure_ascii=False)}

【要求】
1. 将每个问题归类到上述话题之一。如果无法匹配，归入"其他"。
2. 统计每个话题被提及的次数。
3. 返回 TOP 10 个话题（按提及次数降序）。
4. 输出格式为 JSON 数组，每个元素包含 topic, count。

【输出格式】（只输出 JSON，不要有任何额外文字）：
[
  {{"topic": "开放时间", "count": 15}},
  {{"topic": "门票价格", "count": 12}}
]
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",  # 使用已验证可用的模型
            messages=[
                {"role": "system", "content": "你是一个数据分析专家，只输出JSON，不要有任何额外文字。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1024
        )
        content = response.choices[0].message.content
        print(f"[话题聚类] LLM 原始返回:\n{content[:500]}...")

        # 清理 markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        content = content.strip()

        topics = json.loads(content)
        # 过滤有效话题
        valid_topics = [t for t in topics if t['topic'] in predefined_categories or t['topic'] == "其他"]
        return valid_topics[:10]
    except Exception as e:
        print(f"[话题聚类] LLM 调用失败: {e}")
        return None  # 返回 None 表示需要降级


# ==================== 关键词匹配降级方案 ====================
async def simple_group(questions: list) -> list:
    """
    精细降级方案：多关键词权重匹配
    """
    topic_keywords = {
        "开放时间": {
            "keywords": ["开放时间", "几点开", "几点关", "营业时间", "开门", "关门", "什么时候开", "什么时候关"],
            "weight": 1
        },
        "门票价格": {
            "keywords": ["门票", "票价", "多少钱", "价格", "收费", "免费", "优惠", "学生票", "老人票", "联票"],
            "weight": 1
        },
        "交通路线": {
            "keywords": ["怎么去", "交通", "公交", "地铁", "自驾", "停车", "路线", "导航", "打车", "班车"],
            "weight": 1
        },
        "景点介绍": {
            "keywords": ["景点", "特色", "看点", "介绍", "游览", "参观", "必看", "景区"],
            "weight": 1
        },
        "祈福体验": {
            "keywords": ["祈福", "许愿", "拜佛", "烧香", "抱佛脚", "摸佛手", "转经筒", "圣水", "菩萨", "保佑", "求", "拜"],
            "weight": 1
        },
        "游览建议": {
            "keywords": ["怎么玩", "路线", "攻略", "建议", "安排", "行程", "多久", "时间", "顺序", "最佳", "怎么安排"],
            "weight": 1
        },
        "历史故事": {
            "keywords": ["历史", "故事", "由来", "传说", "典故", "文化", "渊源", "千年", "古代", "名人"],
            "weight": 1
        },
        "餐饮住宿": {
            "keywords": ["吃", "住", "餐厅", "酒店", "素斋", "素食", "住宿", "餐饮", "美食", "旅馆", "好吃的", "吃饭", "住宿推荐"],
            "weight": 2
        }
    }

    topic_scores = {topic: 0 for topic in topic_keywords}

    for q in questions:
        q_lower = q.lower()
        for topic, info in topic_keywords.items():
            score = 0
            for kw in info["keywords"]:
                if kw in q_lower:
                    score += info["weight"]
            if score > 0:
                topic_scores[topic] += score

    if sum(topic_scores.values()) == 0:
        return [{"topic": "其他", "count": len(questions), "keywords": []}]

    sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)[:10]
    result = [{"topic": t[0], "count": t[1], "keywords": []} for t in sorted_topics if t[1] > 0]
    return result


# ==================== 更新缓存（定时任务调用） ====================
async def update_hot_topics_cache():
    """
    从 conversations 表获取最近30天的问题，尝试 LLM 聚类，失败则降级为关键词匹配
    """
    db = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(days=30)
        results = db.query(Conversation.user_question).filter(
            Conversation.created_at >= cutoff
        ).all()
        questions = [r[0] for r in results if r[0]]
        print(f"[话题缓存] 获取到 {len(questions)} 个问题")
    finally:
        db.close()

    if not questions:
        print("[话题缓存] 没有新问题，清空缓存")
        db = SessionLocal()
        try:
            db.query(HotTopicCache).delete()
            db.commit()
        finally:
            db.close()
        return

    # 1. 尝试 LLM 聚类（取前 200 个问题）
    topics = await classify_with_llm(questions[:200])

    # 2. 如果 LLM 失败，使用降级方案
    if not topics:
        print("[话题缓存] LLM 聚类失败，使用关键词匹配降级方案")
        topics = await simple_group(questions)

    if not topics:
        print("[话题缓存] 无任何结果")
        return

    # 3. 写入缓存表（全量替换）
    db = SessionLocal()
    try:
        db.query(HotTopicCache).delete()
        for item in topics:
            cache = HotTopicCache(
                topic=item["topic"],
                count=item["count"],
                keywords=json.dumps(item.get("keywords", []), ensure_ascii=False)
            )
            db.add(cache)
        db.commit()
        print(f"[话题缓存] 已更新 {len(topics)} 条话题")
    except Exception as e:
        print(f"[话题缓存] 更新失败: {e}")
        db.rollback()
    finally:
        db.close()


# ==================== 读取缓存（供 API 调用） ====================
async def get_cached_topics(limit: int = 10) -> list:
    """
    从缓存表读取话题（供前端 API 调用）
    """
    db = SessionLocal()
    try:
        results = db.query(HotTopicCache).order_by(HotTopicCache.count.desc()).limit(limit).all()
        return [{"topic": r.topic, "count": r.count} for r in results]
    finally:
        db.close()