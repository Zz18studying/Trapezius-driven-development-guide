# -*- coding: utf-8 -*-
"""
构建向量数据库 - 使用本地嵌入模型
"""

import json
import os
import time
import chromadb
from chromadb.utils import embedding_functions

# ==================== 路径配置 ====================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
CHROMA_DB_PATH = os.path.join(BACKEND_DIR, "chroma_db")
INPUT_FILE = os.path.join(DATA_PROCESSED, "faq_final.json")

# 本地模型路径
LOCAL_MODEL_PATH = "/home/ubuntu/.cache/sentence-transformers/local_model"

# 确保目录存在
os.makedirs(BACKEND_DIR, exist_ok=True)
os.makedirs(CHROMA_DB_PATH, exist_ok=True)

# 集合名称
COLLECTION_NAME = "lingshan_faq"

print("=" * 60)
print("灵山胜境 - 向量数据库构建")
print("=" * 60)

# 检查模型是否存在
if not os.path.exists(LOCAL_MODEL_PATH):
    print(f"❌ 本地模型不存在: {LOCAL_MODEL_PATH}")
    print("   请先下载模型到该路径")
    exit(1)

print(f"✅ 使用本地模型: {LOCAL_MODEL_PATH}")

# 使用本地嵌入模型
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=LOCAL_MODEL_PATH
)

# 初始化 Chroma 客户端
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# 删除旧集合
try:
    chroma_client.delete_collection(COLLECTION_NAME)
    print("🔄 已删除旧的知识库")
except:
    pass

# 创建新集合
collection = chroma_client.create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_fn
)

print("✅ 已创建向量数据库集合")
print(f"   数据库路径: {CHROMA_DB_PATH}")


def load_faq_data(file_path):
    """加载FAQ数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if "faq" in data:
            return data["faq"]
        else:
            return []
    else:
        return []


def build_vector_store(faq_list):
    """将FAQ存入向量数据库"""
    documents = []
    metadatas = []
    ids = []

    for i, faq in enumerate(faq_list):
        question = faq.get("question", "")
        answer = faq.get("answer", "")
        category = faq.get("category", "通用")

        doc_text = f"问题：{question}\n答案：{answer}"

        documents.append(doc_text)
        metadatas.append({
             "type": "faq", 
            "question": question,
            "answer": answer,
            "category": category,
            "index": i
        })
        ids.append(f"faq_{i:04d}")

    batch_size = 100
    total = len(documents)

    print(f"\n💾 正在存入向量数据库（共{total}条）...")

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        collection.add(
            documents=documents[start:end],
            metadatas=metadatas[start:end],
            ids=ids[start:end]
        )
        print(f"   已存入 {end}/{total} 条")

    print(f"\n✅ 成功存入 {total} 条知识")
    return total


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"\n❌ 文件不存在: {INPUT_FILE}")
        print("   请先运行 scripts/02_generate_faq.py 生成FAQ数据")
        return

    print(f"\n📖 加载FAQ数据: {INPUT_FILE}")
    faq_list = load_faq_data(INPUT_FILE)
    print(f"   共 {len(faq_list)} 条FAQ")

    if len(faq_list) == 0:
        print("❌ 没有加载到FAQ数据")
        return

    start_time = time.time()
    total = build_vector_store(faq_list)
    elapsed = time.time() - start_time

    print(f"\n⏱️ 构建耗时: {elapsed:.1f} 秒")
    print(f"📊 平均速度: {total / elapsed:.1f} 条/秒")

    print("\n✨ 向量数据库构建完成！")


if __name__ == "__main__":
    main()
