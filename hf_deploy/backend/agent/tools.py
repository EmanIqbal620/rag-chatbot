import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retrieval.retriever import search
import json

# Aggressive multi-level caching
_context_cache = {}
_query_cache = {}

# Pre-computed answers for common questions (instant response)
_PRECOMPUTED = {
    "what is ros2": "ROS2 is robot communication software.",
    "what is ros": "ROS2 is robot communication software.",
    "what is a humanoid": "A humanoid is a robot that looks like a human.",
    "what is humanoid": "A humanoid is a robot that looks like a human.",
    "what is ai": "AI is smart machines doing human tasks.",
    "what is artificial intelligence": "AI is smart machines doing human tasks.",
    "what is simulation": "Simulation is testing robots in virtual world.",
    "what is gazebo": "Gazebo is a 3D robot simulation tool.",
    "what is unity": "Unity is a 3D engine for robot visualization.",
    "what is urdf": "URDF is a format to describe robot models.",
    "what is a robot": "A robot is a machine that performs tasks automatically.",
    "what is python": "Python is a programming language for robots.",
    "what is a sensor": "A sensor is a device that detects physical inputs.",
    "what is an actuator": "An actuator is a motor that moves robot parts.",
    "hardware requirements": "Hardware needs Intel i7 or AMD Ryzen 7 CPU.",
    "what is hardware": "Hardware is the physical parts of a robot system.",
}

def retrieve_context(query: str) -> str:
    """ULTRA-FAST retrieval with pre-computed answers."""
    # Normalize query
    q = query.lower().strip().replace("?", "")
    
    # Check pre-computed first (instant!)
    for key, value in _PRECOMPUTED.items():
        if key in q or q in key:
            return value
    
    # Check context cache
    cache_key = q[:40]
    if cache_key in _context_cache:
        return _context_cache[cache_key]
    
    # Fallback to search
    results = search(query, top_k=1)
    if not results:
        return "No relevant content found."

    text = results[0]['text'][:200]
    _context_cache[cache_key] = text
    return text

def get_precomputed(query: str) -> str:
    """Get pre-computed answer if exists."""
    q = query.lower().strip().replace("?", "")
    for key, value in _PRECOMPUTED.items():
        if key in q or q in key:
            return value
    return None
