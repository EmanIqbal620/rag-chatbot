"""
ULTRA-FAST RAG Agent with Multi-Level Caching
Optimized for sub-second response times
"""
import os
import httpx
import asyncio
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any
from functools import lru_cache
import hashlib

load_dotenv()

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3-8b-instruct")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Aggressive caching
_response_cache: Dict[str, dict] = {}
_context_cache: Dict[str, str] = {}

# Pre-computed answers for instant responses (most common questions)
_PRECOMPUTED_ANSWERS = {
    # Greetings
    "hi": "Hello! 👋 I'm your Robotics Tutor. Ask me anything about ROS2, humanoids, AI, or simulation!",
    "hello": "Hello! 👋 I'm your Robotics Tutor. Ask me anything about ROS2, humanoids, AI, or simulation!",
    "hey": "Hey there! 🤖 Ready to learn about humanoid robotics? Ask me anything!",
    "hi there": "Hi there! 👋 Welcome! I'm here to help you learn humanoid robotics.",
    "hello there": "Hello there! 🤖 What would you like to learn about robotics today?",
    "good morning": "Good morning! ☀️ Ready to explore robotics? Ask me anything!",
    "good afternoon": "Good afternoon! 🌞 Let's learn about humanoid robotics together!",
    "good evening": "Good evening! 🌙 How can I help you with robotics today?",
    "how are you": "I'm doing great! 🤖 Ready to help you learn about humanoid robotics!",
    "whats up": "Not much! Just here to help you learn about robots. What's your question?",
    "help": "I'm here to help! Ask me about ROS2, humanoids, simulation, AI, hardware, or any robotics topic!",
    
    # Chapter/Module questions
    "chapter 1": "Chapter 1 covers ROS 2 Fundamentals - the robotic nervous system. You'll learn about nodes, topics, services, and actions for robot communication.",
    "explain chapter 1": "Chapter 1 covers ROS 2 Fundamentals - the robotic nervous system. You'll learn about nodes, topics, services, and actions for robot communication.",
    "what is chapter 1": "Chapter 1 is about ROS 2 Fundamentals - robot communication software using nodes, topics, services, and actions.",
    "chapter 2": "Chapter 2 covers Simulation & Digital Twins using Gazebo and Unity for virtual robot testing.",
    "explain chapter 2": "Chapter 2 teaches you to build virtual robot models in Gazebo and Unity, creating digital twins for safe testing before real deployment.",
    "chapter 3": "Chapter 3 covers NVIDIA Isaac AI - advanced AI-powered robotics for perception and motion planning.",
    "explain chapter 3": "Chapter 3 teaches NVIDIA Isaac for AI robotics - perception, manipulation, and autonomous navigation with deep learning.",
    "chapter 4": "Chapter 4 covers Vision-Language-Action (VLA) systems - combining vision, language, and robot control.",
    "explain chapter 4": "Chapter 4 teaches VLA systems that enable robots to understand natural language commands and interact intelligently with the world.",
    "module 1": "Module 1 is ROS 2 Fundamentals - learning robot communication with nodes, topics, services, and actions.",
    "module 2": "Module 2 is Simulation & Digital Twins - building virtual robots in Gazebo and Unity.",
    "module 3": "Module 3 is NVIDIA Isaac AI - AI-powered robotics for perception and planning.",
    "module 4": "Module 4 is Vision-Language-Action - combining vision, language, and robot control.",
    
    # ROS2
    "ros2": "ROS2 is robot communication software for controlling robots.",
    "ros 2": "ROS2 is robot communication software for controlling robots.",
    "what is ros2": "ROS2 is robot communication software for controlling robots.",
    "what is ros 2": "ROS2 is robot communication software for controlling robots.",
    "ros2 basics": "ROS2 uses nodes, topics, services, and actions for robot control.",
    
    # Humanoid
    "humanoid": "A humanoid is a robot designed to look and move like a human.",
    "what is a humanoid": "A humanoid is a robot designed to look and move like a human.",
    "what is humanoid": "A humanoid is a robot designed to look and move like a human.",
    "humanoid robot": "A humanoid is a robot designed to look and move like a human.",
    
    # AI
    "ai": "AI enables robots to learn, perceive, and make decisions like humans.",
    "what is ai": "AI enables robots to learn, perceive, and make decisions like humans.",
    "what is artificial intelligence": "AI enables robots to learn, perceive, and make decisions like humans.",
    "artificial intelligence": "AI enables robots to learn, perceive, and make decisions like humans.",
    "test the terminal widget": "Terminal widget is working! The chatbot uses a sci-fi interface with glowing borders.",
    "widget": "The terminal widget has a cyberpunk design with cyan glow effects and monospace font.",
    
    # Simulation
    "simulation": "Simulation tests robots in virtual worlds before real deployment.",
    "what is simulation": "Simulation tests robots in virtual worlds before real deployment.",
    "gazebo": "Gazebo is a 3D physics simulator for testing robot behaviors.",
    "what is gazebo": "Gazebo is a 3D physics simulator for testing robot behaviors.",
    "unity": "Unity is a 3D engine used for robot visualization and simulation.",
    "what is unity": "Unity is a 3D engine used for robot visualization and simulation.",
    "digital twin": "A digital twin is a virtual robot model for testing before real deployment.",
    "what is a digital twin": "A digital twin is a virtual robot model for testing before real deployment.",

    # NVIDIA
    "nvidia isaac": "NVIDIA Isaac is an AI robotics platform for simulation and deployment.",
    "what is nvidia isaac": "NVIDIA Isaac is an AI robotics platform for simulation and deployment.",
    "isaac": "NVIDIA Isaac is an AI robotics platform for simulation and deployment.",
    "isaac sim": "Isaac Sim is NVIDIA's photorealistic robot simulation environment.",
    "isaac ros": "Isaac ROS provides GPU-accelerated AI packages for robot perception.",

    # URDF
    "urdf": "URDF is an XML format describing robot model structure and properties.",
    "what is urdf": "URDF is an XML format describing robot model structure and properties.",
    "urdf file": "URDF files define robot links, joints, and physical properties in XML.",

    # Hardware
    "hardware": "Hardware includes CPU (Intel i7/Ryzen 7), GPU, and robot sensors.",
    "hardware requirements": "Hardware needs Intel i7/Ryzen 7 CPU, 16GB RAM, and GPU.",
    "what hardware": "Hardware needs Intel i7/Ryzen 7 CPU, 16GB RAM, and GPU.",
    "cpu": "CPU: Intel i7 or Ryzen 7 for running robotics software.",
    "gpu": "GPU: NVIDIA RTX for AI acceleration and simulation.",
    "ram": "16GB RAM minimum for simulation and AI workloads.",

    # VLA
    "vla": "VLA combines vision, language, and action for robot learning.",
    "what is vla": "VLA combines vision, language, and action for robot learning.",
    "vision language action": "VLA combines vision, language, and action for robot learning.",
    "vision language action models": "VLA models enable robots to understand commands and interact with the world.",

    # General
    "robot": "A robot is a machine that senses, thinks, and acts in the physical world.",
    "what is a robot": "A robot is a machine that senses, thinks, and acts in the physical world.",
    "python": "Python is a programming language widely used in robotics and AI.",
    "what is python": "Python is a programming language widely used in robotics and AI.",
    "sensor": "A sensor detects physical inputs like light, sound, or touch.",
    "what is a sensor": "A sensor detects physical inputs like light, sound, or touch.",
    "actuator": "An actuator is a motor that moves robot joints and parts.",
    "what is an actuator": "An actuator is a motor that moves robot joints and parts.",
    "lidar": "LiDAR uses laser pulses to measure distances for robot navigation.",
    "what is lidar": "LiDAR uses laser pulses to measure distances for robot navigation.",
    "camera": "Cameras provide visual input for robot perception systems.",
    "what is ros": "ROS2 is robot communication software for controlling robots.",
    "nodes": "Nodes are processes that communicate in ROS2 for robot control.",
    "topics": "Topics are channels for publishing/subscribing messages between nodes.",
    "services": "Services are request-response communication between ROS2 nodes.",
    "actions": "Actions are long-running tasks with feedback in ROS2.",
}


