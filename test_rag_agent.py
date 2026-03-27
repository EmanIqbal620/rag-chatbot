import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from agents.rag_agent import RAGAgent
from database.postgres_client import PostgresService

async def test_rag_agent():
    """
    Test script to verify the RAG agent is working properly.
    """
    print("Testing RAG Agent with OpenAI Agents SDK...")

    try:
        # Initialize services
        rag_agent = RAGAgent()
        postgres_service = PostgresService()
        await postgres_service.initialize()

        print("✓ RAG Agent initialized successfully")
        print("✓ Postgres Service initialized successfully")

        # Test health checks
        if rag_agent.is_healthy():
            print("✓ RAG Agent health check passed")
        else:
            print("✗ RAG Agent health check failed")
            return

        if postgres_service.is_healthy():
            print("✓ Postgres Service health check passed")
        else:
            print("✗ Postgres Service health check failed")
            return

        # Test a simple query (this will use the vector store to retrieve context)
        print("\nTesting a sample query...")
        test_query = "What is humanoid robotics?"

        response_data = await rag_agent.process_query(
            query=test_query,
            top_k=3,
            max_tokens=500,
            temperature=0.7
        )

        print(f"✓ Query processed successfully")
        print(f"Response: {response_data['response'][:200]}...")
        print(f"Sources: {len(response_data['sources'])} sources retrieved")

        # Test logging
        await postgres_service.log_chat_interaction(
            query=test_query,
            response=response_data["response"],
            context=str(response_data.get("context", "")),
            sources=response_data["sources"],
            response_time_ms=1000,
            user_id="test_user"
        )

        print("✓ Logging test completed successfully")

        # Test stats
        stats = await postgres_service.get_usage_stats()
        print(f"✓ Stats retrieved: {stats}")

        print("\n🎉 All tests passed! RAG agent system is working properly.")

    except Exception as e:
        print(f"✗ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        await postgres_service.close()
        rag_agent.cleanup()

if __name__ == "__main__":
    asyncio.run(test_rag_agent())