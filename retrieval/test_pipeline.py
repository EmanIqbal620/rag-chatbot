import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retrieval.retriever import search

TEST_QUERIES = [
    "What is ROS2?",
    "Explain the key concepts of robotics simulation",
    "[SELECTED]: ROS2 is a set of software libraries for robot development",
    "What is the capital of France?",  # Out of scope — expect low score
    "hardware requirements"
]

def run_tests():
    print("=" * 60)
    print("RAG PIPELINE TEST")
    print("=" * 60)
    passed = 0

    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\nQuery {i}: {query[:60]}...")
        results = search(query, top_k=3)

        if not results:
            print("  ⚠️  No results returned")
            continue

        top = results[0]
        print(f"  Top Score : {top['score']}")
        print(f"  Source    : {top['source_url']}")
        print(f"  Snippet   : {top['text'][:100]}...")

        if i != 4 and top["score"] > 0.5:  # Skip out-of-scope test
            passed += 1

    print(f"\n{'=' * 60}")
    print(f"Result: {passed}/4 queries passed (score > 0.5)")
    if passed >= 3:
        print("✅ Phase 2 PASSED")
    else:
        print("❌ Phase 2 FAILED — check embeddings and collection")

if __name__ == "__main__":
    run_tests()
