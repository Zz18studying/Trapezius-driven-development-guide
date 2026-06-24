# -*- coding: utf-8 -*-
"""
使用 DeepSeek API 生成完整FAQ - 官方数据 + 适度扩展
数据来源：
1. 灵山胜境 景点结构化数据集.docx（核心数据）
2. 灵山胜境：历史、文化、景点特色与个性化游览指南.docx（历史、路线、实用信息）

扩展原则：
- 硬数据（高度、价格、时间、数量）必须来自文档，不可修改
- 概述性描述可综合多条数据形成流畅叙述
- 关联性推荐可基于景点特色进行逻辑推理
- 体验性建议可结合常识适度补充（如防晒、穿舒适鞋等）
- 场景化推荐可根据用户需求重组路线
"""

import json
import re
import time
import os
from openai import OpenAI

# ==================== 路径配置 ====================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")
INPUT_FILE = os.path.join(DATA_PROCESSED, "attractions_complete.json")
OUTPUT_FILE = os.path.join(DATA_PROCESSED, "faq_final.json")

os.makedirs(DATA_PROCESSED, exist_ok=True)

# ==================== API 配置 ====================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-v4-flash"

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)


def call_deepseek_api(prompt, temperature=0.3):
    """调用 DeepSeek API"""
    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=4096
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"   ❌ API调用失败: {e}")
        return None


def fix_and_parse_json(text):
    """修复并解析JSON"""
    if not text:
        return None

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    text = re.sub(r'\}\s*\n\s*\{', '},\n{', text)
    text = re.sub(r'\]\s*\n\s*\{', '],\n{', text)
    text = re.sub(r',\s*\]', ']', text)
    text = re.sub(r',\s*\}', '}', text)

    pattern = r'\[\s*\{.*?\}\s*\]'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass

    try:
        return json.loads(text.strip())
    except:
        return None


def load_attractions():
    """加载景点数据"""
    if not os.path.exists(INPUT_FILE):
        print(f"   ❌ 文件不存在: {INPUT_FILE}")
        return None
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ==================== 核心景点列表 ====================
CORE_ATTRACTIONS = [
    "灵山大照壁", "五明桥", "佛足坛", "五智门", "菩提大道",
    "九龙灌浴", "降魔浮雕", "阿育王柱", "百子戏弥勒", "祥符禅寺",
    "灵山大佛", "佛教文化博览馆", "灵山梵宫", "五印坛城", "曼飞龙塔", "无尽意斋"
]

NH_ATTRACTIONS = [
    "拈花广场", "梵天花海", "香月花街", "拈花堂", "五灯湖", "鹿鸣谷"
]


def generate_attraction_faq(attraction, target_count):
    """
    为景点生成FAQ - 官方数据 + 适度扩展
    硬数据必须来自文档，描述可综合扩展
    """
    name = attraction.get('name', '')
    if not name:
        return []

    specs = attraction.get('specs', '')[:200]
    culture = attraction.get('culture', '')[:150]
    highlights = attraction.get('highlights', '')[:150]
    hours = attraction.get('hours', '')
    details = attraction.get('details', '')[:150]
    function = attraction.get('function', '')[:100]
    location = attraction.get('location', '')[:100]

    supplement = attraction.get("supplement", {})
    supplement_text = ""
    if supplement:
        supplement_text = f"补充信息：{json.dumps(supplement, ensure_ascii=False)[:200]}"

    prompt = f"""为景点「{name}」生成{target_count}条FAQ。

【官方核心数据】（必须使用，不可修改数字）
名称：{name}
位置：{location}
建筑参数：{specs}
文化内涵：{culture}
游玩亮点：{highlights}
开放时间：{hours}
详细介绍：{details}
功能用途：{function}
{supplement_text}

【生成规则】
1. 硬数据（高度、重量、尺寸、价格、时间、数量）：必须来自上方数据，不可修改
2. 概述性描述：可综合多条数据形成流畅的自然语言描述
3. 体验性建议：可基于常识补充合理建议（如"注意防晒""穿舒适鞋"等）
4. 关联性推荐：可基于景点特色进行逻辑推理
5. 每条答案30-60字

【必须包含的5种类型】
- 概述性（2条）：{name}有什么特色/看点
- 事实性（2条）：具体数据
- 体验性（2条）：怎么玩/做什么
- 文化性（2条）：文化内涵/历史
- 实用性（2条）：注意事项/最佳时间

category根据类型设置：景点概述/景点数据/游玩体验/文化历史/实用贴士

输出JSON数组："""
    print(f"      📤 {name} ({target_count}条)...")
    result = call_deepseek_api(prompt)
    if not result:
        return []
    faq_list = fix_and_parse_json(result)
    if faq_list and len(faq_list) >= 3:
        print(f"         ✅ 生成 {len(faq_list)} 条")
        return faq_list[:target_count]
    print(f"         ⚠️ 解析失败")
    return []


