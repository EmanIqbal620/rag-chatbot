from typing import List, Dict, Any, Optional
import logging
import asyncpg
import os
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class PostgresService:
    """
    Service for interacting with Neon Serverless Postgres database.
    Handles logging of chat interactions and errors.
    """

    def __init__(self):
        """Initialize the PostgresService with connection details."""
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        self.database_url = database_url
        self.pool = None

    async def initialize(self):
        """Initialize the connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60,
                ssl="require"  # Required for Neon
            )

            # Ensure required tables exist
            await self._ensure_tables_exist()
            logger.info("PostgresService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PostgresService: {str(e)}")
            raise

    async def get_pool(self):
        """Get the connection pool, initializing if needed."""
        if not self.pool:
            await self.initialize()
        return self.pool

    async def _ensure_tables_exist(self):
        """Create required tables if they don't exist."""
        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            # Create chat_logs table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_logs (
                    id SERIAL PRIMARY KEY,
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    context TEXT,
                    sources JSONB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_time_ms INTEGER,
                    user_id VARCHAR(255)
                )
            """)

            # Create query_metrics table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS query_metrics (
                    id SERIAL PRIMARY KEY,
                    query TEXT NOT NULL,
                    response_time_ms INTEGER,
                    success BOOLEAN,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT
                )
            """)

            logger.info("Ensured required tables exist in Postgres")

    async def log_chat_interaction(
        self,
        query: str,
        response: str,
        context: str,
        sources: List[Dict[str, Any]],
        response_time_ms: float,
        user_id: Optional[str] = None
    ):
        """Log a chat interaction to the database."""
        pool = await self.get_pool()

        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO chat_logs
                    (query, response, context, sources, response_time_ms, user_id)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    query,
                    response,
                    context,
                    json.dumps(sources),
                    int(response_time_ms),
                    user_id
                )
            logger.info(f"Logged chat interaction for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to log chat interaction: {str(e)}")
            # Don't raise the exception as logging shouldn't break the main flow

    async def log_error(
        self,
        query: str,
        error_message: str,
        response_time_ms: float,
        user_id: Optional[str] = None
    ):
        """Log an error to the database."""
        pool = await self.get_pool()

        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO query_metrics
                    (query, response_time_ms, success, error_message, user_id)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    query,
                    int(response_time_ms),
                    False,
                    error_message,
                    user_id
                )
            logger.info(f"Logged error for user: {user_id}, error: {error_message[:100]}")
        except Exception as e:
            logger.error(f"Failed to log error: {str(e)}")

    async def log_success(
        self,
        query: str,
        response_time_ms: float,
        user_id: Optional[str] = None
    ):
        """Log a successful query to the metrics table."""
        pool = await self.get_pool()

        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO query_metrics
                    (query, response_time_ms, success, user_id)
                    VALUES ($1, $2, $3, $4)
                    """,
                    query,
                    int(response_time_ms),
                    True,
                    user_id
                )
            logger.info(f"Logged successful query for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to log success: {str(e)}")

    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics from the database."""
        pool = await self.get_pool()

        try:
            async with pool.acquire() as conn:
                # Get total interactions
                total_interactions = await conn.fetchval("SELECT COUNT(*) FROM chat_logs")

                # Get total errors
                total_errors = await conn.fetchval(
                    "SELECT COUNT(*) FROM query_metrics WHERE success = false"
                )

                # Get average response time
                avg_response_time = await conn.fetchval(
                    "SELECT AVG(response_time_ms) FROM query_metrics WHERE success = true"
                )

                # Get recent interactions (last 24 hours)
                recent_interactions = await conn.fetchval("""
                    SELECT COUNT(*) FROM chat_logs
                    WHERE timestamp > NOW() - INTERVAL '24 hours'
                """)

                stats = {
                    "total_interactions": total_interactions or 0,
                    "total_errors": total_errors or 0,
                    "average_response_time_ms": float(avg_response_time) if avg_response_time else 0,
                    "recent_interactions": recent_interactions or 0,
                    "timestamp": datetime.utcnow().isoformat()
                }

                return stats
        except Exception as e:
            logger.error(f"Failed to get usage stats: {str(e)}")
            raise

    async def get_recent_interactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent chat interactions."""
        pool = await self.get_pool()

        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT query, response, timestamp, response_time_ms, user_id
                    FROM chat_logs
                    ORDER BY timestamp DESC
                    LIMIT $1
                """, limit)

                interactions = []
                for row in rows:
                    interactions.append({
                        "query": row['query'],
                        "response": row['response'],
                        "timestamp": row['timestamp'].isoformat(),
                        "response_time_ms": row['response_time_ms'],
                        "user_id": row['user_id']
                    })

                return interactions
        except Exception as e:
            logger.error(f"Failed to get recent interactions: {str(e)}")
            raise

    async def is_healthy(self) -> bool:
        """
        Check if the Postgres connection is healthy.
        """
        try:
            # This is a basic check - in production you might want to do an actual query
            return self.pool is not None
        except Exception as e:
            logger.error(f"Postgres service health check failed: {str(e)}")
            return False

    async def close(self):
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("PostgresService connection pool closed")