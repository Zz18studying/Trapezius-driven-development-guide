# -*- coding: utf-8 -*-
"""
测试向量数据库检索效果。
"""

import argparse
import os
import sys
import chromadb
from chromadb.utils import embedding_functions


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, "backend", "chroma_db")
COLLECTION_NAME = "lingshan_faq"
LOCAL_MODEL_CANDIDATES = [
    "/home/ubuntu/.cache/sentence-transformers/local_model",
    os.path.join(os.path.expanduser("~"), ".cache", "sentence-transformers", "local_model"),
]

sys.path.insert(0, BACKEND_DIR)
from services.local_embedding import SimpleChineseEmbeddingFunction
from services.retrieval_ranker import detect_intents, rerank_candidates


def get_embedding_function():
    for model_path in LOCAL_MODEL_CANDIDATES:
        if os.path.exists(model_path):
            return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_path)
    return SimpleChineseEmbeddingFunction()


def get_collection():
    if not os.path.exists(CHROMA_DB_PATH):
        print(f"向量数据库不存在: {CHROMA_DB_PATH}")
        print("请先运行 scripts/03_build_vector_db.py")
        return None

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    embedding_fn = get_embedding_function()
    try:
        collection = client.get_collection(COLLECTION_NAME, embedding_function=embedding_fn)
    except Exception as e:
        print(f"无法获取集合: {e}")
        return None

    print("已连接向量数据库")
    print(f"数据库路径: {CHROMA_DB_PATH}")
    print(f"集合名称: {COLLECTION_NAME}")
    print(f"条目数: {collection.count()}")
    return collection


def expand_question(question: str) -> list:
    queries = [question]
    intents = detect_intents(question)
    if "price" in intents:
        queries.extend(["灵山胜境门票多少钱", "票务价格 成人票 半价票 免票 观光车"])
    if "parent" in intents:
        queries.extend(["亲子游怎么玩", "亲子家庭路线 孩子 儿童"])
    if "rain" in intents:
        queries.extend(["雨天适合去哪", "室内景点 馆内 展厅"])
    if "elder" in intents:
        queries.extend(["老人游怎么玩", "观光车 体力有限 老人"])
    if "quick" in intents:
        queries.extend(["半天怎么玩", "快速游 轻松游 路线规划"])

    result = []
    seen = set()
    for query in queries:
        query = query.strip()
        if query and query not in seen:
            seen.add(query)
            result.append(query)
    return result


def query_candidates(collection, question: str, n_results: int) -> list:
    candidates = []
    for query in expand_question(question):
        result = collection.query(query_texts=[query], n_results=max(n_results * 12, 50))
        docs = result.get("documents", [[]])[0] or []
        metadatas = result.get("metadatas", [[]])[0] or []
        distances = result.get("distances", [[]])[0] or []
        candidates.extend(make_candidates(metadatas, distances, docs))
    return candidates


def test_single_question(collection, question: str, n_results: int = 5):
    print("\n" + "=" * 70)
    print(f"问题: {question}")
    print("=" * 70)

    candidates = query_candidates(collection, question, n_results)
    if not candidates:
        print("未找到结果")
        return None

    reranked = rerank_candidates(candidates, question)[:n_results]

    for index, item in enumerate(reranked, 1):
        print(f"\n[{index}] 总分: {item.get('final_score', 0):.3f} | 向量: {item.get('vector_similarity', 0):.3f}")
        print(f"类型: {item.get('type', '')} / {item.get('category', '')}")
        print(f"问题: {item.get('question', '')}")
        answer = item.get("answer", "")
        print(f"答案: {answer[:180]}{'...' if len(answer) > 180 else ''}")
        if item.get("source"):
            print(f"来源: {item.get('source')}")
    return reranked


def test_batch(collection, questions: list, n_results: int = 3):
    summary = []
    for question in questions:
        candidates = query_candidates(collection, question, n_results)
        if not candidates:
            summary.append((question, False, 0, ""))
            print(f"未命中: {question}")
            continue
        top = rerank_candidates(candidates, question)[0]
        score = top.get("final_score", 0)
        top_question = top.get("question", "")
        summary.append((question, True, score, top_question))
        print(f"命中: {question} -> {top_question[:45]} (总分 {score:.3f})")
    return summary


def make_candidates(metadatas: list, distances: list, docs: list) -> list:
    candidates = []
    for metadata, distance, doc in zip(metadatas, distances, docs):
        candidates.append({
            "type": metadata.get("type", ""),
            "question": metadata.get("question", ""),
            "answer": metadata.get("answer", ""),
            "category": metadata.get("category", ""),
            "attraction_name": metadata.get("attraction_name", ""),
            "source": metadata.get("source", ""),
            "source_type": metadata.get("source_type", ""),
            "vector_similarity": 1 - distance,
            "doc": doc,
        })
    return candidates


def interactive(collection):
    print("进入交互检索，输入 exit 退出。")
    while True:
        question = input("\n请输入问题: ").strip()
        if question.lower() in {"exit", "quit", "q"}:
            break
        if question:
            test_single_question(collection, question, 5)


def main():
    parser = argparse.ArgumentParser(description="测试灵山胜境向量检索")
    parser.add_argument("-q", "--question", help="单个问题")
    parser.add_argument("-n", "--n_results", type=int, default=5)
    parser.add_argument("-i", "--interactive", action="store_true")
    parser.add_argument("--batch", action="store_true")
    args = parser.parse_args()

    collection = get_collection()
    if collection is None:
        sys.exit(1)

    batch_questions = [
        "灵山大佛有多高？",
        "九龙灌浴几点开始？",
        "门票多少钱？",
        "祥符禅寺有什么历史？",
        "梵宫有什么看点？",
        "五印坛城是什么风格？",
        "带孩子怎么玩？",
        "雨天适合去哪？",
        "拈花广场有什么特色？",
        "香月花街可以做什么？",
        "曼飞龙塔在哪里？",
        "菩提大道有什么文化寓意？",
    ]

    if args.question:
        test_single_question(collection, args.question, args.n_results)
    elif args.interactive:
        interactive(collection)
    else:
        summary = test_batch(collection, batch_questions, 3)
        found = sum(1 for _, ok, _, _ in summary if ok)
        print("\n" + "=" * 70)
        print(f"批量测试完成: {found}/{len(summary)} 命中")
        low = [(q, sim) for q, ok, sim, _ in summary if ok and sim < 0.35]
        if low:
            print("低相似度问题:")
            for question, similarity in low:
                print(f"  {question}: {similarity:.3f}")


if __name__ == "__main__":
    main()