def generate_overview_faq(attractions):
    """
    为核心景点生成概述性FAQ - 允许综合扩展
    确保"XX有什么特色"类问题能自然回答
    """
    overview_faq = []
    core_names = ["灵山大佛", "九龙灌浴", "灵山梵宫", "五印坛城", "祥符禅寺"]

    for attr in attractions:
        name = attr.get('name', '')
        if name not in core_names:
            continue

        specs = attr.get('specs', '')[:200]
        culture = attr.get('culture', '')[:150]
        highlights = attr.get('highlights', '')[:150]
        details = attr.get('details', '')[:150]

        prompt = f"""为「{name}」生成4条概述性FAQ，要求自然、有温度，像真人导游介绍。

【官方数据】（硬数据必须准确）
名称：{name}
建筑参数：{specs}
文化内涵：{culture}
游玩亮点：{highlights}
详细介绍：{details}

【4个问题】
1. {name}有什么特色？
2. {name}有什么看点？
3. {name}值得去吗？
4. {name}有什么好玩的？

【规则】
- 硬数据（高度、重量、尺寸等）必须来自上方数据
- 描述可以综合扩展，形成流畅的自然语言
- 每条答案40-60字
- category为"景点概述"

输出JSON数组："""
        print(f"      📤 概述FAQ: {name}")
        result = call_deepseek_api(prompt)
        if result:
            faq_list = fix_and_parse_json(result)
            if faq_list:
                overview_faq.extend(faq_list)
                print(f"         ✅ 生成 {len(faq_list)} 条")
        time.sleep(0.3)

    return overview_faq


def generate_history_faq():
    """历史文化FAQ - 综合扩展"""
    prompt = """生成历史文化FAQ，答案要有故事感。

【官方历史数据】
- 唐贞观年间，玄奘取经归来见马山形似印度灵鹫山，命名"小灵山"
- 玄奘弟子窥基在此住持道场，兴建小灵山庵
- 北宋大中祥符年间（1008-1016年），宋真宗赐额"祥符禅寺"
- 现存千年银杏、六角古井等遗迹
- 1994年灵山大佛奠基，1997年落成
- 2009年梵宫开放，成为世界佛教论坛永久会址
- 赵朴初提出"五方五佛"：灵山、香港、乐山、云冈、龙门

【规则】
- 历史事实必须准确
- 可适当增加"故事感"和"温度"
- category为"历史文化"

输出JSON数组（15-18条）："""
    print(f"      📤 历史文化FAQ...")
    result = call_deepseek_api(prompt)
    if not result:
        return []
    faq_list = fix_and_parse_json(result)
    if faq_list:
        print(f"         ✅ 生成 {len(faq_list)} 条")
        return faq_list
    return []


def generate_route_faq():
    """路线FAQ - 可灵活组合"""
    prompt = """生成游览路线FAQ，推荐要自然、有温度。

【官方路线】
历史文化路线（6小时）：大照壁→佛手广场→祥符禅寺→灵山大佛→灵山梵宫→五印坛城
自然风光路线（5小时）：佛足坛→九龙灌浴→菩提大道→灵山大佛→曼飞龙塔→灵山精舍
亲子路线（4小时）：九龙灌浴→佛手广场→百子戏弥勒→灵山梵宫→五印坛城

【特色体验】
- 祥符禅寺撞钟（12.8吨）
- 梵宫《吉祥颂》（10:35/11:30/14:00/16:00）
- 大佛平台看日落
- 五印坛城转经筒

【规则】
- 路线景点顺序要准确
- 可根据用户需求灵活推荐（如"只有半天"可精简路线）
- 推荐语言要像真人导游
- category为"游玩建议"

输出JSON数组（12-15条）："""
    print(f"      📤 游览路线FAQ...")
    result = call_deepseek_api(prompt)
    if not result:
        return []
    faq_list = fix_and_parse_json(result)
    if faq_list:
        print(f"         ✅ 生成 {len(faq_list)} 条")
        return faq_list
    return []


