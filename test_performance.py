#!/usr/bin/env python3
"""
Test Script for Optimized Chatbot Response Times
Tests caching, pre-computed answers, and overall performance
"""
import asyncio
import time
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.rag_agent import run_agent, get_precomputed_answer, _response_cache, _context_cache


async def test_precomputed_answers():
    """Test pre-computed answers (should be instant)."""
    print("\n" + "="*60)
    print("TEST 1: Pre-computed Answers (Target: <50ms)")
    print("="*60)
    
    test_questions = [
        "What is ROS2?",
        "What is a humanoid?",
        "What is AI?",
        "What is Gazebo?",
        "Hardware requirements?",
    ]
    
    total_time = 0
    for question in test_questions:
        start = time.time()
        result = await run_agent(question)
        elapsed = (time.time() - start) * 1000  # ms
        
        total_time += elapsed
        status = "✅" if elapsed < 50 else "⚠️"
        print(f"{status} {question[:30]:<30} {elapsed:>8.2f}ms - {result['answer'][:60]}...")
    
    avg_time = total_time / len(test_questions)
    print(f"\nAverage response time: {avg_time:.2f}ms")
    print(f"Status: {'✅ PASS' if avg_time < 50 else '⚠️ NEEDS OPTIMIZATION'}")


async def test_cached_responses():
    """Test cached responses (should be very fast)."""
    print("\n" + "="*60)
    print("TEST 2: Cached Responses (Target: <100ms)")
    print("="*60)
    
    # First call to populate cache
    question = "Explain the basics of robot simulation"
    print(f"\nFirst call (uncached): {question}")
    start = time.time()
    result1 = await run_agent(question)
    first_time = (time.time() - start) * 1000
    print(f"  Time: {first_time:.2f}ms")
    
    # Second call should use cache
    print(f"Second call (cached): {question}")
    start = time.time()
    result2 = await run_agent(question)
    second_time = (time.time() - start) * 1000
    print(f"  Time: {second_time:.2f}ms")
    
    speedup = first_time / second_time if second_time > 0 else float('inf')
    print(f"\nSpeedup: {speedup:.1f}x faster")
    print(f"Status: {'✅ PASS' if second_time < 100 else '⚠️ NEEDS OPTIMIZATION'}")


async def test_concurrent_requests():
    """Test handling multiple concurrent requests."""
    print("\n" + "="*60)
    print("TEST 3: Concurrent Requests")
    print("="*60)
    
    questions = [
        "What is ROS2?",
        "What is a humanoid robot?",
        "Explain NVIDIA Isaac",
        "What is URDF?",
        "What are sensors?",
    ]
    
    start = time.time()
    tasks = [run_agent(q) for q in questions]
    results = await asyncio.gather(*tasks)
    elapsed = (time.time() - start) * 1000
    
    print(f"Processed {len(questions)} requests in {elapsed:.2f}ms")
    print(f"Average: {elapsed/len(questions):.2f}ms per request")
    print(f"Status: {'✅ PASS' if elapsed < 1000 else '⚠️ NEEDS OPTIMIZATION'}")


def test_cache_memory():
    """Test cache memory usage."""
    print("\n" + "="*60)
    print("TEST 4: Cache Memory Usage")
    print("="*60)
    
    response_cache_size = len(_response_cache)
    context_cache_size = len(_context_cache)
    
    print(f"Response cache entries: {response_cache_size}")
    print(f"Context cache entries: {context_cache_size}")
    print(f"Pre-computed answers: {len(get_precomputed_answer.__globals__.get('_PRECOMPUTED_ANSWERS', {}))}")
    print(f"Status: ✅ Cache initialized")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🤖 HUMANOID ROBOTICS CHATBOT - PERFORMANCE TEST")
    print("="*60)
    
    try:
        await test_precomputed_answers()
        await test_cached_responses()
        await test_concurrent_requests()
        test_cache_memory()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED")
        print("="*60)
        print("\n💡 Optimization Tips:")
        print("  1. Pre-computed answers are instant (<10ms)")
        print("  2. Cached responses are very fast (<50ms)")
        print("  3. LLM responses take longer (500-2000ms)")
        print("  4. Cache is cleared on server restart")
        print("\n🎯 For best performance:")
        print("  - Common questions use pre-computed answers")
        print("  - Repeated questions use response cache")
        print("  - Context is cached to avoid re-fetching")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
