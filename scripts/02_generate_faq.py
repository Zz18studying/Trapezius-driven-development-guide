# -*- coding: utf-8 -*-
"""
基于已抽取的 Word 数据生成 FAQ。

不调用大模型，所有答案均来自 data/processed 中的结构化数据和原文知识块。
"""

import json
import os
import re
from collections import defaultdict


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")

INPUT_ATTRACTIONS = os.path.join(DATA_PROCESSED, "attractions_complete.json")
INPUT_KNOWLEDGE_UNITS = os.path.join(DATA_PROCESSED, "knowledge_units.json")
OUTPUT_FAQ = os.path.join(DATA_PROCESSED, "faq_final.json")


def load_json(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_text(text: str, max_len: int = 900) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    punct = max(cut.rfind("。"), cut.rfind("；"), cut.rfind("，"))
    if punct > max_len * 0.65:
        return cut[:punct + 1]
    return cut.rstrip() + "..."


def add_faq(faqs: list, question: str, answer: str, category: str, source: dict):
    question = clean_text(question, 120)
    answer = clean_text(answer, 1000)
    if not question or not answer:
        return
    faqs.append({
        "question": question,
        "answer": answer,
        "category": category or "通用知识",
        "source": source.get("source_file", ""),
        "source_type": source.get("source_type", ""),
        "source_attraction": source.get("source_attraction", ""),
        "attraction_name": source.get("attraction_name", ""),
    })


def is_global_price_unit(unit: dict) -> bool:
    title = unit.get("title", "")
    source_type = unit.get("source_type", "")
    content = unit.get("content", "")
    return source_type == "table" and any(word in title for word in ["票务", "票价", "门票", "价格"]) and "票种" in content


def is_global_time_unit(unit: dict) -> bool:
    title = unit.get("title", "")
    source_type = unit.get("source_type", "")
    if source_type != "table":
        return False
    return any(word in title for word in ["开放时间", "营业时间", "演出时间", "表演时间"])


def is_route_unit(unit: dict) -> bool:
    title = unit.get("title", "")
    content = unit.get("content", "")
    return "路线" in title or "路线规划" in content


def make_source_from_unit(unit: dict) -> dict:
    return {
        "source_file": unit.get("source_file", ""),
        "source_type": unit.get("source_type", ""),
        "source_attraction": unit.get("source_attraction", ""),
        "attraction_name": unit.get("attraction_name", ""),
    }


def field_answer(attraction: dict, fields: list) -> str:
    labels = {
        "location": "位置",
        "specs": "建筑/景观参数",
        "function": "核心功能",
        "culture": "文化内涵",
        "details": "详细介绍",
        "highlights": "游玩亮点",
        "hours": "演艺/开放信息",
        "remarks": "备注",
    }
    parts = []
    for field in fields:
        value = attraction.get(field)
        if value:
            parts.append(f"{labels[field]}：{value}")
    return "\n".join(parts)


def generate_attraction_faq(attractions: list) -> list:
    faqs = []
    for attraction in attractions:
        name = attraction.get("name", "")
        source = {
            "source_file": "；".join(sorted(set(attraction.get("source_files", [])))),
            "source_type": "attraction",
            "source_attraction": attraction.get("id", ""),
            "attraction_name": name,
        }

        overview = field_answer(attraction, ["location", "function", "highlights"])
        introduction = field_answer(attraction, ["location", "specs", "function", "culture", "details", "highlights"])
        add_faq(faqs, f"{name}介绍", introduction, "景点介绍", source)
        add_faq(faqs, f"介绍一下{name}", introduction, "景点介绍", source)
        add_faq(faqs, f"{name}是什么地方？", overview, "景点介绍", source)
        add_faq(faqs, f"{name}有什么特色？", field_answer(attraction, ["function", "culture", "highlights"]), "景点介绍", source)
        add_faq(faqs, f"{name}有什么看点？", field_answer(attraction, ["details", "highlights"]), "景点介绍", source)
        add_faq(faqs, f"{name}在哪里？", attraction.get("location", ""), "景点介绍", source)
        add_faq(faqs, f"{name}有什么参数或规模？", attraction.get("specs", ""), "景点数据", source)
        add_faq(faqs, f"{name}有什么文化内涵？", attraction.get("culture", ""), "历史文化", source)
        add_faq(faqs, f"{name}怎么玩？", attraction.get("highlights", ""), "游玩建议", source)
        add_faq(faqs, f"{name}开放时间是什么？", attraction.get("hours", ""), "开放时间", source)
        add_faq(faqs, f"{name}有什么注意事项？", attraction.get("remarks", ""), "实用贴士", source)

        for alias in attraction.get("aliases", []):
            if alias != name:
                add_faq(faqs, f"{alias}有什么特色？", field_answer(attraction, ["function", "culture", "highlights"]), "景点介绍", source)

        for key, value in attraction.get("supplement", {}).items():
            add_faq(faqs, f"{name}{key}是什么？", value, classify_question(key + value), source)
            add_faq(faqs, f"{name}的{key}", value, classify_question(key + value), source)

        add_numeric_questions(faqs, attraction, source)

    return faqs


def add_numeric_questions(faqs: list, attraction: dict, source: dict):
    name = attraction.get("name", "")
    searchable = "\n".join([
        attraction.get("specs", ""),
        attraction.get("hours", ""),
        attraction.get("remarks", ""),
        "\n".join(attraction.get("supplement", {}).values()),
    ])
    if not searchable:
        return

    if re.search(r"\d+(\.\d+)?\s*(米|m|M)", searchable):
        add_faq(faqs, f"{name}多高或多大？", searchable, "景点数据", source)
    if re.search(r"\d+(\.\d+)?\s*(元|免费)", searchable):
        add_faq(faqs, f"{name}收费吗？", searchable, "票务价格", source)
    if re.search(r"\d{1,2}[:：]\d{2}|\d{1,2}点|\d+场|开放|闭园", searchable):
        add_faq(faqs, f"{name}几点开放或表演？", searchable, "开放时间", source)


def generate_knowledge_faq(units: list) -> list:
    faqs = []
    for unit in units:
        title = unit.get("title", "")
        content = unit.get("content", "")
        category = unit.get("category", "通用知识")
        source = {
            "source_file": unit.get("source_file", ""),
            "source_type": unit.get("source_type", ""),
            "source_attraction": unit.get("source_attraction", ""),
            "attraction_name": unit.get("attraction_name", ""),
        }
        if not content:
            continue

        add_faq(faqs, f"{title}是什么？", content, category, source)
        if category == "历史文化":
            add_faq(faqs, f"介绍一下{title}", content, category, source)
        elif category == "票务价格" and is_global_price_unit(unit):
            add_faq(faqs, "灵山胜境门票多少钱？", content, category, source)
            add_faq(faqs, "门票多少钱？", content, category, source)
            add_faq(faqs, "票价是多少？", content, category, source)
            add_faq(faqs, "灵山胜境有哪些优惠票？", content, category, source)
            add_faq(faqs, "老人和儿童买票有什么优惠？", content, category, source)
            add_faq(faqs, "观光车多少钱？", content, category, source)
        elif category == "开放时间" and is_global_time_unit(unit):
            add_faq(faqs, "灵山胜境开放时间是什么？", content, category, source)
            add_faq(faqs, "景区演出时间是什么？", content, category, source)
        elif category == "交通路线":
            add_faq(faqs, "灵山胜境怎么去？", content, category, source)
        elif category == "游玩建议" and is_route_unit(unit):
            add_faq(faqs, "灵山胜境怎么玩？", content, category, source)
            add_faq(faqs, "灵山胜境推荐路线是什么？", content, category, source)
    faqs.extend(generate_scenario_faq(units))
    return faqs


def first_matching_unit(units: list, title_keywords: list, content_keywords: list = None):
    content_keywords = content_keywords or []
    for unit in units:
        title = unit.get("title", "")
        content = unit.get("content", "")
        if all(keyword in title for keyword in title_keywords):
            return unit
        if content_keywords and all(keyword in content for keyword in content_keywords):
            return unit
    return None


def collect_units(units: list, keywords: list, limit: int = 4) -> list:
    matched = []
    for unit in units:
        text = f"{unit.get('title', '')} {unit.get('content', '')}"
        if any(keyword in text for keyword in keywords):
            matched.append(unit)
        if len(matched) >= limit:
            break
    return matched


def combine_units(units: list, max_len: int = 900) -> str:
    parts = []
    seen = set()
    for unit in units:
        title = unit.get("title", "")
        content = clean_text(unit.get("content", ""), 360)
        if not content or title in seen:
            continue
        seen.add(title)
        parts.append(f"{title}：{content}")
    return clean_text("\n".join(parts), max_len)


def generate_scenario_faq(units: list) -> list:
    faqs = []

    parent_route = first_matching_unit(units, ["亲子", "路线"])
    parent_points = collect_units(units, ["亲子", "孩子", "儿童"], 3)
    if parent_route:
        source = make_source_from_unit(parent_route)
        answer = combine_units([parent_route] + parent_points, 1000)
        for question in ["带孩子怎么玩？", "亲子游怎么玩？", "灵山胜境适合孩子的路线是什么？"]:
            add_faq(faqs, question, answer, "游玩建议", source)

    history_route = first_matching_unit(units, ["历史文化", "路线"])
    natural_route = first_matching_unit(units, ["自然风光", "路线"])
    if history_route:
        source = make_source_from_unit(history_route)
        add_faq(faqs, "深度游怎么玩？", history_route.get("content", ""), "游玩建议", source)
        add_faq(faqs, "历史文化爱好者怎么玩？", history_route.get("content", ""), "游玩建议", source)
    if natural_route:
        source = make_source_from_unit(natural_route)
        add_faq(faqs, "半天怎么玩？", natural_route.get("content", ""), "游玩建议", source)
        add_faq(faqs, "快速游怎么玩？", natural_route.get("content", ""), "游玩建议", source)

    rainy_units = collect_units(units, ["馆内", "展厅", "室内", "雨天", "闭馆", "禁止使用闪光灯"], 5)
    if rainy_units:
        source = make_source_from_unit(rainy_units[0])
        answer = combine_units(rainy_units, 1000)
        for question in ["雨天适合去哪？", "下雨天怎么玩？", "雨天有哪些室内景点？"]:
            add_faq(faqs, question, answer, "游玩建议", source)

    easy_units = collect_units(units, ["观光车", "体力有限", "休息", "老人", "60-69周岁老人", "70周岁以上老人"], 5)
    if easy_units:
        source = make_source_from_unit(easy_units[0])
        answer = combine_units(easy_units, 1000)
        for question in ["老人游怎么玩？", "体力有限怎么玩？", "带老人适合怎么安排？"]:
            add_faq(faqs, question, answer, "游玩建议", source)

    best_time = first_matching_unit(units, ["最佳游览时间"])
    if best_time:
        source = make_source_from_unit(best_time)
        for question in ["什么时候去比较好？", "最佳游览时间是什么？", "灵山胜境几点入园合适？"]:
            add_faq(faqs, question, best_time.get("content", ""), "游玩建议", source)

    return faqs


def classify_question(text: str) -> str:
    rules = [
        ("票务价格", ["票", "价格", "元", "免费", "半价"]),
        ("开放时间", ["开放", "时间", "场", "营业", "闭园", "演出"]),
        ("交通路线", ["交通", "公交", "自驾", "停车", "路线"]),
        ("历史文化", ["历史", "文化", "佛教", "禅", "意义", "地位"]),
        ("游玩建议", ["体验", "游览", "推荐", "适合", "路线"]),
        ("景点数据", ["基本数据", "规模", "高度", "建筑", "面积", "重量"]),
    ]
    for category, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return category
    return "景点介绍"


def dedupe_faq(faqs: list) -> list:
    seen = {}
    for faq in faqs:
        q = re.sub(r"\s+", "", faq.get("question", ""))
        a = re.sub(r"\s+", "", faq.get("answer", ""))[:120]
        key = (q, a)
        if key not in seen:
            seen[key] = faq

    result = []
    for index, faq in enumerate(seen.values(), 1):
        faq["id"] = f"faq_{index:04d}"
        result.append(faq)
    return result


def category_stats(faqs: list) -> dict:
    stats = defaultdict(int)
    for faq in faqs:
        stats[faq.get("category", "通用知识")] += 1
    return dict(sorted(stats.items()))


def main():
    print("=" * 70)
    print("灵山胜境 FAQ 生成")
    print("=" * 70)

    attractions = load_json(INPUT_ATTRACTIONS)
    units = load_json(INPUT_KNOWLEDGE_UNITS)
    print(f"加载景点: {len(attractions)}")
    print(f"加载知识块: {len(units)}")

    faqs = []
    faqs.extend(generate_attraction_faq(attractions))
    faqs.extend(generate_knowledge_faq(units))
    faqs = dedupe_faq(faqs)

    output = {
        "total": len(faqs),
        "data_source": "data/raw 两个 Word 文档",
        "generation": "rule_based_no_llm",
        "categories": category_stats(faqs),
        "faq": faqs,
    }

    with open(OUTPUT_FAQ, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"生成 FAQ: {len(faqs)} 条")
    print(f"保存到: {OUTPUT_FAQ}")
    print("类别分布:")
    for category, count in output["categories"].items():
        print(f"  {category}: {count}")


if __name__ == "__main__":
    main()
