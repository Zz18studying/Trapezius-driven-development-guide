# -*- coding: utf-8 -*-
"""
统一数据提取与合并脚本（DeepSeek API增强版）
功能：
1. 从文档1提取灵山胜境景点数据
2. 从文档2提取表格数据
3. 使用DeepSeek API智能清洗和补充数据
4. 自动匹配表格到对应景点并合并
5. 生成补充FAQ

适配新目录结构：
- 原始文档位置：data/raw/
- 输出文件位置：data/processed/
"""

import os
import sys
import json
import time
from docx import Document
from openai import OpenAI

# ==================== 路径配置 ====================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

DATA_RAW = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

os.makedirs(DATA_PROCESSED, exist_ok=True)

# 文件路径
DOC1_PATH = os.path.join(DATA_RAW, "灵山胜境 景点结构化数据集.docx")
DOC2_PATH = os.path.join(DATA_RAW, "灵山胜境：历史、文化、景点特色与个性化游览指南.docx")
OUTPUT_ATTRACTIONS = os.path.join(DATA_PROCESSED, "attractions_complete.json")
OUTPUT_SUPPLEMENT_FAQ = os.path.join(DATA_PROCESSED, "supplement_faq.json")

# ==================== DeepSeek API 配置 ====================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-v4-flash"  # 推荐使用 Flash 版本

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)


def call_deepseek_api(prompt, temperature=0.3, max_tokens=2048):
    """调用 DeepSeek API，使用较低温度保证输出稳定"""
    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"   ⚠️ API调用失败: {e}")
        return None


def clean_and_enhance_attraction(attraction):
    """使用 API 清洗和补充景点数据"""

    # 检查是否需要补充（如果数据已经完整则跳过）
    name = attraction.get("name", "")
    specs = attraction.get("specs", "")

    if len(specs) > 100 and attraction.get("culture"):
        # 数据已经比较完整，跳过API调用节省成本
        return attraction

    prompt = f"""你是灵山胜境景区的数据专家。请根据以下原始数据，为景点「{name}」生成补充信息。

【原始数据】
{json.dumps(attraction, ensure_ascii=False, indent=2)[:1500]}

【要求】
请分析并补充以下字段（JSON格式）：
1. short_desc: 一句话简介（20字以内）
2. best_time: 最佳游览时间（如：上午/下午/全天）
3. duration: 建议游览时长（如：15分钟/30分钟）
4. tags: 标签数组（3-5个，如：["地标","祈福","拍照"]）
5. enhanced_specs: 如果原始specs不完整，补充完整信息
6. enhanced_culture: 如果原始culture不完整，补充文化内涵

【输出格式】
直接输出JSON对象，不要有其他文字：
{{
  "short_desc": "...",
  "best_time": "...",
  "duration": "...",
  "tags": [...],
  "enhanced_specs": "...",
  "enhanced_culture": "..."
}}

如果某个字段无需补充，请留空字符串或空数组。
"""

    result = call_deepseek_api(prompt, temperature=0.3)
    if result:
        try:
            # 清理可能的markdown标记
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                result = result.split("```")[1].split("```")[0]
            supplement = json.loads(result.strip())
            attraction["ai_supplement"] = supplement
            print(f"      🤖 AI补充: {supplement.get('short_desc', '')[:30]}...")
        except Exception as e:
            print(f"      ⚠️ AI补充解析失败: {e}")

    return attraction


# ==================== 表格到景点的映射 ====================
TABLE_TO_ATTRACTION_MAP = {
    1: "LS-011",  # 灵山大佛
    2: "LS-013",  # 灵山梵宫
    3: "LS-006",  # 九龙灌浴
    4: "LS-010",  # 祥符禅寺
    5: "LS-014",  # 五印坛城
    6: "LS-015",  # 曼飞龙塔
}

FIELD_MAPPING = {
    "基本数据": "basic_data",
    "建造工艺": "construction_process",
    "佛教意义": "buddhist_meaning",
    "最佳体验": "best_experience",
    "建筑规模": "architecture_scale",
    "核心艺术": "core_art",
    "特色体验": "special_experience",
    "文化地位": "cultural_status",
}


