# -*- coding: utf-8 -*-
"""
情感分析服务 - 游客感受度分析核心模块
"""

import re
import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy import func
from models.database import SessionLocal, Conversation


def analyze_sentiment_static(text: str) -> str:
    if not text:
        return "neutral"
    negative_keywords = [
        "不好", "差", "失望", "不满意", "坑", "太差", "垃圾",
        "没意思", "无聊", "浪费时间", "后悔", "不值", "骗人",
        "糟糕", "烂", "不行", "一般", "普通", "凑合",
        "不如", "没有", "不会", "不能", "不让", "不开放",
        "遗憾", "可惜", "太贵", "贵", "人太多", "排队", "挤"
    ]
    positive_keywords = [
        "好", "棒", "满意", "喜欢", "值得", "推荐", "好玩",
        "开心", "震撼", "壮观", "美丽", "漂亮", "很赞",
        "精彩", "完美", "优秀", "不错", "挺好", "可以",
        "方便", "贴心", "热情", "周到", "值得一去",
        "流连忘返", "不虚此行", "大开眼界"
    ]
    text_lower = text.lower()
    neg_score = sum(1 for kw in negative_keywords if kw in text_lower)
    pos_score = sum(1 for kw in positive_keywords if kw in text_lower)
    if neg_score > 0 and pos_score == 0:
        return "negative"
    elif pos_score > neg_score:
        return "positive"
    elif neg_score > pos_score:
        return "negative"
    else:
        return "neutral"


def analyze_sentiment_llm(text: str) -> str:
    if not text:
        return "neutral"

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("[情感分析] 未找到 DEEPSEEK_API_KEY，降级到静态")
        return analyze_sentiment_static(text)

    url = "https://api.deepseek.com/v1/chat/completions"
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个情感分析助手。请分析用户对景区的评价，只输出一个词：positive（正面）、neutral（中性）或 negative（负面）。"},
            {"role": "user", "content": text}
        ],
        "temperature": 0.1,
        "max_tokens": 10
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }
    json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            sentiment = result['choices'][0]['message']['content'].strip().lower()
            if sentiment in ["positive", "neutral", "negative"]:
                return sentiment
    except Exception as e:
        print(f"[情感分析] LLM 调用异常: {e}")
        # 降级到静态
        return analyze_sentiment_static(text)


def analyze_sentiment(text: str, use_llm: bool = True) -> str:
    if use_llm:
        return analyze_sentiment_llm(text)
    return analyze_sentiment_static(text)


def get_sentiment_overview(days: int = 7) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(days=days)
        total = db.query(Conversation).filter(Conversation.created_at >= cutoff).count()
        sentiment_counts = {}
        for s in ["positive", "neutral", "negative"]:
            cnt = db.query(Conversation).filter(
                Conversation.created_at >= cutoff,
                Conversation.sentiment == s
            ).count()
            sentiment_counts[s] = cnt
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_total = db.query(Conversation).filter(Conversation.created_at >= today_start).count()
        today_sentiment = {}
        for s in ["positive", "neutral", "negative"]:
            cnt = db.query(Conversation).filter(
                Conversation.created_at >= today_start,
                Conversation.sentiment == s
            ).count()
            today_sentiment[s] = cnt
        avg_response = db.query(func.avg(Conversation.response_time)).filter(
            Conversation.created_at >= cutoff
        ).scalar() or 0.0
        positive_rate = round(sentiment_counts["positive"] / max(total, 1) * 100, 2)
        negative_rate = round(sentiment_counts["negative"] / max(total, 1) * 100, 2)
        neutral_rate = round(sentiment_counts["neutral"] / max(total, 1) * 100, 2)
        return {
            "total_conversations": total,
            "today_conversations": today_total,
            "sentiment_distribution": sentiment_counts,
            "today_sentiment": today_sentiment,
            "avg_response_time": round(avg_response, 2),
            "positive_rate": positive_rate,
            "negative_rate": negative_rate,
            "neutral_rate": neutral_rate
        }
    finally:
        db.close()


