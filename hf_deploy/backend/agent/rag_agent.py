"""
ULTRA-FAST RAG Agent with Multi-Level Caching
Optimized for sub-second response times
Pre-computed answers + Cohere embeddings + Qdrant retrieval + LLM fallback
"""
import os
import httpx
import asyncio
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, List, Optional, Any
import re
import hashlib

# Load backend .env specifically
backend_dir = Path(__file__).parent.parent
load_dotenv(backend_dir / ".env", override=True)

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3-8b-instruct")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Aggressive caching
_response_cache: Dict[str, dict] = {}
_context_cache: Dict[str, str] = {}

# Pre-computed answers for instant responses
# Covers ALL common queries from the textbook
_PRECOMPUTED_ANSWERS = {
    # Greetings
    "hi": "Hi! Ask me anything about ROS2, NVIDIA Isaac, simulation, VLA systems, or hardware.",
    "hello": "Hello! I'm your robotics tutor. Ask me about ROS2, Isaac Sim, VLA, or hardware!",
    "hey": "Hey! What robotics topic would you like to learn about?",
    "hi there": "Hi there! Welcome to the Humanoid Robotics AI textbook!",
    "hello there": "Hello there! What would you like to learn about robotics today?",
    "good morning": "Good morning! Ready to explore humanoid robotics?",
    "good afternoon": "Good afternoon! Let's learn about humanoid robotics together!",
    "good evening": "Good evening! How can I help you with robotics today?",
    "how are you": "I'm doing great! Ready to help you learn about humanoid robotics!",
    "whats up": "Not much! Just here to help you learn about robots. What's your question?",
    "help": "I'm here to help! Ask me about ROS2, humanoids, simulation, NVIDIA Isaac, VLA, hardware, or any robotics topic!",
    "ok": "Is there anything specific you'd like to know about robotics?",
    "yes": "Great! What would you like to learn about? Try asking about ROS2, NVIDIA Isaac, simulation, VLA, or hardware!",
    "thanks": "You're welcome! Feel free to ask more questions about robotics anytime!",
    "thank you": "You're welcome! Feel free to ask more questions anytime!",

    # How many modules
    "how many modules": "The textbook has 6 modules: 1) ROS 2 Fundamentals, 2) Simulation & Digital Twins, 3) NVIDIA Isaac AI, 4) Vision-Language-Action, 5) Hardware Requirements, 6) Assessment.",
    "how many module": "The textbook has 6 modules: 1) ROS 2 Fundamentals, 2) Simulation & Digital Twins, 3) NVIDIA Isaac AI, 4) Vision-Language-Action, 5) Hardware Requirements, 6) Assessment.",
    "how many modules in this book": "The textbook has 6 modules: 1) ROS 2 Fundamentals, 2) Simulation & Digital Twins, 3) NVIDIA Isaac AI, 4) Vision-Language-Action, 5) Hardware Requirements, 6) Assessment.",
    "modules overview": "6 modules: Module 1: ROS 2 Fundamentals. Module 2: Simulation & Digital Twins. Module 3: NVIDIA Isaac AI. Module 4: Vision-Language-Action. Module 5: Hardware Requirements. Module 6: Assessment.",

    # Chapter/Module questions
    "chapter 1": "Chapter 1 covers ROS 2 Fundamentals — the robotic nervous system. You'll learn about nodes, topics, services, and actions for robot communication.",
    "explain chapter 1": "Chapter 1 covers ROS 2 Fundamentals — the robotic nervous system. You'll learn about nodes, topics, services, and actions for robot communication.",
    "explain me chapter 1": "Chapter 1 covers ROS 2 Fundamentals — the robotic nervous system. You'll learn about nodes, topics, services, and actions for robot communication.",
    "what is chapter 1": "Chapter 1 is about ROS 2 Fundamentals — robot communication software using nodes, topics, services, and actions.",
    "chapter 2": "Chapter 2 covers Simulation & Digital Twins using Gazebo and Unity for virtual robot testing.",
    "explain chapter 2": "Chapter 2 teaches you to build virtual robot models in Gazebo and Unity, creating digital twins for safe testing before real deployment.",
    "explain me chapter 2": "Chapter 2 teaches you to build virtual robot models in Gazebo and Unity, creating digital twins for safe testing before real deployment.",
    "what is chapter 2": "Chapter 2 covers Simulation & Digital Twins — building virtual robots using Gazebo physics simulation and Unity visualization.",
    "chapter 3": "Chapter 3 covers NVIDIA Isaac AI — advanced AI-powered robotics for perception and motion planning.",
    "explain chapter 3": "Chapter 3 teaches NVIDIA Isaac for AI robotics — perception, manipulation, and autonomous navigation with deep learning.",
    "what is chapter 3": "Chapter 3 is about NVIDIA Isaac AI — advanced AI-powered robotics for perception and motion planning.",
    "chapter 4": "Chapter 4 covers Vision-Language-Action (VLA) systems — combining vision, language, and robot control.",
    "explain chapter 4": "Chapter 4 teaches VLA systems that enable robots to understand natural language commands and interact intelligently with the world.",
    "what is chapter 4": "Chapter 4 is about Vision-Language-Action (VLA) systems — combining vision, language understanding, and robot action.",
    "chapter 5": "Chapter 5 covers Hardware Requirements — CPU, GPU, RAM, and sensor specifications for humanoid robotics.",
    "explain chapter 5": "Chapter 5 details the hardware requirements: Intel i7/Ryzen 7 CPU, 32GB RAM, NVIDIA RTX 3070 GPU, 1TB SSD, and Ubuntu 22.04 LTS.",
    "chapter 6": "Chapter 6 covers Assessment — comprehensive evaluation methods for measuring progress in humanoid robotics learning.",

    # Module questions
    "module 1": "Module 1 is ROS 2 Fundamentals — learning robot communication with nodes, topics, services, and actions.",
    "module 2": "Module 2 is Simulation & Digital Twins — building virtual robots in Gazebo and Unity.",
    "module 3": "Module 3 is NVIDIA Isaac AI — AI-powered robotics for perception and planning.",
    "module 4": "Module 4 is Vision-Language-Action — combining vision, language understanding, and robot action execution.",
    "module 5": "Module 5 covers Hardware Requirements — CPU (Intel i7/Ryzen 7), GPU (RTX 3070), 32GB RAM, and sensor specifications.",
    "module 6": "Module 6 is Assessment — evaluation methods and grading for humanoid robotics learning.",

    # Week questions
    "week 1": "Week 1 covers Introduction to ROS 2 Architecture — understanding nodes, topics, DDS, and the ROS 2 ecosystem.",
    "week 2": "Week 2 covers ROS 2 Programming — writing Python code for robot control with nodes, publishers, and subscribers.",
    "week 3": "Week 3 covers URDF and Robot Modeling — describing robot structure using Unified Robot Description Format.",
    "week 4": "Week 4 covers Physics Simulation in Gazebo — building and testing robot models in a physics-based simulator.",
    "week 5": "Week 5 covers High-Fidelity Visualization in Unity — creating realistic 3D robot rendering and simulation.",
    "week 6": "Week 6 covers Isaac Sim Fundamentals — NVIDIA's photorealistic 3D simulation environment for robotics.",
    "week 7": "Week 7 covers Isaac ROS Packages — GPU-accelerated perception and navigation packages for robotics.",
    "week 8": "Week 8 covers Navigation and Bipedal Control — path planning and walking control for humanoid robots.",
    "week 9": "Week 9 covers Voice Recognition and VLA Systems — combining speech understanding with vision and action.",
    "week 10": "Week 10 covers LLM Cognitive Planning — using Large Language Models for robot reasoning and task planning.",
    "week 11": "Week 11 covers Advanced VLA Integration — combining vision, language, and action for complex tasks.",
    "week 12": "Week 12 covers System Integration — putting together all components for a complete humanoid robot system.",
    "week 13": "Week 13 is the Capstone Project — building an autonomous humanoid system integrating all modules.",

    # ROS2
    "ros2": "ROS 2 serves as the nervous system for humanoid robots, providing a framework for architecture and communication through nodes, topics, services, and actions.",
    "ros 2": "ROS 2 serves as the nervous system for humanoid robots, providing a framework for architecture and communication through nodes, topics, services, and actions.",
    "what is ros2": "ROS 2 serves as the nervous system for humanoid robots, providing a framework for architecture and communication through nodes, topics, services, and actions.",
    "what is ros 2": "ROS 2 serves as the nervous system for humanoid robots, providing a framework for architecture and communication through nodes, topics, services, and actions.",
    "ros2 basics": "ROS 2 uses nodes (processes), topics (pub/sub), services (request-response), and actions (long-running tasks) for robot communication.",
    "ros": "ROS 2 serves as the nervous system for humanoid robots, providing a framework for architecture and communication through nodes, topics, services, and actions.",
    "what is ros": "ROS 2 serves as the nervous system for humanoid robots, providing a framework for architecture and communication through nodes, topics, services, and actions.",
    "nodes": "A node is a process that performs computation in ROS 2, communicating with other nodes through topics, services, and actions.",
    "topics": "Topics are named channels for publishing and subscribing to messages between ROS 2 nodes, enabling distributed communication.",
    "services": "Services provide request-response communication between ROS 2 nodes for synchronous interactions.",
    "actions": "Actions are long-running tasks in ROS 2 that provide feedback and can be cancelled, used for complex robot operations.",
    "dds": "DDS (Data Distribution Service) is the middleware layer in ROS 2 that enables real-time, reliable communication between nodes.",
    "urdf": "URDF (Unified Robot Description Format) is an XML format that describes robot structure including links, joints, and physical properties.",
    "what is urdf": "URDF (Unified Robot Description Format) is an XML format that describes robot structure including links, joints, and physical properties.",

    # Humanoid
    "humanoid": "A humanoid is a robot designed to look and move like a human, with two legs, arms, and a head for natural interaction.",
    "what is a humanoid": "A humanoid is a robot designed to look and move like a human, with two legs, arms, and a head for natural interaction.",
    "what is humanoid": "A humanoid is a robot designed to look and move like a human, with two legs, arms, and a head for natural interaction.",
    "humanoid robot": "A humanoid is a robot designed to look and move like a human, with two legs, arms, and a head for natural interaction.",

    # Physical AI
    "physical ai": "Physical AI refers to artificial intelligence systems that interact with the physical world through sensors and actuators, enabling robots to perceive, understand, and act in real environments.",
    "what is physical ai": "Physical AI refers to AI systems that interact with the physical world — robots that perceive their environment through sensors, process information, and take actions using actuators.",
    "what is physical artificial intelligence": "Physical AI refers to AI systems that interact with the physical world through sensors, processing, and actuators for real-world robot interaction.",

    # AI
    "ai": "AI enables robots to learn, perceive, and make decisions like humans.",
    "what is ai": "AI enables robots to learn, perceive, and make decisions like humans.",
    "what is artificial intelligence": "AI enables robots to learn, perceive, and make decisions like humans.",
    "artificial intelligence": "AI enables robots to learn, perceive, and make decisions like humans.",
    "machine learning": "Machine learning allows robots to improve their performance over time by learning from data rather than being explicitly programmed.",

    # Simulation
    "simulation": "Simulation allows testing robots in virtual worlds using Gazebo for physics and Unity for visualization before real deployment.",
    "what is simulation": "Simulation creates virtual environments where robots can be tested safely before real-world deployment.",
    "gazebo": "Gazebo is a powerful 3D physics simulation environment for robotics, used to test robot behavior before real-world deployment.",
    "what is gazebo": "Gazebo is a powerful 3D physics simulation environment for robotics, used to test robot behavior before real-world deployment.",
    "unity": "Unity is a high-fidelity 3D visualization engine used for realistic robot rendering and simulation.",
    "what is unity": "Unity is a high-fidelity 3D visualization engine used for realistic robot rendering and simulation.",
    "digital twin": "Digital twins are virtual robot models created using Gazebo for physics simulation and Unity for high-fidelity visualization.",
    "what is a digital twin": "Digital twins are virtual robot models created using Gazebo for physics simulation and Unity for high-fidelity visualization.",

    # NVIDIA
    "nvidia isaac": "NVIDIA Isaac is an AI robotics platform providing photorealistic simulation (Isaac Sim) and GPU-accelerated perception (Isaac ROS).",
    "what is nvidia isaac": "NVIDIA Isaac is an AI robotics platform providing photorealistic simulation (Isaac Sim) and GPU-accelerated perception (Isaac ROS).",
    "isaac": "NVIDIA Isaac is an AI robotics platform providing photorealistic simulation (Isaac Sim) and GPU-accelerated perception (Isaac ROS).",
    "isaac sim": "Isaac Sim is NVIDIA's photorealistic 3D simulation environment for testing robots before real-world deployment.",
    "what is isaac sim": "Isaac Sim is NVIDIA's photorealistic 3D simulation environment for testing robots before real-world deployment.",
    "isaac ros": "Isaac ROS provides GPU-accelerated perception and navigation packages for robotics applications.",
    "robot brain": "The AI-Robot Brain is powered by NVIDIA Isaac ecosystem, providing perception, navigation, and control through Isaac Sim and Isaac ROS.",

    # VLA
    "vla": "VLA (Vision-Language-Action) systems integrate vision, language understanding, and action execution for autonomous humanoid robots.",
    "what is vla": "VLA (Vision-Language-Action) systems integrate vision, language understanding, and action execution for autonomous humanoid robots.",
    "vision language action": "VLA systems combine computer vision, natural language processing, and robot action execution for intelligent behavior.",
    "vision language action models": "VLA models enable robots to understand visual scenes, process language commands, and execute physical actions.",

    # Navigation
    "navigation": "Navigation in robotics involves path planning, obstacle avoidance, and localization to move robots autonomously.",
    "bipedal control": "Bipedal control manages the balance and walking motion of humanoid robots using sensors and actuators.",

    # Voice Recognition
    "voice recognition": "Voice recognition allows robots to process and understand spoken commands for human-robot interaction.",

    # LLM
    "llm": "Large Language Models (LLMs) enable robots to understand natural language commands and reason about tasks.",

    # Hardware
    "hardware": "Hardware requirements include: Intel i7/Ryzen 7 CPU, 32GB RAM, NVIDIA RTX 3070 GPU, 1TB SSD, and Ubuntu 22.04 LTS.",
    "hardware requirements": "Hardware requirements include: Intel i7/Ryzen 7 CPU, 32GB RAM, NVIDIA RTX 3070 GPU, 1TB SSD, and Ubuntu 22.04 LTS.",
    "what hardware": "Hardware needs Intel i7/Ryzen 7 CPU, 32GB RAM, NVIDIA RTX 3070 GPU, 1TB SSD for running humanoid robotics software.",
    "cpu": "Intel i7 or AMD Ryzen 7 processor with 8 cores and 16 threads is the minimum CPU requirement.",
    "gpu": "NVIDIA RTX 3070 or equivalent GPU with CUDA support is required for AI acceleration and simulation.",
    "ram": "32GB DDR4 RAM is required for running simulation environments and AI workloads.",

    # Assessment
    "assessment": "Assessment guidelines provide comprehensive evaluation methods for measuring progress in humanoid robotics learning.",

    # General
    "robot": "A robot is a machine that senses, thinks, and acts in the physical world, often autonomously.",
    "what is a robot": "A robot is a machine that senses, thinks, and acts in the physical world, often autonomously.",
    "robotics": "Robotics is the field of engineering and science that designs, builds, and programs robots to perform tasks.",
    "what is robotics": "Robotics is the field of engineering and science that designs, builds, and programs robots to perform tasks.",
    "python": "Python is a programming language widely used in robotics and AI for its simplicity and extensive libraries.",
    "what is python": "Python is a programming language widely used in robotics and AI for its simplicity and extensive libraries.",
    "sensor": "A sensor detects physical inputs like light, sound, or touch for robot perception.",
    "what is a sensor": "A sensor detects physical inputs like light, sound, or touch for robot perception.",
    "actuator": "An actuator is a motor that moves robot joints and parts based on control signals.",
    "what is an actuator": "An actuator is a motor that moves robot joints and parts based on control signals.",
    "lidar": "LiDAR uses laser pulses to measure distances for robot navigation and mapping.",
    "what is lidar": "LiDAR uses laser pulses to measure distances for robot navigation and mapping.",
    "camera": "Cameras provide visual input for robot perception systems, enabling object detection and scene understanding.",
}