# ==================== 1. 从文档1提取景点数据 ====================
def extract_attractions_from_doc1(file_path):
    """从文档1提取灵山胜境景点数据"""
    print(f"   读取文件: {os.path.basename(file_path)}")
    doc = Document(file_path)
    attractions = []

    for table in doc.tables:
        rows = list(table.rows)
        if len(rows) < 2:
            continue

        first_cell = rows[0].cells[0].text if rows[0].cells else ""
        if "景区名称" not in first_cell:
            continue

        for row in rows[1:]:
            cells = row.cells
            if len(cells) < 5:
                continue

            scenic_name = cells[0].text.strip()
            if "拈花湾" in scenic_name:
                continue
            if "灵山胜境" not in scenic_name:
                continue

            attraction = {
                "id": cells[1].text.strip() if len(cells) > 1 else "",
                "name": cells[2].text.strip() if len(cells) > 2 else "",
                "location": cells[3].text.strip() if len(cells) > 3 else "",
                "specs": cells[4].text.strip() if len(cells) > 4 else "",
                "function": cells[5].text.strip() if len(cells) > 5 else "",
                "culture": cells[6].text.strip() if len(cells) > 6 else "",
                "details": cells[7].text.strip() if len(cells) > 7 else "",
                "highlights": cells[8].text.strip() if len(cells) > 8 else "",
                "hours": cells[9].text.strip() if len(cells) > 9 else "",
                "remarks": cells[10].text.strip() if len(cells) > 10 else "",
                "supplement": {},
                "ai_supplement": {}
            }

            if attraction["name"]:
                attractions.append(attraction)
                print(f"   ✅ 景点: {attraction['id']} {attraction['name']}")

    return attractions


# ==================== 2. 从文档2提取表格数据 ====================
def extract_tables_from_doc2(file_path):
    """从文档2提取表格数据"""
    print(f"   读取文件: {os.path.basename(file_path)}")
    doc = Document(file_path)
    all_tables = []

    for idx, table in enumerate(doc.tables):
        table_data = {
            "index": idx + 1,
            "structured": {}
        }

        rows = list(table.rows)
        if len(rows) < 2:
            continue

        headers = [cell.text.strip() for cell in rows[0].cells]

        for row in rows[1:]:
            cells = [cell.text.strip() for cell in row.cells]
            if len(cells) >= 2:
                key = cells[0]
                value = cells[1] if len(cells) > 1 else ""
                if key and value:
                    table_data["structured"][key] = value

        if table_data["structured"]:
            all_tables.append(table_data)
            print(f"   📊 表格{idx + 1}: {len(table_data['structured'])} 项数据")

    return all_tables


# ==================== 3. 合并表格数据到景点 ====================
def merge_tables_to_attractions(attractions, tables):
    """将表格数据合并到对应的景点"""

    attraction_map = {a.get("id"): a for a in attractions if a.get("id")}
    merged_count = 0
    supplements_added = {}

    for table in tables:
        table_idx = table["index"]

        if table_idx not in TABLE_TO_ATTRACTION_MAP:
            print(f"   ⏭️ 表格{table_idx}: 无对应景点（通用信息，跳过）")
            continue

        attraction_id = TABLE_TO_ATTRACTION_MAP[table_idx]

        if attraction_id not in attraction_map:
            print(f"   ⚠️ 表格{table_idx}: 景点 {attraction_id} 不存在")
            continue

        attraction = attraction_map[attraction_id]
        structured_data = table["structured"]

        for key, value in structured_data.items():
            field_name = FIELD_MAPPING.get(key, key)
            attraction["supplement"][field_name] = value

        merged_count += 1
        supplements_added[attraction_id] = len(structured_data)
        print(f"   ✅ 表格{table_idx} → {attraction_id} {attraction['name']}: 添加 {len(structured_data)} 个补充字段")

    return attractions, merged_count, supplements_added