def get_sentiment_trend(days: int = 7) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        trend = []
        for i in range(days - 1, -1, -1):
            date = datetime.now() - timedelta(days=i)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            positive = db.query(Conversation).filter(
                Conversation.created_at >= date_start,
                Conversation.created_at <= date_end,
                Conversation.sentiment == "positive"
            ).count()
            neutral = db.query(Conversation).filter(
                Conversation.created_at >= date_start,
                Conversation.created_at <= date_end,
                Conversation.sentiment == "neutral"
            ).count()
            negative = db.query(Conversation).filter(
                Conversation.created_at >= date_start,
                Conversation.created_at <= date_end,
                Conversation.sentiment == "negative"
            ).count()
            trend.append({
                "date": date.strftime("%Y-%m-%d"),
                "positive": positive,
                "neutral": neutral,
                "negative": negative
            })
        return trend
    finally:
        db.close()


def get_session_sentiment_trajectory(session_id: str) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        convs = db.query(Conversation).filter(
            Conversation.session_id == session_id,
            Conversation.sentiment.isnot(None)
        ).order_by(Conversation.created_at).all()
        if len(convs) < 2:
            return {
                "session_id": session_id,
                "total_turns": len(convs),
                "start_sentiment": convs[0].sentiment if convs else None,
                "end_sentiment": convs[-1].sentiment if convs else None,
                "direction": "insufficient_data",
                "trajectory": [c.sentiment for c in convs]
            }
        start = convs[0].sentiment
        end = convs[-1].sentiment
        score_map = {"positive": 1, "neutral": 0, "negative": -1}
        start_score = score_map.get(start, 0)
        end_score = score_map.get(end, 0)
        if end_score > start_score:
            direction = "improving"
        elif end_score < start_score:
            direction = "declining"
        else:
            direction = "stable"
        return {
            "session_id": session_id,
            "total_turns": len(convs),
            "start_sentiment": start,
            "end_sentiment": end,
            "direction": direction,
            "trajectory": [c.sentiment for c in convs]
        }
    finally:
        db.close()


def get_high_risk_sessions(days: int = 7, threshold: int = 2) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(days=days)
        sessions = db.query(Conversation.session_id).filter(
            Conversation.created_at >= cutoff,
            Conversation.session_id.isnot(None),
            Conversation.session_id != "unknown"
        ).distinct().all()
        high_risk = []
        for (session_id,) in sessions:
            traj = get_session_sentiment_trajectory(session_id)
            if traj["direction"] == "declining":
                neg_count = traj["trajectory"].count("negative") if traj["trajectory"] else 0
                if neg_count >= threshold:
                    high_risk.append({
                        "session_id": session_id,
                        "total_turns": traj["total_turns"],
                        "negative_count": neg_count,
                        "start_sentiment": traj["start_sentiment"],
                        "end_sentiment": traj["end_sentiment"],
                        "trajectory": traj["trajectory"]
                    })
        high_risk.sort(key=lambda x: x["negative_count"], reverse=True)
        return high_risk
    finally:
        db.close()


def get_session_history(session_id: str) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        convs = db.query(Conversation).filter(
            Conversation.session_id == session_id
        ).order_by(Conversation.created_at).all()
        return [
            {
                "turn": idx + 1,
                "question": c.user_question,
                "answer": c.ai_answer,
                "sentiment": c.sentiment,
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else None
            }
            for idx, c in enumerate(convs)
        ]
    finally:
        db.close()


