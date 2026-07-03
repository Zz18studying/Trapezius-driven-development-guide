# -*- coding: utf-8 -*-
"""
构建向量数据库。

同时索引 FAQ 和原文知识块，保证口语问题与原文知识都可被检索到。
"""

import json
import os
import sys
import time
import chromadb
from chromadb.utils import embedding_functions


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
CHROMA_DB_PATH = os.path.join(BACKEND_DIR, "chroma_db")
FAQ_FILE = os.path.join(DATA_PROCESSED, "faq_final.json")
KNOWLEDGE_FILE = os.path.join(DATA_PROCESSED, "knowledge_units.json")
COLLECTION_NAME = "lingshan_faq"

LOCAL_MODEL_CANDIDATES = [
    "/home/ubuntu/.cache/sentence-transformers/local_model",
    os.path.join(os.path.expanduser("~"), ".cache", "sentence-transformers", "local_model"),
]

sys.path.insert(0, BACKEND_DIR)
from services.local_embedding import SimpleChineseEmbeddingFunction


def load_json(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_embedding_function():
    for model_path in LOCAL_MODEL_CANDIDATES:
        if os.path.exists(model_path):
            print(f"使用本地嵌入模型: {model_path}")
            return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_path)

    print("未找到本地 sentence-transformers 模型，使用离线中文 n-gram 向量兜底。")
    print("服务器部署时如果已有 /home/ubuntu/.cache/sentence-transformers/local_model，会自动优先使用。")
    return SimpleChineseEmbeddingFunction()


def load_faq_records() -> list:
    data = load_json(FAQ_FILE)
    faq_list = data.get("faq", data if isinstance(data, list) else [])
    records = []
    for index, faq in enumerate(faq_list, 1):
        question = faq.get("question", "")
        answer = faq.get("answer", "")
        if not question or not answer:
            continue
        records.append({
            "id": faq.get("id") or f"faq_{index:04d}",
            "document": f"问题：{question}\n答案：{answer}",
            "metadata": {
                "type": "faq",
                "question": question,
                "answer": answer,
                "category": faq.get("category", "通用知识"),
                "source": faq.get("source", ""),
                "source_type": faq.get("source_type", ""),
                "source_attraction": faq.get("source_attraction", ""),
                "attraction_name": faq.get("attraction_name", ""),
            }
        })
    return records


def load_knowledge_records() -> list:
    units = load_json(KNOWLEDGE_FILE)
    records = []
    for index, unit in enumerate(units, 1):
        title = unit.get("title", "")
        content = unit.get("content", "")
        if not content:
            continue
        question = title if title.endswith(("？", "?")) else f"{title}是什么？"
        answer = content
        records.append({
            "id": unit.get("id") or f"ku_{index:04d}",
            "document": f"标题：{title}\n内容：{content}",
            "metadata": {
                "type": "knowledge",
                "question": question,
                "answer": answer,
                "category": unit.get("category", "通用知识"),
                "source": unit.get("source_file", ""),
                "source_type": unit.get("source_type", ""),
                "source_attraction": unit.get("source_attraction", ""),
                "attraction_name": unit.get("attraction_name", ""),
            }
        })
    return records


def recreate_collection(client, embedding_fn):
    try:
        client.delete_collection(COLLECTION_NAME)
        print("已删除旧知识库集合。")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn
    )
    print(f"已创建集合: {COLLECTION_NAME}")
    return collection


def add_records(collection, records: list, batch_size: int = 100):
    total = len(records)
    for start in range(0, total, batch_size):
        batch = records[start:start + batch_size]
        collection.add(
            ids=[item["id"] for item in batch],
            documents=[item["document"] for item in batch],
            metadatas=[item["metadata"] for item in batch],
        )
        print(f"已写入 {min(start + batch_size, total)}/{total}")


def main():
    print("=" * 70)
    print("灵山胜境向量数据库构建")
    print("=" * 70)
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)

    faq_records = load_faq_records()
    knowledge_records = load_knowledge_records()
    records = faq_records + knowledge_records

    print(f"FAQ 记录: {len(faq_records)}")
    print(f"原文知识块: {len(knowledge_records)}")
    print(f"总入库记录: {len(records)}")
    if not records:
        raise RuntimeError("没有可入库数据，请先运行 01 和 02 脚本。")

    start = time.time()
    embedding_fn = get_embedding_function()
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = recreate_collection(client, embedding_fn)
    add_records(collection, records)

    elapsed = time.time() - start
    print(f"构建完成，集合条目数: {collection.count()}")
    print(f"数据库路径: {CHROMA_DB_PATH}")
    print(f"耗时: {elapsed:.1f} 秒")


if __name__ == "__main__":
    main()