# ==================== 3.5 AI 智能清洗数据 ====================
def ai_enhance_attractions(attractions):
    """使用 AI 批量清洗和补充景点数据"""
    print("\n🤖 正在使用 AI 智能补充景点数据...")

    # 只对数据不完整的景点调用 API
    for i, attr in enumerate(attractions, 1):
        specs = attr.get("specs", "")
        if len(specs) < 50:  # 数据不完整
            print(f"   [{i}/{len(attractions)}] 补充: {attr['name']}")
            clean_and_enhance_attraction(attr)
            time.sleep(0.5)  # 避免请求过快

    return attractions


# ==================== 4. 生成补充FAQ ====================
def generate_supplement_faq(attractions, tables):
    """基于合并后的数据生成补充FAQ"""
    supplement_faq = []
    attraction_map = {a.get("id"): a for a in attractions if a.get("id")}

    # 预设的FAQ模板
    faq_templates = [
        {"trigger_key": "basic_data", "question_template": "{name}的基本数据是什么？", "category": "景点介绍"},
        {"trigger_key": "construction_process", "question_template": "{name}是怎么建造的？", "category": "景点介绍"},
        {"trigger_key": "buddhist_meaning", "question_template": "{name}有什么佛教意义？", "category": "历史文化"},
        {"trigger_key": "best_experience", "question_template": "{name}的最佳体验方式是什么？", "category": "游玩建议"},
        {"trigger_key": "architecture_scale", "question_template": "{name}的规模有多大？", "category": "景点介绍"},
        {"trigger_key": "core_art", "question_template": "{name}有什么艺术珍品？", "category": "景点介绍"},
        {"trigger_key": "special_experience", "question_template": "{name}有什么特色体验？", "category": "游玩建议"},
        {"trigger_key": "cultural_status", "question_template": "{name}有什么文化地位？", "category": "历史文化"},
    ]

    for table in tables:
        table_idx = table["index"]
        if table_idx not in TABLE_TO_ATTRACTION_MAP:
            continue

        attraction_id = TABLE_TO_ATTRACTION_MAP[table_idx]
        attraction = attraction_map.get(attraction_id)
        if not attraction:
            continue

        name = attraction.get("name", "")
        supplement = attraction.get("supplement", {})

        for template in faq_templates:
            trigger_key = template["trigger_key"]
            if trigger_key in supplement:
                value = supplement[trigger_key]
                answer = value[:200] + "..." if len(value) > 200 else value
                supplement_faq.append({
                    "question": template["question_template"].format(name=name),
                    "answer": answer,
                    "category": template["category"],
                    "source_attraction": attraction_id,
                    "source": "文档2表格数据"
                })

    # 添加 AI 补充的 FAQ
    for attr in attractions:
        ai_supp = attr.get("ai_supplement", {})
        name = attr.get("name", "")

        if ai_supp.get("short_desc"):
            supplement_faq.append({
                "question": f"{name}有什么特色？",
                "answer": ai_supp.get("short_desc", ""),
                "category": "景点介绍",
                "source_attraction": attr.get("id", ""),
                "source": "AI生成"
            })

        if ai_supp.get("best_time"):
            supplement_faq.append({
                "question": f"{name}什么时候去最好？",
                "answer": f"建议{ai_supp.get('best_time', '')}游览",
                "category": "游玩建议",
                "source_attraction": attr.get("id", ""),
                "source": "AI生成"
            })

    return supplement_faq


# ==================== 5. 保存所有结果 ====================
def save_all_results(attractions, supplement_faq):
    """保存所有结果"""
    with open(OUTPUT_ATTRACTIONS, 'w', encoding='utf-8') as f:
        json.dump(attractions, f, ensure_ascii=False, indent=2)
    print(f"   ✅ 景点数据: {OUTPUT_ATTRACTIONS}")
    print(f"      文件大小: {os.path.getsize(OUTPUT_ATTRACTIONS) / 1024:.1f} KB")

    with open(OUTPUT_SUPPLEMENT_FAQ, 'w', encoding='utf-8') as f:
        json.dump(supplement_faq, f, ensure_ascii=False, indent=2)
    print(f"   ✅ 补充FAQ: {OUTPUT_SUPPLEMENT_FAQ}")
    print(f"      文件大小: {os.path.getsize(OUTPUT_SUPPLEMENT_FAQ) / 1024:.1f} KB")


