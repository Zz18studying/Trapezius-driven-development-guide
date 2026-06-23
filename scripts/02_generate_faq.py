# -*- coding: utf-8 -*-
"""
使用 DeepSeek API 生成完整FAQ - 基于官方数据集
数据来源：
1. 灵山胜境 景点结构化数据集.docx（景点数据）
2. 灵山胜境：历史、文化、景点特色与个性化游览指南.docx（历史、文化、路线、实用信息）
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
    """调用 DeepSeek API，使用低温度保证输出稳定"""
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
    """加载景点数据（来自文档一）"""
    if not os.path.exists(INPUT_FILE):
        print(f"   ❌ 文件不存在: {INPUT_FILE}")
        print("   请先运行 scripts/01_extract_and_merge_data.py")
        return None
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ==================== 核心景点列表 ====================
CORE_ATTRACTIONS = [
    "灵山大佛", "九龙灌浴", "灵山梵宫", "五印坛城", "祥符禅寺",
    "拈花广场", "梵天花海", "香月花街", "五灯湖"
]


# ==================== 第一部分：景点FAQ ====================
def generate_attraction_faq(attraction, target_count):
    """为单个景点生成FAQ - 基于文档一的结构化数据"""
    name = attraction.get('name', '')
    location = attraction.get('location', '')[:150]
    specs = attraction.get('specs', '')[:250]
    culture = attraction.get('culture', '')[:200]
    highlights = attraction.get('highlights', '')[:200]
    hours = attraction.get('hours', '')
    details = attraction.get('details', '')[:200]
    function = attraction.get('function', '')[:150]

    supplement = attraction.get("supplement", {})
    supplement_text = ""
    if supplement:
        supplement_text = f"补充信息：{json.dumps(supplement, ensure_ascii=False)[:300]}"

    prompt = f"""你是灵山胜境景区的AI导游专家。请为「{name}」景点生成{target_count}条游客常见问题。

【景点信息】（全部来自官方数据集，请严格使用以下数据）
名称：{name}
位置：{location}
建筑/景观参数：{specs}
文化内涵：{culture}
游玩亮点：{highlights}
开放时间：{hours}
详细介绍：{details}
功能用途：{function}
{supplement_text}

【要求】
1. 生成{target_count}条不同的FAQ，覆盖以下类型：
   - 概述性（2条）：{name}有什么特色/看点/值得去吗
   - 事实性（2条）：{name}的具体数据
   - 体验性（2条）：去{name}可以做什么/怎么玩
   - 文化性（2条）：{name}有什么文化内涵/历史故事
   - 实用性（2条）：去{name}需要注意什么/最佳时间

2. 问题要口语化、自然
3. 答案必须使用上面数据中的具体信息，不捏造
4. 每条答案30-50字
5. category根据类型设置：景点概述/景点数据/游玩体验/文化历史/实用贴士

【输出格式】
直接输出JSON数组"""
    print(f"      📤 {name} ({target_count}条)...")
    result = call_deepseek_api(prompt)
    if not result:
        return []
    faq_list = fix_and_parse_json(result)
    if faq_list and len(faq_list) >= 3:
        print(f"         ✅ 生成 {len(faq_list)} 条")
        return faq_list[:target_count]
    print(f"         ⚠️ JSON解析失败")
    return []


# ==================== 第二部分：历史文化FAQ（来自文档二） ====================
def generate_history_faq():
    """生成历史文化相关FAQ - 基于文档二的千年历史渊源"""
    history_data = """
【灵山胜境的历史渊源】

小灵山的佛教缘起：
唐贞观年间（1300多年前），玄奘法师西行取经归来，途经马山时，见此地"层峦丛翠，曲水净秀，山形酷似印度灵鹫山"，遂将所译《大般若经》中的"灵鹫胜境"之名赐予此地，命名为"小灵山"，并嘱咐大弟子窥基法师在此住持道场，兴建小灵山庵。

祥符禅寺的千年兴衰：
小灵山庵历经数百年发展，至北宋大中祥符年间（1008-1016年），宋真宗赵恒赐额"祥符禅寺"。南宋时曾遭兵燹，元代重建；明代达到鼎盛；清末民初再次毁于战火，仅存一棵千年银杏、一口六角古井和一段残垣断壁。

现代灵山胜境的崛起：
- 1994年：修复祥符禅寺、建造灵山大佛工程奠基
- 1997年11月15日：灵山大佛落成开光
- 2003年：二期工程九龙灌浴建成
- 2009年：灵山梵宫正式开放，成为世界佛教论坛永久会址

