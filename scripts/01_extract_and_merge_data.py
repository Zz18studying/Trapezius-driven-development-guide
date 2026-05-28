# -*- coding: utf-8 -*-
"""
统一数据提取与合并脚本
功能：
1. 从文档1提取灵山胜境景点数据
2. 从文档2提取表格数据
3. 自动匹配表格到对应景点并合并
4. 生成补充FAQ

适配新目录结构：
- 原始文档位置：data/raw/
- 输出文件位置：data/processed/
"""

import os
import sys
import json
from docx import Document

# ==================== 路径配置 ====================
# 获取脚本所在目录和项目根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# 定义各目录路径
DATA_RAW = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

# 确保目录存在
os.makedirs(DATA_PROCESSED, exist_ok=True)

# 文件路径
DOC1_PATH = os.path.join(DATA_RAW, "灵山胜境 景点结构化数据集.docx")
DOC2_PATH = os.path.join(DATA_RAW, "灵山胜境：历史、文化、景点特色与个性化游览指南.docx")
OUTPUT_ATTRACTIONS = os.path.join(DATA_PROCESSED, "attractions_complete.json")
OUTPUT_SUPPLEMENT_FAQ = os.path.join(DATA_PROCESSED, "supplement_faq.json")


# ==================== 配置 ====================
# 表格到景点的映射（表格索引 -> 景点ID）
# 注意：表格索引从1开始，按文档中出现的顺序
TABLE_TO_ATTRACTION_MAP = {
    1: "LS-011",  # 灵山大佛
    2: "LS-013",  # 灵山梵宫
    3: "LS-006",  # 九龙灌浴
    4: "LS-010",  # 祥符禅寺
    5: "LS-014",  # 五印坛城
    6: "LS-015",  # 曼飞龙塔
}

# 需要合并的字段映射
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
                "supplement": {}  # 预留补充字段
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

        # 尝试获取表头（第一行）
        headers = [cell.text.strip() for cell in rows[0].cells]

        for row in rows[1:]:  # 跳过表头
            cells = [cell.text.strip() for cell in row.cells]
            if len(cells) >= 2:
                # 如果第一列是"项目"类，直接用第一列作为key
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

    # 创建景点ID映射
    attraction_map = {a.get("id"): a for a in attractions if a.get("id")}

    merged_count = 0
    supplements_added = {}

    for table in tables:
        table_idx = table["index"]

        # 查找对应的景点
        if table_idx not in TABLE_TO_ATTRACTION_MAP:
            print(f"   ⏭️ 表格{table_idx}: 无对应景点（通用信息，跳过）")
            continue

        attraction_id = TABLE_TO_ATTRACTION_MAP[table_idx]

        if attraction_id not in attraction_map:
            print(f"   ⚠️ 表格{table_idx}: 景点 {attraction_id} 不存在")
            continue

        attraction = attraction_map[attraction_id]
        structured_data = table["structured"]

        # 合并数据
        for key, value in structured_data.items():
            field_name = FIELD_MAPPING.get(key, key)
            attraction["supplement"][field_name] = value

        merged_count += 1
        supplements_added[attraction_id] = len(structured_data)
        print(f"   ✅ 表格{table_idx} → {attraction_id} {attraction['name']}: 添加 {len(structured_data)} 个补充字段")

    return attractions, merged_count, supplements_added