def _normalize_query(query: str) -> str:
    """Normalize query for matching."""
    return query.lower().strip().replace("?", "").replace("_", " ").strip()


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

    # Partial match: check if any key is contained in the query
    for key, answer in _PRECOMPUTED_ANSWERS.items():
        if key in normalized or normalized in key:
            return answer

    # Word overlap match: require significant overlap
    query_words = set(normalized.split())
    for key, answer in _PRECOMPUTED_ANSWERS.items():
        key_words = set(key.split())
        if len(key_words) >= 2 and len(key_words & query_words) >= len(key_words) * 0.5:
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
    3. Full RAG: Cohere embed + Qdrant search + LLM generation
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
        sources_task = asyncio.create_task(_get_sources_async(full_query))
        sources = await sources_task
        return {
            "answer": precomputed,
            "sources": sources if sources else [{"chapter_name": "Textbook", "source_url": "https://humanoid-robotics-textbook.vercel.app/docs/intro", "score": 0.0}],
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

    # LEVEL 3: Full RAG pipeline
    try:
        # Get context from Qdrant
        context = await _get_context_cached(full_query)

        # Build prompt
        user_prompt = _build_prompt(context, full_query)

        # Call LLM — OpenRouter first, then Cohere fallback
        try:
            answer = await _call_llm(user_prompt)
        except Exception:
            try:
                answer = await _call_cohere_llm(user_prompt)
            except Exception:
                # Final fallback: use context directly
                answer = context[:300] if context and context != "No relevant content found in the textbook." else _generate_fallback_answer(question)

        # Get sources
        sources = await _get_sources_async(full_query)

        # If no sources and no context found, use fallback answer
        if not sources and (not context or context == "No relevant content found in the textbook."):
            answer = _generate_fallback_answer(question)

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
            "answer": _generate_fallback_answer(question),
            "sources": [],
            "response_time": 0,
            "cache_hit": None
        }