【佛教文化】
赵朴初提出"五方五佛"之论：灵山大佛、香港天坛大佛、四川乐山大佛、山西云冈大佛、河南龙门大佛。
灵山胜境融合汉传与藏传佛教文化，曼飞龙塔代表南传佛教，三大语系齐聚。
"""
    prompt = f"""你是灵山胜境景区的AI导游专家。请根据以下历史信息生成FAQ。

【历史信息】（全部来自官方指南文档，请严格使用以下数据）
{history_data}

【要求】
1. 生成15-18条历史文化FAQ
2. 覆盖：玄奘命名小灵山、祥符禅寺千年历史、灵山大佛建造历程、五方五佛理念
3. 问题要口语化，如"灵山为什么叫小灵山""祥符禅寺有多少年历史"
4. 答案必须使用上面数据中的具体信息，不捏造
5. category统一为"历史文化"

【输出格式】
直接输出JSON数组"""
    print(f"      📤 历史文化FAQ...")
    result = call_deepseek_api(prompt, temperature=0.2)
    if not result:
        return []
    faq_list = fix_and_parse_json(result)
    if faq_list:
        print(f"         ✅ 生成 {len(faq_list)} 条")
        return faq_list
    return []


# ==================== 第三部分：游览路线FAQ（来自文档二） ====================
def generate_route_faq():
    """生成游览路线FAQ - 基于文档二的个性化路线推荐"""
    route_data = """
【历史文化爱好者路线】6小时深度游
路线：南门→灵山大照壁→胜境广场→佛手广场→祥符禅寺→杏坛广场→佛前广场→灵山大佛→灵山梵宫→五印坛城→三圣殿→出口
讲解重点：玄奘法师与"小灵山"渊源、祥符禅寺千年兴衰、灵山大佛手印含义、梵宫艺术瑰宝、汉藏佛教对比

【自然风光爱好者路线】5小时全景游
路线：南门→佛足坛→九龙灌浴→菩提大道→灵山大佛→曼飞龙塔→灵山精舍→梵宫广场→出口
讲解重点：菩提大道的佛教文化意义、大佛选址的地理优势、曼飞龙塔的傣族建筑风格、灵山精舍的禅意园林

【亲子家庭路线】4小时轻松游
路线：南门→九龙灌浴→佛手广场→百子戏弥勒→梵宫→五印坛城→出口
讲解重点：用生动语言讲述释迦牟尼诞生故事、百子戏弥勒的生活百态、梵宫色彩造型的直观艺术

【特色体验】
- 祥符禅寺撞钟祈福（12.8吨江南第一钟）
- 梵宫《吉祥颂》演出（10:35/11:30/14:00/16:00）
- 灵山大佛平台俯瞰太湖日落
- 五印坛城转经筒祈福
- 抱佛脚亲子活动
"""
    prompt = f"""你是灵山胜境景区的AI导游专家。请根据以下路线信息生成FAQ。

【路线信息】（全部来自官方指南文档，请严格使用以下数据）
{route_data}

【要求】
1. 生成12-15条游览路线FAQ
2. 覆盖：历史文化路线、自然风光路线、亲子路线、特色体验
3. 问题要口语化，如"历史文化爱好者怎么玩""带孩子怎么逛灵山"
4. 答案必须使用上面数据中的具体信息，不捏造
5. category统一为"游玩建议"

【输出格式】
直接输出JSON数组"""
    print(f"      📤 游览路线FAQ...")
    result = call_deepseek_api(prompt, temperature=0.2)
    if not result:
        return []
    faq_list = fix_and_parse_json(result)
    if faq_list:
        print(f"         ✅ 生成 {len(faq_list)} 条")
        return faq_list
    return []


# ==================== 第四部分：实用贴士FAQ（来自文档二） ====================
def generate_practical_faq():
    """生成实用贴士FAQ - 基于文档二的实用游览贴士"""
    practical_data = """
【门票价格】
- 成人票：210元
- 半价票：105元（6-18周岁未成年人、全日制本科及以下学生、60-69周岁老人）
- 免票：6周岁以下或1.4米以下儿童、70周岁以上老人、现役军人、残疾人
- 网购联票：225元（门票+观光车）

【最佳游览时间】
- 春秋季节（3-5月、9-11月）气候宜人
- 建议上午9点前入园避开人流高峰
- 九龙灌浴表演每日4-5场
- 《吉祥颂》演出：10:35、11:30、14:00、16:00

【餐饮住宿】
餐饮：梵宫素斋自助50元/位、素面套餐35元/位
住宿：灵山精舍800-1500元/晚（含素斋与早课）、周边酒店200-500元/晚

【其他建议】
- 穿着舒适运动鞋，景区需步行较多
- 景区提供导游讲解服务，300元起
- 文明游览，保持安静，尊重宗教信仰
- 夏季防晒、冬季保暖
"""
    prompt = f"""你是灵山胜境景区的AI导游专家。请根据以下实用信息生成FAQ。

