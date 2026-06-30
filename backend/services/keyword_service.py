# -*- coding: utf-8 -*-
"""
关键词提取服务 - 真正的词云
从用户对话中提取高频关键词，按词频统计
"""

import re
import jieba
from collections import Counter
from datetime import datetime, timedelta
from models.database import SessionLocal, Conversation

# 停用词列表（过滤无意义词）
STOPWORDS = {
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
    '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
    '自己', '这', '那', '什么', '怎么', '为什么', '如何', '可以', '吗', '呢', '吧',
    '请问', '我想', '请问一下', '一下', '一点', '一些', '哪个', '哪里', '这边',
    '那里', '然后', '之后', '现在', '今天', '明天', '昨天', '嗯', '啊', '哦',
    '哈哈', '呵呵', '算了', '算了', '就是', '还是', '不是', '比较', '特别',
    '非常', '真的', '感觉', '觉得', '知道', '谢谢', '感谢', '好的', '行', '好',
    '嗯嗯', '哦哦', '哈哈', '嘿嘿', '额', '呃', '哇', '呀', '吧', '啦',
    # ==== 问候语 ====
    '你好', '您好', '嗨', '哈喽', 'hello', 'hi', 'hi你好', '你好呀',
    '早上好', '下午好', '晚上好', '大家好', '大家好呀', 'hello你好',
    '大家好', '你好啊', '您好啊', '嗨你好', '喂', '在吗', '在不在'
    
      '其他', '东西', '地方', '时候', '情况', '事情', '问题',
    '方法', '方式', '了解', '告诉', '推荐', '建议', '介绍', '介绍下',
    '说一下', '问一下', '问下', '咨询', '内容', '方面', '这个', '那个',
    '这些', '那些', '能不能', '有没有', '可不可以', '是不是', '一次',
    '一天', '两个', '三个', '首先', '然后', '最后', '接着', '再', '还',
    '更', '太', '相当', '挺', '蛮', '有点', '还好', '不错', '挺好',
    '挺好的', '很棒', '不错哦', '挺好的啊', '比较', '非常', '特别',
    '感觉', '觉得', '知道', '了解',
}


def extract_keywords_from_text(text: str) -> list:
    """
    从单条文本中提取关键词
    """
    if not text or not isinstance(text, str):
        return []

    text_clean = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
    words = jieba.cut(text_clean)

    keywords = []
    for word in words:
        word = word.strip()
        if len(word) < 2:
            continue
        if word in STOPWORDS:
            continue
        if not re.search(r'[\u4e00-\u9fa5]', word):
            continue
        keywords.append(word)

    return keywords


def get_hot_keywords(days: int = 7, limit: int = 30) -> list:
    """
    从最近 days 天的对话中提取热门关键词
    返回词频统计结果
    """
    db = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(days=days)

        conversations = db.query(Conversation.user_question).filter(
            Conversation.created_at >= cutoff,
            Conversation.user_question.isnot(None)
        ).all()

        if not conversations:
            return []

        all_keywords = []
        for (text,) in conversations:
            keywords = extract_keywords_from_text(text)
            all_keywords.extend(keywords)

        counter = Counter(all_keywords)

        return [
            {"keyword": word, "count": count}
            for word, count in counter.most_common(limit)
        ]
    finally:
        db.close()