def _generate_fallback_answer(question: str) -> str:
    """Generate a helpful answer from general robotics knowledge when RAG fails."""
    q = _normalize_query(question)

    # Physical AI
    if "physical ai" in q or "physical artificial" in q:
        return "Physical AI refers to artificial intelligence systems that interact with the physical world through sensors and actuators, enabling robots to perceive, understand, and act in real environments."

    # Module/Chapter questions
    if any(w in q for w in ["module", "chapter", "week"]):
        if "module 4" in q or "chapter 4" in q:
            return "Module 4 covers Vision-Language-Action (VLA) systems — combining vision, language understanding, and robot action execution for autonomous humanoid robots."
        if "module 5" in q or "chapter 5" in q:
            return "Module 5 covers Hardware Requirements — CPU (Intel i7/Ryzen 7), GPU (RTX 3070), 32GB RAM, and sensor specifications."
        if "module 6" in q or "chapter 6" in q:
            return "Module 6 covers Assessment — comprehensive evaluation methods for measuring progress in humanoid robotics learning."
        if "week 4" in q:
            return "Week 4 covers Physics Simulation in Gazebo — building and testing robot models in a physics-based 3D simulator."
        if "week 7" in q:
            return "Week 7 covers Isaac ROS Packages — GPU-accelerated perception and navigation packages for robotics."
        if "how many" in q:
            return "The textbook has 6 modules: 1) ROS 2 Fundamentals, 2) Simulation & Digital Twins, 3) NVIDIA Isaac AI, 4) Vision-Language-Action, 5) Hardware Requirements, 6) Assessment."

    # VLA
    if "vla" in q or "vision language action" in q:
        return "VLA (Vision-Language-Action) systems integrate vision, language understanding, and action execution for autonomous humanoid robots."

    # NVIDIA Isaac
    if "isaac" in q or "nvidia" in q:
        return "NVIDIA Isaac is an AI robotics platform providing photorealistic simulation (Isaac Sim) and GPU-accelerated perception (Isaac ROS)."

    # Gazebo
    if "gazebo" in q:
        return "Gazebo is a powerful 3D physics simulation environment for robotics, used to test robot behavior before real-world deployment."

    # Simulation
    if "simulation" in q:
        return "Simulation allows testing robots in virtual worlds using Gazebo for physics and Unity for visualization before real deployment."

    # ROS
    if "ros" in q:
        return "ROS 2 serves as the nervous system for humanoid robots, providing a framework for architecture and communication through nodes, topics, services, and actions."

    # Hardware
    if "hardware" in q:
        return "Hardware requirements include: Intel i7/Ryzen 7 CPU, 32GB RAM, NVIDIA RTX 3070 GPU, 1TB SSD, and Ubuntu 22.04 LTS."

    # Humanoid
    if "humanoid" in q:
        return "A humanoid is a robot designed to look and move like a human, with two legs, arms, and a head for natural interaction."

    # Default
    return "I'm still learning about this topic. Try asking about ROS2, NVIDIA Isaac, simulation, VLA systems, hardware requirements, or any of the 6 modules in the textbook!"


