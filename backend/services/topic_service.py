# -*- coding: utf-8 -*-
"""
话题聚类服务 - 按关键词匹配统计提及次数
"""

import json
import os
from datetime import datetime, timedelta
from openai import OpenAI
from models.database import SessionLocal, Conversation, HotTopicCache
from sqlalchemy import func, or_

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    print("⚠️ 警告: DEEPSEEK_API_KEY 未设置，将直接使用关键词匹配")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)


def get_last_processed_time():
    try:
        with open("/tmp/last_topic_update.txt", "r") as f:
            return datetime.fromisoformat(f.read().strip())
    except (FileNotFoundError, ValueError):
        return datetime.now() - timedelta(days=30)


def save_last_processed_time(dt):
    with open("/tmp/last_topic_update.txt", "w") as f:
        f.write(dt.isoformat())


async def classify_with_llm(questions: list) -> list:
    if not questions or not DEEPSEEK_API_KEY:
        return []
    predefined_categories = [
        "开放时间", "门票价格", "交通路线", "景点介绍",
        "祈福体验", "游览建议", "历史故事", "餐饮住宿"
    ]
    sample = questions[:200]
    prompt = f"""
你是一个数据分析专家，请对以下游客提问进行话题归类。
【固定话题类别】{json.dumps(predefined_categories, ensure_ascii=False)}
【用户问题列表】{json.dumps(sample, ensure_ascii=False)}
【要求】
1. 将每个问题归类到上述话题之一。如果无法匹配，归入"其他"。
2. 统计每个话题被提及的次数。
3. 返回 TOP 10 个话题（按提及次数降序）。
4. 输出格式为 JSON 数组，每个元素包含 topic, count。
【输出格式】（只输出 JSON）：
[
  {{"topic": "开放时间", "count": 15}},
  {{"topic": "门票价格", "count": 12}}
]
"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个数据分析专家，只输出JSON，不要有任何额外文字。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1024
        )
        content = response.choices[0].message.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        content = content.strip()
        topics = json.loads(content)
        valid_topics = [t for t in topics if t['topic'] in predefined_categories or t['topic'] == "其他"]
        return valid_topics[:10]
    except Exception as e:
        print(f"[话题聚类] LLM 调用失败: {e}")
        return None


async def simple_group(questions: list) -> list:
    topic_keywords = {
        "开放时间": ["开放时间", "几点开", "几点关", "营业时间", "开门", "关门", "什么时候开", "什么时候关"],
        "门票价格": ["门票", "票价", "多少钱", "价格", "收费", "免费", "优惠", "学生票", "老人票", "联票"],
        "交通路线": ["怎么去", "交通", "公交", "地铁", "自驾", "停车", "路线", "导航", "打车", "班车"],
        "景点介绍": ["景点", "特色", "看点", "介绍", "游览", "参观", "必看", "景区"],
        "祈福体验": ["祈福", "许愿", "拜佛", "烧香", "抱佛脚", "摸佛手", "转经筒", "圣水", "菩萨", "保佑", "求", "拜"],
        "游览建议": ["怎么玩", "路线", "攻略", "建议", "安排", "行程", "多久", "时间", "顺序", "最佳", "怎么安排"],
        "历史故事": ["历史", "故事", "由来", "传说", "典故", "文化", "渊源", "千年", "古代", "名人"],
        "餐饮住宿": ["吃", "住", "餐厅", "酒店", "素斋", "素食", "住宿", "餐饮", "美食", "旅馆", "好吃的", "吃饭", "住宿推荐"]
    }
    topic_scores = {topic: 0 for topic in topic_keywords}
    for q in questions:
        q_lower = q.lower()
        for topic, keywords in topic_keywords.items():
            score = 0
            for kw in keywords:
                if kw in q_lower:
                    score += 1
            if score > 0:
                topic_scores[topic] += score
    if sum(topic_scores.values()) == 0:
        return [{"topic": "其他", "count": len(questions)}]
    sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)[:10]
    return [{"topic": t[0], "count": t[1]} for t in sorted_topics if t[1] > 0]


async def update_hot_topics_cache():
    last_time = get_last_processed_time()
    now = datetime.now()
    db = SessionLocal()
    try:
        results = db.query(Conversation.user_question).filter(
            Conversation.created_at > last_time
        ).all()
        questions = [r[0] for r in results if r[0]]
        print(f"[话题缓存] 获取到 {len(questions)} 个新问题")
    finally:
        db.close()
    if not questions:
        await clean_old_data()
        return
    topics = await classify_with_llm(questions[:200])
    if not topics:
        topics = await simple_group(questions)
    if not topics:
        return
    today = now.strftime("%Y-%m-%d")
    db = SessionLocal()
    try:
        for item in topics:
            topic = item["topic"]
            count = item["count"]
            record = db.query(HotTopicCache).filter(
                HotTopicCache.topic == topic,
                HotTopicCache.date == today
            ).first()
            if record:
                record.count += count
            else:
                new_record = HotTopicCache(
                    topic=topic,
                    count=count,
                    date=today,
                    keywords=json.dumps(item.get("keywords", []), ensure_ascii=False)
                )
                db.add(new_record)
        db.commit()
        print(f"[话题缓存] 累加完成")
    except Exception as e:
        print(f"[话题缓存] 累加失败: {e}")
        db.rollback()
    finally:
        db.close()
    await clean_old_data()
    save_last_processed_time(now)


async def clean_old_data():
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    db = SessionLocal()
    try:
        deleted = db.query(HotTopicCache).filter(HotTopicCache.date < cutoff).delete()
        db.commit()
        if deleted:
            print(f"[话题缓存] 清理了 {deleted} 条30天前的记录")
    except Exception as e:
        print(f"[话题缓存] 清理失败: {e}")
        db.rollback()
    finally:
        db.close()


# ============================================================
# 关键改动：统计提及次数（不去重）
# ============================================================
async def get_cached_topics(limit: int = 10) -> list:
    """
    查询热门话题（提及次数统计，按关键词匹配累计）
    返回每个话题的提及次数，总数可能超过会话数，占比需用总提及次数计算。
    """
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    db = SessionLocal()
    try:
        # 直接从 HotTopicCache 查询累加计数（这就是提及次数）
        results = db.query(
            HotTopicCache.topic,
            func.sum(HotTopicCache.count).label("total_count")
        ).filter(HotTopicCache.date >= cutoff).group_by(
            HotTopicCache.topic
        ).order_by(func.sum(HotTopicCache.count).desc()).limit(limit).all()

        # 如果缓存表无数据，则直接从 Conversation 统计（降级）
        if not results:
            print("[话题缓存] 缓存表无数据，直接从对话表统计提及次数")
            topic_keywords = {
                "开放时间": ["开放时间", "几点开", "几点关", "营业时间", "开门", "关门", "什么时候开", "什么时候关"],
                "门票价格": ["门票", "票价", "多少钱", "价格", "收费", "免费", "优惠", "学生票", "老人票", "联票"],
                "交通路线": ["怎么去", "交通", "公交", "地铁", "自驾", "停车", "路线", "导航", "打车", "班车"],
                "景点介绍": ["景点", "特色", "看点", "介绍", "游览", "参观", "必看", "景区"],
                "祈福体验": ["祈福", "许愿", "拜佛", "烧香", "抱佛脚", "摸佛手", "转经筒", "圣水", "菩萨", "保佑", "求", "拜"],
                "游览建议": ["怎么玩", "路线", "攻略", "建议", "安排", "行程", "多久", "时间", "顺序", "最佳", "怎么安排"],
                "历史故事": ["历史", "故事", "由来", "传说", "典故", "文化", "渊源", "千年", "古代", "名人"],
                "餐饮住宿": ["吃", "住", "餐厅", "酒店", "素斋", "素食", "住宿", "餐饮", "美食", "旅馆", "好吃的", "吃饭", "住宿推荐"]
            }
            # 统计每个话题的提及次数（累加匹配到的关键词数）
            result_list = []
            # 获取所有对话问题
            questions = db.query(Conversation.user_question).filter(
                Conversation.created_at >= cutoff,
                Conversation.user_question.isnot(None)
            ).all()
            questions = [q[0] for q in questions]
            if not questions:
                return []
            # 按话题统计提及次数
            topic_mentions = {topic: 0 for topic in topic_keywords}
            for q in questions:
                q_lower = q.lower()
                for topic, keywords in topic_keywords.items():
                    for kw in keywords:
                        if kw in q_lower:
                            topic_mentions[topic] += 1
            # 排序取top
            sorted_topics = sorted(topic_mentions.items(), key=lambda x: x[1], reverse=True)[:limit]
            return [{"topic": t[0], "count": t[1]} for t in sorted_topics if t[1] > 0]
        else:
            return [{"topic": r[0], "count": r[1]} for r in results]
    finally:
        db.close()