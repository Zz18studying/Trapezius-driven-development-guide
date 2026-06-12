# -*- coding: utf-8 -*-
"""
使用 DeepSeek API 生成完整FAQ
- 普通景点：5条
- 核心景点：8-10条
- 通用类别：每类至少10条

适配新目录结构：
- 输入：data/processed/attractions_complete.json
- 输出：data/processed/faq_final.json
"""

import json
import re
import time
import os
from openai import OpenAI

# ==================== 路径配置 ====================
# 获取脚本所在目录和项目根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# 定义路径
DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")
INPUT_FILE = os.path.join(DATA_PROCESSED, "attractions_complete.json")
OUTPUT_FILE = os.path.join(DATA_PROCESSED, "faq_final.json")

# 确保输出目录存在
os.makedirs(DATA_PROCESSED, exist_ok=True)

# ==================== API 配置 ====================
# DeepSeek API 配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-v4-flash"

# 初始化 OpenAI 客户端（兼容 DeepSeek API）
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)


def call_deepseek_api(prompt, temperature=0.7):
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
        print("   请先运行 scripts/01_extract_data.py")
        return None

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ==================== 核心景点列表 ====================
CORE_ATTRACTIONS = [
    "灵山大佛",
    "九龙灌浴",
    "灵山梵宫",
    "五印坛城",
    "祥符禅寺",
    "拈花广场",
    "梵天花海",
    "香月花街",
    "五灯湖"
]


def generate_attraction_faq(attraction, target_count):
    """为景点生成指定数量的FAQ"""

    name = attraction.get('name', '')
    location = attraction.get('location', '')[:150]
    specs = attraction.get('specs', '')[:200]
    culture = attraction.get('culture', '')[:150]
    highlights = attraction.get('highlights', '')[:150]
    hours = attraction.get('hours', '')

    supplement = attraction.get("supplement", {})
    supplement_text = ""
    if supplement:
        supplement_text = f"补充信息：{json.dumps(supplement, ensure_ascii=False)[:300]}"

    prompt = f"""你是灵山胜境景区的AI导游专家。请为「{name}」景点生成{target_count}条游客常见问题。

【景点信息】
名称：{name}
位置：{location}
规格数据：{specs}
文化内涵：{culture}
游玩亮点：{highlights}
开放时间：{hours}
{supplement_text}

【要求】
1. 生成{target_count}条不同的FAQ
2. 问题要口语化、自然（像真实游客问的）
3. 答案要准确，使用上面数据中的具体信息
4. 每条答案控制在35字以内
5. category字段统一为"景点介绍"

【输出格式】
直接输出JSON数组，不要有任何其他文字：
[
  {{"question": "问题1", "answer": "答案1", "category": "景点介绍"}},
  {{"question": "问题2", "answer": "答案2", "category": "景点介绍"}}
]

现在生成{target_count}条FAQ："""

    print(f"      📤 {name} ({target_count}条)...")
    result = call_deepseek_api(prompt)

    if not result:
        print(f"         ❌ API调用失败")
        return []

    faq_list = fix_and_parse_json(result)

    if faq_list and len(faq_list) >= 3:
        print(f"         ✅ 生成 {len(faq_list)} 条")
        return faq_list[:target_count]
    else:
        print(f"         ⚠️ JSON解析失败，返回空列表")
        return []


def generate_general_faq(category_name, category_data, target_count):
    """为通用类别生成FAQ"""

    prompt = f"""你是灵山胜境景区的AI导游专家。请生成关于「{category_name}」的游客常见问题。

【数据信息】
{category_data}

【要求】
- 生成{target_count}条FAQ
- 问题要口语化、多样化（同一信息用不同问法）
- 答案简洁准确（35字以内）
- 必须使用上面数据中的具体信息

【输出格式】
直接输出JSON数组：
[
  {{"question": "问题1", "answer": "答案1", "category": "{category_name}"}},
  {{"question": "问题2", "answer": "答案2", "category": "{category_name}"}}
]

现在生成{target_count}条FAQ："""

    print(f"      📤 {category_name} ({target_count}条)...")
    result = call_deepseek_api(prompt)

    if not result:
        print(f"         ❌ API调用失败")
        return []

    faq_list = fix_and_parse_json(result)

    if faq_list:
        print(f"         ✅ 生成 {len(faq_list)} 条")
        return faq_list[:target_count]
    else:
        print(f"         ⚠️ JSON解析失败，返回空列表")
        return []