【实用信息】（全部来自官方指南文档，请严格使用以下数据）
{practical_data}

【要求】
1. 生成12-15条实用贴士FAQ
2. 覆盖：门票价格与优惠政策、最佳游览时间、餐饮住宿、游览建议
3. 问题要口语化，如"灵山胜境门票多少钱""老人有优惠吗"
4. 答案必须使用上面数据中的具体信息，不捏造
5. category统一为"实用信息"

【输出格式】
直接输出JSON数组"""
    print(f"      📤 实用贴士FAQ...")
    result = call_deepseek_api(prompt, temperature=0.2)
    if not result:
        return []
    faq_list = fix_and_parse_json(result)
    if faq_list:
        print(f"         ✅ 生成 {len(faq_list)} 条")
        return faq_list
    return []


# ==================== 第五部分：场景化FAQ ====================
def generate_scenario_faq():
    """生成场景化FAQ - 基于文档二的路线信息"""
    scenarios = [
        ("亲子游", "推荐亲子路线：九龙灌浴→佛手广场→百子戏弥勒→灵山梵宫。亮点：喷泉互动、趣味打卡、奇幻体验，适合带孩子游玩。"),
        ("老人游", "推荐老人路线：坐观光车游览九龙灌浴→祥符禅寺→灵山大佛→灵山梵宫。有轮椅租赁和无障碍通道。"),
        ("雨天", "推荐雨天路线：灵山梵宫→佛教文化博览馆→五印坛城→无尽意斋。全部为室内景点。"),
        ("情侣", "推荐情侣路线：香水海→灵山大佛→灵山梵宫→五印坛城。适合拍照打卡，感受浪漫禅意。"),
        ("深度游", "推荐深度游：灵山大照壁→祥符禅寺→灵山大佛→灵山梵宫→五印坛城→曼飞龙塔。6小时全面感受佛教文化。"),
        ("快速游", "推荐快速游：灵山大佛→九龙灌浴→灵山梵宫。2-3小时逛完核心景点。"),
        ("拍照打卡", "最佳打卡点：大佛平台全景、香水海栈道梵宫倒影、梵宫穹顶、九龙灌浴广场。清晨或傍晚光线最佳。"),
        ("祈福", "祈福路线：祥符禅寺撞钟→灵山大佛抱佛脚→五印坛城转经筒→佛手广场摸佛手。"),
    ]
    faq_list = []
    for name, content in scenarios:
        faq_list.append({"question": f"灵山胜境{name}怎么玩？", "answer": content[:200], "category": "游玩建议"})
        faq_list.append({"question": f"灵山胜境{name}推荐路线", "answer": content[:200], "category": "游玩建议"})
    return faq_list


# ==================== 第六部分：概述性FAQ ====================
def generate_overview_faq(attractions):
    """为每个景点生成概述性FAQ - 基于文档一的数据"""
    overview_faq = []
    for attr in attractions:
        name = attr.get('name', '')
        specs = attr.get('specs', '')[:200]
        culture = attr.get('culture', '')[:150]
        highlights = attr.get('highlights', '')[:150]
        details = attr.get('details', '')[:150]

        if not name:
            continue

        prompt = f"""为景点「{name}」生成4条概述性FAQ。

【景点信息】（来自官方数据集）
名称：{name}
规格数据：{specs}
文化内涵：{culture}
游玩亮点：{highlights}
详细描述：{details}

【必须包含以下4个问题】
1. {name}有什么特色？
2. {name}有什么看点？
3. {name}值得去吗？
4. {name}有什么好玩的？

【要求】
- 答案必须使用上面数据中的具体信息
- 每条答案30-50字
- category统一为"景点概述"

输出JSON数组："""
        print(f"      📤 概述FAQ: {name}")
        result = call_deepseek_api(prompt, temperature=0.2)
        if result:
            faq_list = fix_and_parse_json(result)
            if faq_list:
                overview_faq.extend(faq_list)
        time.sleep(0.3)
    return overview_faq


# ==================== 第七部分：通用类别FAQ ====================
def generate_general_faq(category_name, category_data, target_count):
    """为通用类别生成FAQ"""
    prompt = f"""生成关于「{category_name}」的FAQ。

【数据】（来自官方指南文档）
{category_data}

要求：
- {target_count}条FAQ
- 问题口语化
- 答案简洁准确
- category为"{category_name}"