def generate_suggestions(overview: Dict[str, Any], trend: List[Dict]) -> List[Dict[str, Any]]:
    suggestions = []
    negative_rate = overview.get("negative_rate", 0)
    positive_rate = overview.get("positive_rate", 0)
    total = overview.get("total_conversations", 0)
    avg_response = overview.get("avg_response_time", 0)

    if total > 0:
        if negative_rate > 30:
            suggestions.append({
                "level": "high",
                "title": "🚨 满意度偏低，需优先改善",
                "description": f"近7天负面反馈占比 {negative_rate}%，游客不满意情绪显著。",
                "action": "检查知识库完整性，补充常见问题，优化回答质量"
            })
        elif negative_rate > 15:
            suggestions.append({
                "level": "medium",
                "title": "⚠️ 存在部分负面反馈",
                "description": f"近7天负面反馈占比 {negative_rate}%，建议关注高频负面问题。",
                "action": "分析负面高频问题，针对性优化知识库"
            })
        else:
            suggestions.append({
                "level": "low",
                "title": "✅ 满意度良好",
                "description": f"近7天正面反馈占比 {positive_rate}%，负面反馈仅 {negative_rate}%。",
                "action": "继续保持，可适当增加主动推荐"
            })

    if total < 10:
        suggestions.append({
            "level": "low",
            "title": "📊 数据量较少",
            "description": f"近7天仅有 {total} 条对话，统计结果可能不够代表性。",
            "action": "增加测试数据或推广数字人使用"
        })

    if avg_response > 3.0:
        suggestions.append({
            "level": "medium",
            "title": "⚡ 响应时间较慢",
            "description": f"平均响应时间 {avg_response} 秒，可能影响用户体验。",
            "action": "检查后端性能，优化数据库查询和LLM调用"
        })
    elif avg_response > 1.5:
        suggestions.append({
            "level": "info",
            "title": "⚡ 响应速度可优化",
            "description": f"平均响应时间 {avg_response} 秒，尚有优化空间。",
            "action": "考虑增加缓存或使用更轻量模型"
        })

    return suggestions


def generate_advanced_report(days: int = 7) -> Dict[str, Any]:
    overview = get_sentiment_overview(days)
    trend = get_sentiment_trend(days)
    high_risk = get_high_risk_sessions(days, threshold=2)

    table_desc = f"""
【数据库表说明】
- 表名：conversations（对话记录）
- 字段说明：
  * session_id: 用户会话ID（同一用户在一次访问中的连续对话）
  * sentiment: 情感标签（positive/neutral/negative），由AI自动标注
  * user_question: 用户提问的原始文本
  * created_at: 对话时间（精确到秒）

【近{days}天数据摘要】
- 总对话数：{overview['total_conversations']}
- 正面占比：{overview['positive_rate']}%
- 中性占比：{overview['neutral_rate']}%
- 负面占比：{overview['negative_rate']}%
- 平均响应时间：{overview['avg_response_time']}秒

【每日情感趋势（最近7天）】
{json.dumps(trend, ensure_ascii=False, indent=2)}

【高风险会话（情绪持续下降）】
{json.dumps(high_risk, ensure_ascii=False, indent=2) if high_risk else '暂无'}
"""

    prompt = f"""
你是一位资深的景区运营管理专家。请基于以下数据，生成一份面向管理层的《游客感受度分析报告》。

{table_desc}

请按以下结构输出报告（纯文本，分四个段落，不要用Markdown）：
1. 满意度总体评价（给出明确的结论，比如“满意/一般/不满意”）
2. 情绪变化趋势分析（指出近期趋势是好转还是恶化，并分析可能原因）
3. 重点问题与风险预警（若存在高风险会话，指出用户主要的不满点）
4. 具体改进建议（至少3条，要具体可操作）

报告要专业、简洁、有洞察力。
"""

    report_text = ""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        report_text = "（未配置 DEEPSEEK_API_KEY，无法生成报告）"
    else:
        url = "https://api.deepseek.com/v1/chat/completions"
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一个景区管理专家，请根据数据生成专业报告。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8"
        }
        json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                report_text = result['choices'][0]['message']['content']
        except Exception as e:
            print(f"[高级报告] LLM调用异常: {e}")
            report_text = "（报告生成服务暂时不可用）"

    return {
        "raw_data": {
            "overview": overview,
            "trend": trend,
            "high_risk_sessions": high_risk
        },
        "report_text": report_text
    }