# ==================== 4. 生成补充FAQ ====================
def generate_supplement_faq(attractions, tables):
    """基于合并后的数据生成补充FAQ"""
    supplement_faq = []

    # 创建景点映射
    attraction_map = {a.get("id"): a for a in attractions if a.get("id")}

    # 预设的FAQ模板
    faq_templates = [
        {
            "trigger_key": "basic_data",
            "question_template": "{name}的基本数据是什么？",
            "category": "景点介绍"
        },
        {
            "trigger_key": "construction_process",
            "question_template": "{name}是怎么建造的？",
            "category": "景点介绍"
        },
        {
            "trigger_key": "buddhist_meaning",
            "question_template": "{name}有什么佛教意义？",
            "category": "历史文化"
        },
        {
            "trigger_key": "best_experience",
            "question_template": "{name}的最佳体验方式是什么？",
            "category": "游玩建议"
        },
        {
            "trigger_key": "architecture_scale",
            "question_template": "{name}的规模有多大？",
            "category": "景点介绍"
        },
        {
            "trigger_key": "core_art",
            "question_template": "{name}有什么艺术珍品？",
            "category": "景点介绍"
        },
        {
            "trigger_key": "special_experience",
            "question_template": "{name}有什么特色体验？",
            "category": "游玩建议"
        },
        {
            "trigger_key": "cultural_status",
            "question_template": "{name}有什么文化地位？",
            "category": "历史文化"
        }
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
                # 截取前200字符作为答案
                answer = value[:200] + "..." if len(value) > 200 else value
                supplement_faq.append({
                    "question": template["question_template"].format(name=name),
                    "answer": answer,
                    "category": template["category"],
                    "source_attraction": attraction_id,
                    "source": "文档2表格数据"
                })

    return supplement_faq


# ==================== 5. 保存所有结果 ====================
def save_all_results(attractions, supplement_faq):
    """保存所有结果"""

    # 保存景点数据
    with open(OUTPUT_ATTRACTIONS, 'w', encoding='utf-8') as f:
        json.dump(attractions, f, ensure_ascii=False, indent=2)
    print(f"   ✅ 景点数据: {OUTPUT_ATTRACTIONS}")
    print(f"      文件大小: {os.path.getsize(OUTPUT_ATTRACTIONS) / 1024:.1f} KB")

    # 保存补充FAQ
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

    # 景点统计
    print(f"\n🏛️ 景点数据:")
    print(f"   总景点数: {len(attractions)}")

    # 分类统计有补充的景点
    with_supplement = [a for a in attractions if a.get("supplement")]
    without_supplement = [a for a in attractions if not a.get("supplement")]

    print(f"   有补充数据: {len(with_supplement)} 个")
    print(f"   无补充数据: {len(without_supplement)} 个")

    # 有补充的景点详情
    if with_supplement:
        print(f"\n📋 有补充数据的景点:")
        for attr in with_supplement:
            supp_count = len(attr.get("supplement", {}))
            print(f"   {attr['id']} {attr['name']}: {supp_count} 个补充字段")

    # 补充FAQ统计
    print(f"\n📝 补充FAQ:")
    print(f"   生成数量: {len(supplement_faq)}")

    # 按类别统计
    if supplement_faq:
        cat_stats = {}
        for faq in supplement_faq:
            cat = faq.get("category", "未知")
            cat_stats[cat] = cat_stats.get(cat, 0) + 1

        print(f"\n📊 补充FAQ类别分布:")
        for cat, count in sorted(cat_stats.items(), key=lambda x: -x[1]):
            print(f"   {cat}: {count}条")

    # 文件保存位置
    print(f"\n💾 输出文件:")
    print(f"   景点数据: {OUTPUT_ATTRACTIONS}")
    print(f"   补充FAQ: {OUTPUT_SUPPLEMENT_FAQ}")


# ==================== 7. 主函数 ====================
def main():
    print("=" * 60)
    print("灵山胜境 - 统一数据提取与合并工具")
    print(f"项目根目录: {PROJECT_ROOT}")
    print("=" * 60)

    # 检查文件是否存在
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
    print("\n📖 [1/4] 从文档1提取景点数据...")
    attractions = extract_attractions_from_doc1(DOC1_PATH)
    print(f"   共提取 {len(attractions)} 个景点")

    if not attractions:
        print("   ❌ 未提取到景点数据")
        return

    # 步骤2：提取表格数据
    print("\n📊 [2/4] 从文档2提取表格数据...")
    tables = extract_tables_from_doc2(DOC2_PATH)
    print(f"   共提取 {len(tables)} 个表格")

    # 步骤3：合并数据
    print("\n🔗 [3/4] 合并表格数据到景点...")
    merged_attractions, merged_count, supplements_added = merge_tables_to_attractions(attractions, tables)
    print(f"   成功合并 {merged_count} 个表格")

    # 步骤4：生成补充FAQ
    print("\n📝 [4/4] 生成补充FAQ...")
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