def main():
    print("=" * 70)
    print("DeepSeek API - 完整FAQ生成")
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"使用模型: {DEEPSEEK_MODEL}")
    print("核心景点8-10条 | 普通景点5条 | 通用类别10+条")
    print("=" * 70)

    # 检查 API Key
    if DEEPSEEK_API_KEY == "你的API-Key":
        print("\n⚠️ 请先设置 DEEPSEEK_API_KEY 环境变量！")
        print("   或在代码中填入你的API Key")
        return

    # 加载数据
    print(f"\n📖 加载景点数据...")
    attractions = load_attractions()

    if attractions is None:
        return

    print(f"   共 {len(attractions)} 个景点")

    # 分类景点
    core_list = []
    normal_list = []
    for a in attractions:
        name = a.get('name', '')
        if name in CORE_ATTRACTIONS:
            core_list.append(a)
        else:
            normal_list.append(a)

    print(f"\n📋 核心景点 ({len(core_list)}个，每景点8-10条):")
    for a in core_list:
        print(f"   ★ {a.get('name')}")
    print(f"\n📋 普通景点 ({len(normal_list)}个，每景点5条):")
    for a in normal_list:
        print(f"   • {a.get('name')}")

    all_faq = []

    # ==================== 第一部分：核心景点 ====================
    print("\n" + "=" * 70)
    print("第一部分：核心景点（每景点8-10条）")
    print("=" * 70)

    for i, attr in enumerate(core_list, 1):
        print(f"\n[{i}/{len(core_list)}]")
        faq_list = generate_attraction_faq(attr, target_count=10)
        if faq_list:
            all_faq.extend(faq_list)
        time.sleep(0.5)  # API 调用间隔

    # ==================== 第二部分：普通景点 ====================
    print("\n" + "=" * 70)
    print("第二部分：普通景点（每景点5条）")
    print("=" * 70)

    for i, attr in enumerate(normal_list, 1):
        print(f"\n[{i}/{len(normal_list)}]")
        faq_list = generate_attraction_faq(attr, target_count=5)
        if faq_list:
            all_faq.extend(faq_list)
        time.sleep(0.5)

    # ==================== 第三部分：通用类别 ====================
    print("\n" + "=" * 70)
    print("第三部分：通用类别（每类10-12条）")
    print("=" * 70)

    general_categories = [
        ("门票价格",
         "成人210元。学生/60-69岁老人半价105元（凭有效证件）。6岁以下/70岁以上/现役军人/残疾人免票。灵山+拈花湾联票225元。年卡398元全年无限次入园。",
         12),
        ("交通出行",
         "公交：无锡市区乘88路或89路到'灵山胜境'站。自驾：导航'灵山胜境'，走太湖大道或环太湖公路。停车场：小车15元/天，大车30元/天，有充电桩。景区观光车：40元/人，无限次乘坐。出租车：无锡站打车约80元，机场约120元。",
         12),
        ("开放时间",
         "夏季（4-10月）8:00-17:00，冬季（11-3月）8:00-16:30。全年无休，除夕当天可能提前闭园。建议上午9点前入园人少。九龙灌浴表演：平日10:00/11:30/13:30/15:00，周末加场。吉祥颂演出：10:35/11:30/14:00/16:00。",
         12),
        ("餐饮住宿",
         "餐饮：梵宫素斋自助50元/位，素面套餐35元/位，景区内有小吃点和饮料机。住宿：灵山精舍（景区内，800-1500元/晚，含早课体验），马山镇周边有酒店民宿（200-500元/晚）。",
         10),
        ("实用设施",
         "轮椅：游客中心免费租借（押金500元）。婴儿车：30元/天。行李寄存：游客中心免费。洗手间：每个主要景点附近都有，有母婴室。WiFi：搜索'Lingshan-Free'连接。医疗点：游客中心和梵宫。",
         12),
        ("祈福体验",
         "抱佛脚：登顶灵山大佛平台摸佛脚。摸佛手：佛手广场摸'天下第一掌'。转经筒：五印坛城顺时针转动。接圣水：九龙灌浴表演后接取。撞钟：祥符禅寺撞祥符禅钟。",
         10),
        ("游览路线",
         "一日游：灵山大照壁→九龙灌浴→祥符禅寺→灵山大佛→灵山梵宫→五印坛城。亲子路线：九龙灌浴→佛手广场→百子戏弥勒→灵山梵宫。老人路线：坐观光车游览九龙灌浴、梵宫、大佛。深度游：加曼飞龙塔、无尽意斋、佛教文化博览馆。",
         12),
        ("适合人群",
         "老人：有观光车、轮椅租赁、无障碍通道，推荐坐观光车。孩子：喜欢九龙灌浴喷泉和百子戏弥勒互动。年轻人：梵宫和香水海拍照打卡。孕妇：避免爬大佛216级台阶，可乘观光车。外国游客：有英文标识和英文导览。",
         10),
        ("拍照打卡",
         "最佳机位：灵山大佛平台拍全景和太湖，九龙灌浴广场拍喷泉表演，香水海栈道拍梵宫倒影，梵宫内拍星空穹顶和琉璃壁画，五印坛城拍藏式建筑。最佳时间：清晨或傍晚光线最佳，日落时大佛有佛光。可以穿汉服拍照。",
         12),
        ("季节天气",
         "最佳季节：春秋季（3-5月、9-11月）气候宜人。夏天：较热需防晒、多喝水，室内景点有空调。冬天：需穿厚外套，室内景点有空调。雨天：可游览梵宫、佛教文化博览馆、五印坛城等室内景点。",
         10),
        ("历史文化",
         "玄奘渊源：唐贞观年间玄奘取经归来见此山形似印度灵鹫山，命名'小灵山'。祥符禅寺：始建于唐贞观年间（1300多年前），玄奘弟子窥基开坛。赵朴初：中国佛教协会会长，题写'灵山胜境'并推动建设。世界佛教论坛：灵山是永久会址。",
         12),
        ("购物特产",
         "特产：灵山素饼（30-50元/盒）、佛珠手串（20-200元）、香薰（50-150元）、文创书签（15-30元）、灵山禅茶。购物地点：灵山梵宫内商店、香月花街（拈花湾）、各景点纪念品店。",
         10),
    ]

    for cat_name, cat_data, target in general_categories:
        print(f"\n📂 {cat_name}")
        faq_list = generate_general_faq(cat_name, cat_data, target)
        if faq_list:
            all_faq.extend(faq_list)
        time.sleep(0.5)

    # ==================== 去重 ====================
    seen = set()
    unique_faq = []
    for faq in all_faq:
        q = faq.get("question", "")
        if q and q not in seen:
            seen.add(q)
            unique_faq.append(faq)

    # ==================== 保存 ====================
    output = {
        "总数量": len(unique_faq),
        "核心景点数": len(core_list),
        "普通景点数": len(normal_list),
        "通用类别数": len(general_categories),
        "生成时间": time.strftime("%Y-%m-%d %H:%M:%S"),
        "模型": DEEPSEEK_MODEL,
        "api_type": "DeepSeek API",
        "faq": unique_faq
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # ==================== 统计输出 ====================
    print("\n" + "=" * 70)
    print("✅ 生成完成！")
    print("=" * 70)
    print(f"   总FAQ数: {len(unique_faq)} 条")
    print(f"   核心景点: {len(core_list)}个 × 8-10条")
    print(f"   普通景点: {len(normal_list)}个 × 5条")
    print(f"   通用类别: {len(general_categories)}类 × 10-12条")
    print(f"   保存到: {OUTPUT_FILE}")

    # 类别统计
    cat_stats = {}
    for faq in unique_faq:
        cat = faq.get("category", "未知")
        cat_stats[cat] = cat_stats.get(cat, 0) + 1

    print("\n📊 类别分布:")
    for cat, count in sorted(cat_stats.items(), key=lambda x: -x[1]):
        bar = "█" * (count // 2)
        print(f"   {cat}: {count}条 {bar}")

    print("\n📝 示例FAQ（前15条）:")
    for i, faq in enumerate(unique_faq[:15], 1):
        print(f"   {i}. [{faq.get('category', '')}] {faq.get('question', '')}")
        print(f"      → {faq.get('answer', '')[:55]}")


if __name__ == "__main__":
    main()