#!/usr/bin/env python3
"""Minimal test server for chatbot"""
import asyncio
from agent.rag_agent import run_agent

async def test():
    print("Testing pre-computed greeting...")
    result = await run_agent("hi", None, True)
    print(f"Result: {result['answer']}")
    print(f"Cache hit: {result.get('cache_hit')}")
    print(f"Response time: {result.get('response_time')}")
    
    print("\nTesting ROS2 question...")
    result = await run_agent("what is ros2", None, True)
    print(f"Result: {result['answer']}")
    
    print("\nTesting hello greeting...")
    result = await run_agent("hello", None, True)
    print(f"Result: {result['answer']}")

if __name__ == "__main__":
    asyncio.run(test())
