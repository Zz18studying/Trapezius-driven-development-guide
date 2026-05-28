# -*- coding: utf-8 -*-
"""
构建向量数据库
将FAQ数据转换为向量并存入Chroma

适配新目录结构：
- 输入：data/processed/faq_final.json
- 输出：backend/chroma_db/
"""

import json
import os
import time
import sys
import chromadb
from chromadb.utils import embedding_functions

# ==================== 路径配置 ====================
# 获取脚本所在目录和项目根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# 定义路径
DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
CHROMA_DB_PATH = os.path.join(BACKEND_DIR, "chroma_db")

INPUT_FILE = os.path.join(DATA_PROCESSED, "faq_final.json")

# 确保目录存在
os.makedirs(BACKEND_DIR, exist_ok=True)
os.makedirs(CHROMA_DB_PATH, exist_ok=True)

# ==================== 配置 ====================
# 使用中文嵌入模型（首次运行会自动下载，约120MB）
# 如果下载慢，设置环境变量：set HF_ENDPOINT=https://hf-mirror.com
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

# 初始化Chroma客户端（使用backend目录下的chroma_db）
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# 集合名称
COLLECTION_NAME = "lingshan_faq"

# 删除旧集合（重新构建）
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


# ==================== 加载FAQ数据 ====================
def load_faq_data(file_path):
    """加载FAQ数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 处理不同的JSON格式
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if "faq" in data:
            return data["faq"]
        else:
            return []
    else:
        return []


# ==================== 构建向量库 ====================
def build_vector_store(faq_list):
    """将FAQ存入向量数据库"""

    documents = []
    metadatas = []
    ids = []

    for i, faq in enumerate(faq_list):
        question = faq.get("question", "")
        answer = faq.get("answer", "")
        category = faq.get("category", "通用")

        # 构造检索文本（问题和答案一起，提高检索准确率）
        doc_text = f"问题：{question}\n答案：{answer}"

        documents.append(doc_text)
        metadatas.append({
            "question": question,
            "answer": answer,
            "category": category,
            "index": i
        })
        ids.append(f"faq_{i:04d}")

    # 分批导入（避免一次性导入过多）
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


# ==================== 测试检索 ====================
def test_search():
    """测试检索功能"""
    print("\n" + "=" * 60)
    print("🔍 测试检索功能")
    print("=" * 60)

    test_questions = [
        "灵山大佛有多高？",
        "九龙灌浴几点开始？",
        "门票多少钱？",
        "怎么去灵山胜境？",
        "有轮椅出租吗？",
        "祥符禅寺建于什么时候？",
        "梵宫有什么看点？",
        "适合带孩子去吗？",
    ]

    for question in test_questions:
        print(f"\n❓ {question}")

        results = collection.query(
            query_texts=[question],
            n_results=2
        )

        if results['documents'][0]:
            for j, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][j]
                distance = results['distances'][0][j] if results['distances'] else 0
                similarity = 1 - distance  # 距离越小，相似度越高

                print(f"   结果{j + 1}: [相似度 {similarity:.3f}] {metadata.get('category', '?')}")
                print(f"           问: {metadata.get('question', '')}")
                print(f"           答: {metadata.get('answer', '')[:60]}...")
        else:
            print("   未找到相关结果")


# ==================== 统计信息 ====================
def print_stats(faq_list):
    """打印FAQ统计信息"""
    print("\n" + "=" * 60)
    print("📊 FAQ数据集统计")
    print("=" * 60)

    # 总数
    print(f"   总FAQ数: {len(faq_list)}")

    # 类别分布
    category_stats = {}
    for faq in faq_list:
        cat = faq.get("category", "未知")
        category_stats[cat] = category_stats.get(cat, 0) + 1

    print("\n   类别分布:")
    for cat, count in sorted(category_stats.items(), key=lambda x: -x[1]):
        bar = "█" * (count // 2)
        print(f"      {cat}: {count}条 {bar}")

    # 示例
    print("\n   示例FAQ（前5条）:")
    for i, faq in enumerate(faq_list[:5], 1):
        print(f"      {i}. {faq.get('question', '')}")
        print(f"         → {faq.get('answer', '')[:50]}...")


# ==================== 主函数 ====================
def main():
    print("=" * 60)
    print("灵山胜境 - 向量数据库构建")
    print(f"项目根目录: {PROJECT_ROOT}")
    print("=" * 60)

    # 检查FAQ文件
    print(f"\n📖 检查输入文件: {INPUT_FILE}")
    if not os.path.exists(INPUT_FILE):
        print(f"   ❌ 文件不存在")
        print("   请先运行 scripts/02_generate_faq.py 生成FAQ数据")
        return
    else:
        print(f"   ✅ 文件存在")

    # 加载数据
    print(f"\n📖 加载FAQ数据...")
    faq_list = load_faq_data(INPUT_FILE)
    print(f"   共 {len(faq_list)} 条FAQ")

    if len(faq_list) == 0:
        print("❌ 没有加载到FAQ数据")
        return

    # 打印统计
    print_stats(faq_list)

    # 构建向量库
    print("\n" + "=" * 60)
    print("🚀 开始构建向量数据库")
    print("=" * 60)

    start_time = time.time()
    total = build_vector_store(faq_list)
    elapsed = time.time() - start_time

    print(f"\n⏱️ 构建耗时: {elapsed:.1f} 秒")
    print(f"📊 平均速度: {total / elapsed:.1f} 条/秒")

    # 测试检索
    test_search()

    print("\n" + "=" * 60)
    print("✨ 向量数据库构建完成！")
    print(f"   数据保存在: {CHROMA_DB_PATH}")
    print(f"   集合名称: {COLLECTION_NAME}")
    print("=" * 60)


if __name__ == "__main__":
    main()