def generate_practical_faq():
    """实用贴士FAQ - 可结合常识补充"""
    prompt = """生成实用贴士FAQ。

【官方数据】
门票：成人210元，学生/老人105元，6岁以下/70岁以上免票，联票225元
时间：夏季8:00-17:00，冬季8:00-16:30
九龙灌浴：10:00/11:30/13:30/15:00
吉祥颂：10:35/11:30/14:00/16:00
餐饮：梵宫素斋50元，素面35元
住宿：灵山精舍800-1500元，周边酒店200-500元

【规则】
- 价格、时间必须准确
- 可补充常识性建议（如"穿运动鞋""夏季防晒"）
- category为"实用信息"

输出JSON数组（12-15条）："""
    print(f"      📤 实用贴士FAQ...")
    result = call_deepseek_api(prompt)
    if not result:
        return []
    faq_list = fix_and_parse_json(result)
    if faq_list:
        print(f"         ✅ 生成 {len(faq_list)} 条")
        return faq_list
    return []


def generate_scenario_faq():
    """场景化FAQ"""
    scenarios = [
        ("亲子游", "九龙灌浴→佛手广场→百子戏弥勒→灵山梵宫，喷泉互动、趣味打卡"),
        ("老人游", "坐观光车游览九龙灌浴→祥符禅寺→灵山大佛→灵山梵宫，有轮椅租赁"),
        ("雨天", "灵山梵宫→佛教文化博览馆→五印坛城→无尽意斋，全部室内"),
        ("情侣", "香水海→灵山大佛→灵山梵宫→五印坛城，适合拍照打卡"),
        ("深度游", "大照壁→祥符禅寺→大佛→梵宫→五印坛城→曼飞龙塔，6小时全面感受"),
        ("快速游", "灵山大佛→九龙灌浴→灵山梵宫，2-3小时逛完核心"),
        ("秋游", "祥符禅寺千年银杏→菩提大道→梵天花海，金黄银杏季"),
        ("春游", "梵天花海格桑花→菩提大道→香水海，春暖花开"),
    ]
    faq_list = []
    for name, content in scenarios:
        faq_list.append({"question": f"灵山胜境{name}怎么玩？", "answer": content[:200], "category": "场景攻略"})
        faq_list.append({"question": f"灵山胜境{name}推荐路线", "answer": content[:200], "category": "场景攻略"})
    print(f"      📤 场景化FAQ: {len(scenarios) * 2}条")
    return faq_list


def generate_general_faq(category_name, category_data, target_count):
    """通用类别FAQ"""
    prompt = f"""生成「{category_name}」FAQ，{target_count}条。

【数据】{category_data}

问题口语化，答案简洁准确，可结合常识适度扩展，category为"{category_name}"。

输出JSON数组："""
    print(f"      📤 {category_name} ({target_count}条)...")
    result = call_deepseek_api(prompt)
    if not result:
        return []
    faq_list = fix_and_parse_json(result)
    if faq_list:
        print(f"         ✅ 生成 {len(faq_list)} 条")
        return faq_list[:target_count]
    return []


