# -*- coding: utf-8 -*-
"""
知识库共享常量。
"""

ATTRACTION_NAMES = [
    "灵山大佛", "九龙灌浴", "灵山梵宫", "五印坛城", "祥符禅寺",
    "拈花广场", "梵天花海", "香月花街", "五灯湖", "灵山大照壁",
    "阿育王柱", "百子戏弥勒", "曼飞龙塔", "无尽意斋", "鹿鸣谷",
    "灵山精舍", "菩提大道", "五明桥", "佛足坛", "五智门",
    "降魔浮雕", "佛教文化博览馆", "拈花堂"
]


def extract_attraction_name(text: str) -> str:
    """从文本中提取已知景点名称。"""
    if not text:
        return ""
    for name in sorted(ATTRACTION_NAMES, key=len, reverse=True):
        if name in text:
            return name
    return ""