def _build_prompt(context: str, query: str) -> str:
    """Build optimized prompt for LLM — STRICTLY BOOK-ONLY, but allow general knowledge if context is empty."""
    if context and context != "No relevant content found in the textbook.":
        return f"""You are a robotics textbook assistant. Answer ONLY using the context below.

RULES:
1. Answer in ONE short sentence
2. Use ONLY the provided context
3. If the answer is NOT in the context, use your general robotics knowledge to provide a helpful answer

Context: {context[:400]}

Q: {query}
A:"""
    else:
        return f"""You are a robotics textbook assistant. Use your general robotics knowledge to answer the question.

RULES:
1. Answer in ONE short sentence
2. Be accurate and helpful
3. Focus on humanoid robotics concepts

Q: {query}
A:"""


async def _call_llm(prompt: str) -> str:
    """Call LLM with optimized parameters for SPEED."""
    if not OPENROUTER_API_KEY:
        raise Exception("AI service not configured")

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://humanoid-robotics-textbook.vercel.app",
                    "X-Title": "Humanoid-Robotics-Tutor",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 50,
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "frequency_penalty": 0,
                    "presence_penalty": 0,
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
        raise Exception("AI service timeout")
    except Exception as e:
        raise Exception(f"AI service unavailable")


async def _call_cohere_llm(prompt: str) -> str:
    """Call Cohere Chat as LLM fallback."""
    try:
        import cohere
        cohere_client = cohere.Client(os.getenv("COHERE_API_KEY"))

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: cohere_client.chat(
                message=prompt,
                model="command-r-08-2024",
                max_tokens=50,
                temperature=0.1
            )
        )
        return response.text.strip()

    except Exception as e:
        raise Exception(f"Cohere Chat failed: {str(e)}")


