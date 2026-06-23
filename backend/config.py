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
MIN_SIMILARITY = 0.6  # 采用更严谨的阈值

# ==================== API配置 ====================
API_TITLE = "灵山胜境AI导游API"
API_VERSION = "1.0.0"
API_HOST = "0.0.0.0"
API_PORT = 8000