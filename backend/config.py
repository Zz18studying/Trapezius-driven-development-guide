# -*- coding: utf-8 -*-
"""
后端配置文件
"""

import os

# 项目路径
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

# 向量数据库路径
CHROMA_DB_PATH = os.path.join(BACKEND_DIR, "chroma_db")
COLLECTION_NAME = "lingshan_faq"

# 大模型配置（本地Ollama）- 用于主模型的备用（/api/generate 接口）
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "deepseek-r1:7b"

# ==================== DeepSeek API 配置 ====================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-v4-flash"

# ==================== 验证模型配置 ====================
# 验证提供商选择: "ollama" 或 "deepseek"
# 本地开发用 "ollama"，云端部署切换到 "deepseek"
VERIFIER_PROVIDER = os.environ.get("VERIFIER_PROVIDER", "deepseek")  # 默认使用deepseek

# ----- Ollama 配置 (本地验证) -----
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_VERIFIER_MODEL = "qwen2:1.5b"

# ----- DeepSeek API 配置 (云端验证) -----
# 验证模型可以使用与主模型相同，也可以单独指定更便宜的版本
DEEPSEEK_VERIFIER_MODEL = os.environ.get("DEEPSEEK_VERIFIER_MODEL", "deepseek-v4-flash")
# 验证 API 复用主模型的 Key 和 Base URL

# ----- 通用验证配置 -----
# 最小一致性得分，低于此分数的句子将被丢弃
MIN_CONSISTENCY_SCORE = 0.8
# 是否强制要求验证通过才返回
REQUIRE_VERIFICATION = True

# ==================== 检索配置 ====================
DEFAULT_N_RESULTS = 5
MAX_N_RESULTS = 10
MIN_SIMILARITY = 0.35# 采用更严谨的阈值
FALLBACK_SIMILARITY = 0.25  # 宽松重试阈值，当标准阈值无结果时使用

# ==================== API配置 ====================
API_TITLE = "灵山胜境AI导游API"
API_VERSION = "1.0.0"
API_HOST = "0.0.0.0"
API_PORT = 8000

# ==================== 个性化推荐配置 ====================
# 路线定义
ROUTES = {
    "历史文化": {
        "name": "历史文化深度游",
        "duration": "约6小时",
        "spots": ["灵山大照壁", "祥符禅寺", "灵山大佛", "灵山梵宫", "五印坛城"],
        "description": "深度体验灵山胜境的佛教文化与历史底蕴，适合对佛教历史感兴趣的游客。",
        "highlights": "参观千年古刹祥符禅寺，欣赏梵宫艺术瑰宝，登顶抱佛脚"
    },
    "自然风光": {
        "name": "自然风光休闲游",
        "duration": "约5小时",
        "spots": ["九龙灌浴", "菩提大道", "灵山大佛", "曼飞龙塔", "香水海"],
        "description": "欣赏太湖之滨的自然风光与园林景观，适合喜欢拍照和放松的游客。",
        "highlights": "观看九龙灌浴喷泉表演，漫步菩提大道，香水海拍照打卡"
    },
    "亲子家庭": {
        "name": "亲子家庭欢乐游",
        "duration": "约4小时",
        "spots": ["九龙灌浴", "佛手广场", "百子戏弥勒", "灵山梵宫"],
        "description": "轻松有趣的亲子游览路线，适合带孩子的家庭。",
        "highlights": "九龙灌浴喷泉互动，百子戏弥勒趣味打卡，梵宫奇幻体验"
    },
    "祈福体验": {
        "name": "祈福静心之旅",
        "duration": "约5小时",
        "spots": ["祥符禅寺", "灵山大佛", "五印坛城", "佛手广场"],
        "description": "以祈福、静心、禅修为主题，适合希望寻求内心平静的游客。",
        "highlights": "祥符禅寺撞钟祈福，登顶抱佛脚，五印坛城转经筒"
    },
    "摄影打卡": {
        "name": "摄影打卡精选游",
        "duration": "约5小时",
        "spots": ["灵山大佛", "灵山梵宫", "香水海", "九龙灌浴", "曼飞龙塔"],
        "description": "精选灵山胜境最佳拍摄机位，适合摄影爱好者和打卡达人。",
        "highlights": "大佛平台全景，梵宫星空穹顶，香水海倒影"
    }
}

# 兴趣关键词 → 路线映射
INTEREST_TO_ROUTE = {
    "历史": "历史文化",
    "文化": "历史文化",
    "佛教": "历史文化",
    "古迹": "历史文化",
    "自然": "自然风光",
    "风光": "自然风光",
    "风景": "自然风光",
    "拍照": "摄影打卡",
    "摄影": "摄影打卡",
    "打卡": "摄影打卡",
    "亲子": "亲子家庭",
    "小孩": "亲子家庭",
    "孩子": "亲子家庭",
    "家庭": "亲子家庭",
    "祈福": "祈福体验",
    "拜佛": "祈福体验",
    "禅修": "祈福体验",
    "静心": "祈福体验"
}