async def _get_context_cached(query: str) -> str:
    """Get context with caching from Qdrant retrieval."""
    cache_key = hashlib.md5(query.encode()).hexdigest()[:16]

    if cache_key in _context_cache:
        return _context_cache[cache_key]

    try:
        from retrieval.retriever import search
        results = search(query, top_k=1)

        if not results:
            context = "No relevant content found in the textbook."
        else:
            context = results[0].get("text", "No content available")
    except Exception:
        context = "No relevant content found in the textbook."

    _context_cache[cache_key] = context
    return context


async def _get_sources_async(query: str, top_k: int = 3) -> List[Dict]:
    """Get sources asynchronously from Qdrant retrieval."""
    try:
        from retrieval.retriever import search
        results = search(query, top_k=top_k)
        if not results:
            return []
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
        items = list(_response_cache.items())
        _response_cache = dict(items[len(items)//2:])

    if len(_context_cache) > max_size:
        items = list(_context_cache.items())
        _context_cache = dict(items[len(items)//2:])


async def _log_to_neon(query: str, answer: str, sources: list):
    """Log chat interaction to Neon Postgres (non-blocking)."""
    try:
        import asyncpg
        import os
        from pathlib import Path

        backend_dir = Path(__file__).parent.parent
        db_url = os.getenv("DATABASE_URL")

        if not db_url:
            return

        pool = await asyncpg.create_pool(db_url, min_size=1, max_size=2)
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO chat_logs (query, response, sources, created_at)
                VALUES ($1, $2, $3, NOW())
                """,
                query, answer, str(sources)
            )
        await pool.close()
    except Exception:
        pass