# ==================== 6. 打印详细统计 ====================
def print_detailed_stats(attractions, merged_count, supplements_added, supplement_faq):
    """打印详细统计信息"""
    print("\n" + "=" * 60)
    print("📊 最终统计")
    print("=" * 60)

    print(f"\n🏛️ 景点数据:")
    print(f"   总景点数: {len(attractions)}")

    with_supplement = [a for a in attractions if a.get("supplement")]
    with_ai_supplement = [a for a in attractions if a.get("ai_supplement")]

    print(f"   有表格补充: {len(with_supplement)} 个")
    print(f"   有AI补充: {len(with_ai_supplement)} 个")

    print(f"\n📝 补充FAQ:")
    print(f"   生成数量: {len(supplement_faq)}")

    print(f"\n💾 输出文件:")
    print(f"   景点数据: {OUTPUT_ATTRACTIONS}")
    print(f"   补充FAQ: {OUTPUT_SUPPLEMENT_FAQ}")


# ==================== 7. 主函数 ====================
def main():
    print("=" * 60)
    print("灵山胜境 - 统一数据提取与合并工具（AI增强版）")
    print(f"项目根目录: {PROJECT_ROOT}")
    print("=" * 60)

    # 检查 API Key
    if DEEPSEEK_API_KEY == "你的API-Key":
        print("\n⚠️ 请先设置 DEEPSEEK_API_KEY 环境变量！")
        print("   或在代码中填入你的API Key")

    # 检查文件
    print("\n📁 检查文件...")
    if not os.path.exists(DOC1_PATH):
        print(f"   ❌ 文件不存在: {DOC1_PATH}")
        print("   请确保原始文档在 data/raw/ 目录下")
        return
    else:
        print(f"   ✅ 文档1: {os.path.basename(DOC1_PATH)}")

    if not os.path.exists(DOC2_PATH):
        print(f"   ❌ 文件不存在: {DOC2_PATH}")
        return
    else:
        print(f"   ✅ 文档2: {os.path.basename(DOC2_PATH)}")

    # 步骤1：提取景点数据
    print("\n📖 [1/5] 从文档1提取景点数据...")
    attractions = extract_attractions_from_doc1(DOC1_PATH)
    print(f"   共提取 {len(attractions)} 个景点")

    if not attractions:
        print("   ❌ 未提取到景点数据")
        return

    # 步骤2：提取表格数据
    print("\n📊 [2/5] 从文档2提取表格数据...")
    tables = extract_tables_from_doc2(DOC2_PATH)
    print(f"   共提取 {len(tables)} 个表格")

    # 步骤3：合并数据
    print("\n🔗 [3/5] 合并表格数据到景点...")
    merged_attractions, merged_count, supplements_added = merge_tables_to_attractions(attractions, tables)
    print(f"   成功合并 {merged_count} 个表格")

    # 步骤4：AI智能补充（可选）
    if DEEPSEEK_API_KEY != "你的API-Key":
        merged_attractions = ai_enhance_attractions(merged_attractions)

    # 步骤5：生成补充FAQ
    print("\n📝 [5/5] 生成补充FAQ...")
    supplement_faq = generate_supplement_faq(merged_attractions, tables)
    print(f"   生成 {len(supplement_faq)} 条补充FAQ")

    # 保存结果
    print("\n💾 保存结果...")
    save_all_results(merged_attractions, supplement_faq)

    # 打印详细统计
    print_detailed_stats(merged_attractions, merged_count, supplements_added, supplement_faq)

    print("\n✨ 数据提取与合并完成！")


if __name__ == "__main__":
    main()