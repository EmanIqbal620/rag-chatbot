import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Configuration settings for the RAG ingestion pipeline."""

    # Cohere settings
    COHERE_API_KEY: str = os.getenv("COHERE_API_KEY", "")

    # Qdrant settings
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")

    # Book source settings
    BOOK_BASE_URL: str = os.getenv("BOOK_BASE_URL", "https://humanoid-robotics-textbook-4ufa.vercel.app/")

    # Processing settings
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: float = float(os.getenv("CHUNK_OVERLAP", "0.2"))

    # Performance settings
    MAX_PAGES_PER_HOUR: int = int(os.getenv("MAX_PAGES_PER_HOUR", "100"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    # Validation
    def validate(self):
        """Validate that required settings are present."""
        errors = []

        if not self.COHERE_API_KEY:
            errors.append("COHERE_API_KEY is required")

        if not self.QDRANT_URL:
            errors.append("QDRANT_URL is required")

        if errors:
            raise ValueError(f"Missing required configuration: {', '.join(errors)}")

# Global settings instance
settings = Settings()