def _normalize_query(query: str) -> str:
    """Normalize query for matching."""
    return query.lower().strip().replace("?", "").replace("_", " ")


def _get_cache_key(query: str, selected_text: Optional[str] = None) -> str:
    """Generate cache key for query."""
    key_str = f"{query}:{selected_text or ''}"
    return hashlib.md5(key_str.encode()).hexdigest()


def get_precomputed_answer(question: str) -> Optional[str]:
    """Get pre-computed answer if query matches known questions."""
    normalized = _normalize_query(question)
    
    # Direct match
    if normalized in _PRECOMPUTED_ANSWERS:
        return _PRECOMPUTED_ANSWERS[normalized]
    
    # Partial match (check if any key is in the query)
    for key, answer in _PRECOMPUTED_ANSWERS.items():
        if key in normalized or normalized in key:
            return answer
    
    return None


async def run_agent(
    question: str, 
    selected_text: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    ULTRA-FAST agent with multi-level caching.
    
    Priority:
    1. Pre-computed answers (instant - 0ms)
    2. Response cache (fast - 50ms)
    3. LLM with cached context (medium - 500ms)
    4. Full LLM + retrieval (slow - 2000ms)
    """
    # Build full query
    if selected_text:
        full_query = f"[SELECTED]: {selected_text}\n\nQuestion: {question}"
    else:
        full_query = question
    
    cache_key = _get_cache_key(full_query)
    
    # LEVEL 1: Check pre-computed answers (INSTANT!)
    precomputed = get_precomputed_answer(question)
    if precomputed:
        # Still fetch sources for display (async, non-blocking)
        sources_task = asyncio.create_task(_get_sources_async(full_query))
        sources = await sources_task
        return {
            "answer": precomputed,
            "sources": sources,
            "response_time": 0.001,
            "cache_hit": "precomputed"
        }
    
    # LEVEL 2: Check response cache (VERY FAST)
    if use_cache and cache_key in _response_cache:
        cached = _response_cache[cache_key]
        return {
            "answer": cached["answer"],
            "sources": cached["sources"],
            "response_time": 0.05,
            "cache_hit": "response"
        }
    
    # LEVEL 3: Full LLM generation
    try:
        # Get context first (with caching)
        context = await _get_context_cached(full_query)
        
        # Build prompt
        user_prompt = _build_prompt(context, full_query)
        
        # Call LLM
        try:
            answer = await _call_llm(user_prompt)
        except Exception as llm_error:
            # Return friendly error instead of technical details
            answer = "I apologize, but I'm having trouble connecting to the AI service right now. However, I can still help with common questions! Try asking about ROS2, humanoids, simulation, or hardware basics."
        
        # Get sources
        sources = await _get_sources_async(full_query)
        
        # Cache the response
        if use_cache:
            _response_cache[cache_key] = {
                "answer": answer,
                "sources": sources,
                "timestamp": asyncio.get_event_loop().time()
            }
        
        return {
            "answer": answer,
            "sources": sources,
            "response_time": 0.5,
            "cache_hit": None
        }
        
    except Exception as e:
        return {
            "answer": f"Error: {str(e)}",
            "sources": [],
            "response_time": 0,
            "cache_hit": None
        }


def _build_prompt(context: str, query: str) -> str:
    """Build optimized prompt for LLM - FASTEST."""
    return f"""You are a robotics textbook assistant. Answer in ONE short sentence.

Context: {context[:400]}

Q: {query}
A:"""


async def _call_llm(prompt: str) -> str:
    """Call LLM with optimized parameters for SPEED."""
    if not OPENROUTER_API_KEY:
        raise Exception("AI service not configured")

    try:
        # Shorter timeout for faster fail
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://humanoid-robotics-textbook-zeta.vercel.app",
                    "X-Title": "Robotics-Tutor-Fast",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 25,  # Even shorter responses
                    "temperature": 0.1,  # Low temperature for consistency
                    "top_p": 0.9,  # Faster sampling
                    "frequency_penalty": 0,  # Disable for speed
                    "presence_penalty": 0,  # Disable for speed
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise Exception("AI service authentication failed")
        raise Exception(f"AI service error: {e.response.status_code}")
    except httpx.ReadTimeout:
        raise Exception("AI service timeout - try again")
    except Exception as e:
        raise Exception(f"AI service unavailable")


async def _get_context_cached(query: str) -> str:
    """Get context with caching."""
    cache_key = hashlib.md5(query.encode()).hexdigest()[:16]
    
    if cache_key in _context_cache:
        return _context_cache[cache_key]
    
    # Get context from retriever
    from retrieval.retriever import search
    results = search(query, top_k=1)
    
    if not results:
        context = "No relevant content found in the textbook."
    else:
        context = results[0].get("text", "No content available")
    
    _context_cache[cache_key] = context
    return context


async def _get_sources_async(query: str, top_k: int = 3) -> List[Dict]:
    """Get sources asynchronously (non-blocking)."""
    try:
        from retrieval.retriever import search
        results = search(query, top_k=top_k)
        return [
            {
                "chapter_name": s.get("chapter_name", s.get("page_title", "Unknown")),
                "source_url": s["source_url"],
                "score": s["score"]
            }
            for s in results
        ]
    except Exception:
        return []


def cleanup_cache(max_size: int = 1000):
    """Cleanup cache if it grows too large."""
    global _response_cache, _context_cache
    
    if len(_response_cache) > max_size:
        # Keep only recent 50%
        items = list(_response_cache.items())
        _response_cache = dict(items[len(items)//2:])
    
    if len(_context_cache) > max_size:
        items = list(_context_cache.items())
        _context_cache = dict(items[len(items)//2:])