def main():
    print("=" * 70)
    print("官方数据集FAQ生成 - 适度扩展版")
    print("硬数据来自文档，描述可综合扩展")
    print("=" * 70)

    if DEEPSEEK_API_KEY == "你的API-Key":
        print("\n⚠️ 请先设置 DEEPSEEK_API_KEY 环境变量！")
        return

    attractions = load_attractions()
    if attractions is None:
        return

    print(f"\n📖 加载 {len(attractions)} 个景点")

    core_list = [a for a in attractions if a.get('name') in CORE_ATTRACTIONS]
    normal_list = [a for a in attractions if a.get('name') not in CORE_ATTRACTIONS and a.get('name') not in NH_ATTRACTIONS]
    nh_list = [a for a in attractions if a.get('name') in NH_ATTRACTIONS]

    all_faq = []

    # ===== 1. 核心景点FAQ =====
    print("\n" + "=" * 70)
    print("第1部分：核心景点FAQ（16个景点 × 10条）")
    print("=" * 70)
    for attr in core_list:
        faq = generate_attraction_faq(attr, 10)
        all_faq.extend(faq)
        time.sleep(0.5)

    # ===== 2. 普通景点FAQ =====
    print("\n" + "=" * 70)
    print("第2部分：普通景点FAQ（6条/个）")
    print("=" * 70)
    for attr in normal_list:
        faq = generate_attraction_faq(attr, 6)
        all_faq.extend(faq)
        time.sleep(0.5)

    # ===== 3. 拈花湾景点FAQ =====
    print("\n" + "=" * 70)
    print("第3部分：拈花湾景点FAQ（6条/个）")
    print("=" * 70)
    for attr in nh_list:
        faq = generate_attraction_faq(attr, 6)
        all_faq.extend(faq)
        time.sleep(0.5)

    # ===== 4. 概述性FAQ =====
    print("\n" + "=" * 70)
    print("第4部分：概述性FAQ（核心景点）")
    print("=" * 70)
    overview = generate_overview_faq(attractions)
    all_faq.extend(overview)

    # ===== 5. 历史文化 =====
    print("\n" + "=" * 70)
    print("第5部分：历史文化FAQ")
    print("=" * 70)
    history = generate_history_faq()
    all_faq.extend(history)

    # ===== 6. 游览路线 =====
    print("\n" + "=" * 70)
    print("第6部分：游览路线FAQ")
    print("=" * 70)
    routes = generate_route_faq()
    all_faq.extend(routes)

    # ===== 7. 实用贴士 =====
    print("\n" + "=" * 70)
    print("第7部分：实用贴士FAQ")
    print("=" * 70)
    practical = generate_practical_faq()
    all_faq.extend(practical)

    # ===== 8. 场景化 =====
    print("\n" + "=" * 70)
    print("第8部分：场景化FAQ")
    print("=" * 70)
    scenario = generate_scenario_faq()
    all_faq.extend(scenario)

    # ===== 9. 通用类别 =====
    print("\n" + "=" * 70)
    print("第9部分：通用类别FAQ")
    print("=" * 70)
    general_categories = [
        ("票务服务", "成人210元。学生/老人半价105元。6岁以下/70岁以上免票。联票225元含观光车。", 8),
        ("开放时间", "夏季8:00-17:00，冬季8:00-16:30。九龙灌浴平日四场。", 8),
        ("交通出行", "公交88/89路。自驾走太湖大道。停车场15元/天。观光车40元。", 8),
        ("餐饮住宿", "梵宫素斋50元。素面35元。灵山精舍800-1500元。周边200-500元。", 8),
        ("便民设施", "轮椅免费租。婴儿车30元。行李寄存免费。母婴室。WiFi。", 8),
        ("购物特产", "灵山素饼、佛珠手串、香薰、书签、禅茶。梵宫商店可购。", 8),
        ("入园须知", "凭身份证或二维码入园。禁带打火机、刀具、宠物。", 6),
        ("安全须知", "禁止翻越栏杆。禁止吸烟。涉水注意安全。", 6),
        ("拍照指南", "最佳机位：大佛平台全景、香水海倒影、梵宫穹顶、九龙灌浴广场。", 6),
        ("避坑建议", "节假日9点前人少。九龙灌浴提前10分钟占位。吉祥颂提前30分钟排队。", 6),
    ]
    for cat_name, cat_data, target in general_categories:
        faq = generate_general_faq(cat_name, cat_data, target)
        all_faq.extend(faq)
        time.sleep(0.3)

    # ===== 去重 =====
    seen = set()
    unique_faq = []
    for faq in all_faq:
        q = faq.get("question", "")
        if q and q not in seen:
            seen.add(q)
            unique_faq.append(faq)

    # ===== 保存 =====
    output = {
        "总数量": len(unique_faq),
        "生成时间": time.strftime("%Y-%m-%d %H:%M:%S"),
        "数据来源": "灵山胜境景点结构化数据集 + 官方历史文化指南",
        "说明": "硬数据来自官方文档，描述进行了适度综合扩展",
        "faq": unique_faq
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # ===== 统计 =====
    print("\n" + "=" * 70)
    print(f"✅ 生成完成！共 {len(unique_faq)} 条FAQ")
    print(f"   保存到: {OUTPUT_FILE}")

    cat_stats = {}
    for faq in unique_faq:
        cat = faq.get("category", "未知")
        cat_stats[cat] = cat_stats.get(cat, 0) + 1

    print("\n📊 类别分布:")
    for cat, count in sorted(cat_stats.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count}条")

    print("\n📝 示例FAQ:")
    for faq in unique_faq[:8]:
        print(f"   ❓ {faq.get('question', '')}")
        print(f"   💬 {faq.get('answer', '')[:50]}...")
        print()


if __name__ == "__main__":
    main()