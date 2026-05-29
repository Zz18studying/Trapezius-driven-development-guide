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

# 大模型配置（本地Ollama）- 保留作为备用
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "deepseek-r1:7b"

# ==================== DeepSeek API 配置 ====================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-v4-flash"

# 检索配置
DEFAULT_N_RESULTS = 5
MAX_N_RESULTS = 10
MIN_SIMILARITY = 0.3

# API配置
API_TITLE = "灵山胜境AI导游API"
API_VERSION = "1.0.0"
API_HOST = "0.0.0.0"
API_PORT = 8000