输出JSON数组："""
    print(f"      📤 {category_name} ({target_count}条)...")
    result = call_deepseek_api(prompt, temperature=0.3)
    if not result:
        return []
    faq_list = fix_and_parse_json(result)
    if faq_list:
        print(f"         ✅ 生成 {len(faq_list)} 条")
        return faq_list[:target_count]
    return []


# ==================== 主函数 ====================
def main():
    print("=" * 70)
    print("DeepSeek API - 官方数据集FAQ生成")
    print("数据来源：灵山胜境景点结构化数据集 + 历史文化指南")
    print("覆盖：景点介绍 | 历史文化 | 游览路线 | 实用贴士 | 场景化")
    print("=" * 70)

    if DEEPSEEK_API_KEY == "你的API-Key":
        print("\n⚠️ 请先设置 DEEPSEEK_API_KEY 环境变量！")
        print("   export DEEPSEEK_API_KEY=你的API-Key")
        return

    attractions = load_attractions()
    if attractions is None:
        return

    print(f"\n📖 加载 {len(attractions)} 个景点")

    core_list = [a for a in attractions if a.get('name') in CORE_ATTRACTIONS]
    normal_list = [a for a in attractions if a.get('name') not in CORE_ATTRACTIONS]
    all_attractions = core_list + normal_list

    all_faq = []

    # ===== 第一部分：景点FAQ =====
    print("\n" + "=" * 70)
    print("第一部分：景点FAQ（基于文档一结构化数据）")
    print("=" * 70)
    for attr in core_list:
        faq_list = generate_attraction_faq(attr, 10)
        if faq_list:
            all_faq.extend(faq_list)
        time.sleep(0.5)

    for attr in normal_list:
        faq_list = generate_attraction_faq(attr, 8)
        if faq_list:
            all_faq.extend(faq_list)
        time.sleep(0.5)

    # ===== 第二部分：概述性FAQ =====
    print("\n" + "=" * 70)
    print("第二部分：概述性FAQ（每个景点4条）")
    print("=" * 70)
    overview = generate_overview_faq(all_attractions)
    all_faq.extend(overview)

    # ===== 第三部分：历史文化FAQ =====
    print("\n" + "=" * 70)
    print("第三部分：历史文化FAQ（基于文档二）")
    print("=" * 70)
    history = generate_history_faq()
    all_faq.extend(history)

    # ===== 第四部分：游览路线FAQ =====
    print("\n" + "=" * 70)
    print("第四部分：游览路线FAQ（基于文档二）")
    print("=" * 70)
    routes = generate_route_faq()
    all_faq.extend(routes)

    # ===== 第五部分：实用贴士FAQ =====
    print("\n" + "=" * 70)
    print("第五部分：实用贴士FAQ（基于文档二）")
    print("=" * 70)
    practical = generate_practical_faq()
    all_faq.extend(practical)

    # ===== 第六部分：场景化FAQ =====
    print("\n" + "=" * 70)
    print("第六部分：场景化FAQ")
    print("=" * 70)
    scenario = generate_scenario_faq()
    all_faq.extend(scenario)

    # ===== 第七部分：通用类别FAQ =====
    print("\n" + "=" * 70)
    print("第七部分：通用类别FAQ")
    print("=" * 70)
    general_categories = [
        ("门票价格", "成人210元。学生/60-69岁老人半价105元。6岁以下/70岁以上免票。联票225元含观光车。", 8),
        ("开放时间", "夏季8:00-17:00，冬季8:00-16:30。九龙灌浴平日10:00/11:30/13:30/15:00。", 8),
        ("交通出行", "公交88/89路。自驾走太湖大道。停车场15元/天。观光车40元/人。", 8),
        ("餐饮住宿", "梵宫素斋50元。灵山精舍800-1500元。马山镇酒店200-500元。", 8),
        ("实用设施", "轮椅免费租借。婴儿车30元/天。行李寄存免费。母婴室。WiFi。", 8),
        ("购物特产", "灵山素饼、佛珠手串、香薰、文创书签、禅茶。梵宫商店可购。", 8),
    ]
    for cat_name, cat_data, target in general_categories:
        faq_list = generate_general_faq(cat_name, cat_data, target)
        if faq_list:
            all_faq.extend(faq_list)
        time.sleep(0.5)

    # ===== 去重与保存 =====
    seen = set()
    unique_faq = []
    for faq in all_faq:
        q = faq.get("question", "")
        if q and q not in seen:
            seen.add(q)
            unique_faq.append(faq)

    output = {
        "总数量": len(unique_faq),
        "生成时间": time.strftime("%Y-%m-%d %H:%M:%S"),
        "数据来源": "灵山胜境景点结构化数据集 + 历史文化指南",
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

    print("\n📝 FAQ示例（前10条）:")
    for i, faq in enumerate(unique_faq[:10], 1):
        print(f"   {i}. [{faq.get('category', '')}] {faq.get('question', '')}")
        print(f"      → {faq.get('answer', '')[:50]}...")


if __name__ == "__main__":
    main()