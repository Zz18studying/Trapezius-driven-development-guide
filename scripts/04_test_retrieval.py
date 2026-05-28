# -*- coding: utf-8 -*-
"""
测试向量数据库检索功能
独立测试脚本，用于验证检索效果

使用方式：
    python scripts/04_test_retrieval.py
    python scripts/04_test_retrieval.py --question "灵山大佛有多高？"
    python scripts/04_test_retrieval.py --interactive
"""

import os
import sys
import argparse
import chromadb

# ==================== 路径配置 ====================
# 获取脚本所在目录和项目根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# 向量数据库路径
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, "backend", "chroma_db")
COLLECTION_NAME = "lingshan_faq"


# ==================== 连接数据库 ====================
def get_collection():
    """获取向量数据库集合"""
    if not os.path.exists(CHROMA_DB_PATH):
        print(f"❌ 向量数据库不存在: {CHROMA_DB_PATH}")
        print("   请先运行 scripts/03_build_vector_db.py 构建数据库")
        return None

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    try:
        collection = client.get_collection(COLLECTION_NAME)
        print(f"✅ 已连接到向量数据库")
        print(f"   数据库路径: {CHROMA_DB_PATH}")
        print(f"   集合名称: {COLLECTION_NAME}")
        return collection
    except Exception as e:
        print(f"❌ 无法获取集合: {e}")
        return None


# ==================== 单问题测试 ====================
def test_single_question(collection, question, n_results=5):
    """测试单个问题"""
    print(f"\n{'='*60}")
    print(f"❓ 问题: {question}")
    print(f"{'='*60}")

    results = collection.query(
        query_texts=[question],
        n_results=n_results
    )

    if results['documents'] and results['documents'][0]:
        print(f"\n📚 检索结果 (共 {len(results['documents'][0])} 条):")
        print("-" * 50)

        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            similarity = 1 - distance
            # 根据相似度设置标记
            if similarity > 0.8:
                flag = "✅ 高相关"
            elif similarity > 0.6:
                flag = "📌 中相关"
            else:
                flag = "⚠️ 低相关"

            print(f"\n   [{i+1}] {flag} | 相似度: {similarity:.4f}")
            print(f"       类别: {metadata.get('category', '未知')}")
            print(f"       问题: {metadata.get('question', '')}")
            print(f"       答案: {metadata.get('answer', '')[:80]}...")

        return results
    else:
        print("   ❌ 未找到相关结果")
        return None


# ==================== 批量测试 ====================
def test_batch(collection, questions, n_results=3):
    """批量测试多个问题"""
    print("\n" + "=" * 70)
    print("📋 批量测试")
    print("=" * 70)

    results_summary = []

    for i, question in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}] ❓ {question}")

        results = collection.query(
            query_texts=[question],
            n_results=n_results
        )

        if results['documents'] and results['documents'][0]:
            top_result = results['documents'][0][0]
            top_metadata = results['metadatas'][0][0]
            top_distance = results['distances'][0][0]
            similarity = 1 - top_distance

            results_summary.append({
                "question": question,
                "found": True,
                "top_question": top_metadata.get('question', ''),
                "top_answer": top_metadata.get('answer', '')[:60],
                "similarity": similarity
            })

            print(f"   ✅ 找到: {top_metadata.get('question', '')[:50]}... (相似度: {similarity:.3f})")
        else:
            results_summary.append({
                "question": question,
                "found": False,
                "top_question": "",
                "top_answer": "",
                "similarity": 0
            })
            print(f"   ❌ 未找到相关结果")

    return results_summary


# ==================== 交互式测试 ====================
def interactive_test(collection):
    """交互式测试，用户可以连续输入问题"""
    print("\n" + "=" * 60)
    print("🎤 交互式测试模式")
    print("=" * 60)
    print("输入问题进行检索，输入 'quit' 或 'exit' 退出")
    print("-" * 60)

    while True:
        question = input("\n❓ 请输入问题: ").strip()

        if question.lower() in ['quit', 'exit', 'q']:
            print("👋 退出测试")
            break

        if not question:
            continue

        test_single_question(collection, question, n_results=3)


# ==================== 统计信息 ====================
def print_collection_info(collection):
    """打印集合统计信息"""
    try:
        count = collection.count()
        print(f"\n📊 集合统计:")
        print(f"   总条目数: {count}")
    except:
        pass


# ==================== 主函数 ====================
def main():
    parser = argparse.ArgumentParser(description='测试向量数据库检索')
    parser.add_argument('-q', '--question', type=str, help='单个测试问题')
    parser.add_argument('-i', '--interactive', action='store_true', help='交互式测试模式')
    parser.add_argument('-n', '--n_results', type=int, default=5, help='返回结果数量（默认5）')
    parser.add_argument('--batch', action='store_true', help='批量测试预设问题')

    args = parser.parse_args()

    print("=" * 60)
    print("灵山胜境 - 向量检索测试工具")
    print("=" * 60)

    # 连接数据库
    collection = get_collection()
    if collection is None:
        sys.exit(1)

    print_collection_info(collection)

    # 预设的批量测试问题
    BATCH_QUESTIONS = [
        "灵山大佛有多高？",
        "九龙灌浴几点开始？",
        "门票多少钱？",
        "怎么去灵山胜境？",
        "有轮椅出租吗？",
        "祥符禅寺建于什么时候？",
        "梵宫有什么看点？",
        "适合带孩子去吗？",
        "五印坛城是什么风格？",
        "可以抱佛脚吗？",
        "景区有洗手间吗？",
        "灵山精舍怎么预定？",
        "曼飞龙塔在哪里？",
        "无尽意斋是什么地方？",
        "菩提大道有什么特色？",
        "百子戏弥勒有什么寓意？",
    ]

    # 根据参数选择测试模式
    if args.question:
        # 单问题模式
        test_single_question(collection, args.question, args.n_results)

    elif args.interactive:
        # 交互式模式
        interactive_test(collection)

    elif args.batch:
        # 批量模式
        results = test_batch(collection, BATCH_QUESTIONS, n_results=3)

        # 打印统计
        print("\n" + "=" * 70)
        print("📊 批量测试统计")
        print("=" * 70)

        success_count = sum(1 for r in results if r['found'])
        total = len(results)
        print(f"   成功率: {success_count}/{total} ({success_count/total*100:.1f}%)")

        print("\n📋 详细结果:")
        for r in results:
            status = "✅" if r['found'] else "❌"
            print(f"   {status} {r['question']}")
            if r['found']:
                print(f"      → {r['top_answer']}...")

    else:
        # 默认：运行批量测试
        results = test_batch(collection, BATCH_QUESTIONS, n_results=3)

        print("\n" + "=" * 70)
        print("📊 批量测试统计")
        print("=" * 70)

        success_count = sum(1 for r in results if r['found'])
        total = len(results)
        print(f"   成功率: {success_count}/{total} ({success_count/total*100:.1f}%)")

        # 显示低相似度的问题（需要改进的）
        low_quality = [r for r in results if r['found'] and r['similarity'] < 0.6]
        if low_quality:
            print(f"\n⚠️ 相似度较低的问题 ({len(low_quality)}个，需要优化):")
            for r in low_quality:
                print(f"   • {r['question']} (相似度: {r['similarity']:.3f})")

    print("\n✨ 测试完成")


if __name__ == "__main__":
    main()