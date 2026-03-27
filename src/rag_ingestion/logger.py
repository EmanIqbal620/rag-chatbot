"""
Logging module for the RAG Book Ingestion Pipeline.
Provides structured logging for ingestion pipeline operations.
"""

import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('rag_ingestion.log')
    ]
)

# Create logger instance for the ingestion pipeline
logger = logging.getLogger('rag_ingestion')

# Set appropriate log level
logger.setLevel(logging.INFO)


class IngestionLogger:
    """
    A structured logger specifically for the RAG ingestion pipeline.
    Provides methods for logging different stages of the ingestion process.
    """

    def __init__(self, name: str = "rag_ingestion"):
        self.logger = logging.getLogger(name)

    def log_crawl_start(self, url: str):
        """Log the start of a crawling operation."""
        self.logger.info(f"Starting crawl for URL: {url}")

    def log_crawl_success(self, url: str, content_length: int):
        """Log successful crawling of a URL."""
        self.logger.info(f"Crawled {url} successfully, content length: {content_length}")

    def log_crawl_error(self, url: str, error: str):
        """Log an error during crawling."""
        self.logger.error(f"Crawling failed for {url}: {error}")

    def log_extraction_start(self, url: str):
        """Log the start of text extraction."""
        self.logger.info(f"Starting text extraction for: {url}")

    def log_extraction_success(self, url: str, text_length: int):
        """Log successful text extraction."""
        self.logger.info(f"Text extraction successful for {url}, extracted {text_length} characters")

    def log_extraction_error(self, url: str, error: str):
        """Log an error during text extraction."""
        self.logger.error(f"Text extraction failed for {url}: {error}")

    def log_chunking_start(self, source: str):
        """Log the start of text chunking."""
        self.logger.info(f"Starting chunking for: {source}")

    def log_chunking_success(self, source: str, num_chunks: int):
        """Log successful text chunking."""
        self.logger.info(f"Chunking successful for {source}, created {num_chunks} chunks")

    def log_chunking_error(self, source: str, error: str):
        """Log an error during text chunking."""
        self.logger.error(f"Chunking failed for {source}: {error}")

    def log_embedding_start(self, num_chunks: int):
        """Log the start of embedding generation."""
        self.logger.info(f"Starting embedding generation for {num_chunks} chunks")

    def log_embedding_success(self, num_chunks: int, duration: float):
        """Log successful embedding generation."""
        self.logger.info(f"Embedding generation successful for {num_chunks} chunks, took {duration:.2f}s")

    def log_embedding_error(self, error: str):
        """Log an error during embedding generation."""
        self.logger.error(f"Embedding generation failed: {error}")

    def log_storage_start(self, num_vectors: int):
        """Log the start of vector storage."""
        self.logger.info(f"Starting storage for {num_vectors} vectors")

    def log_storage_success(self, num_vectors: int):
        """Log successful vector storage."""
        self.logger.info(f"Successfully stored {num_vectors} vectors")

    def log_storage_error(self, error: str):
        """Log an error during vector storage."""
        self.logger.error(f"Vector storage failed: {error}")

    def log_ingestion_start(self, source_url: str):
        """Log the start of the entire ingestion process."""
        self.logger.info(f"Starting ingestion pipeline for: {source_url}")

    def log_ingestion_complete(self, source_url: str, total_pages: int, duration: float):
        """Log completion of the entire ingestion process."""
        self.logger.info(f"Ingestion complete for {source_url}, processed {total_pages} pages in {duration:.2f}s")

    def log_ingestion_error(self, source_url: str, error: str):
        """Log an error during the ingestion process."""
        self.logger.error(f"Ingestion failed for {source_url}: {error}")

    def log_progress(self, current: int, total: int, description: str = ""):
        """Log progress of a multi-step operation."""
        percentage = (current / total) * 100
        self.logger.info(f"Progress: {current}/{total} ({percentage:.1f}%) - {description}")


# Global instance of the ingestion logger
ingestion_logger = IngestionLogger()


def setup_logger(name: str, log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Function to setup a logger with file and console handlers.

    Args:
        name: Name of the logger
        log_file: Optional file path for logging to file
        level: Logging level

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Convenience functions for common logging operations
def info(message: str, extra: Optional[Dict[str, Any]] = None):
    """Log an info message."""
    logger.info(message, extra=extra)


def error(message: str, extra: Optional[Dict[str, Any]] = None):
    """Log an error message."""
    logger.error(message, extra=extra)


def warning(message: str, extra: Optional[Dict[str, Any]] = None):
    """Log a warning message."""
    logger.warning(message, extra=extra)


def debug(message: str, extra: Optional[Dict[str, Any]] = None):
    """Log a debug message."""
    logger.debug(message, extra=extra)


# Context manager for timing operations
from contextlib import contextmanager
import time


@contextmanager
def log_time(operation_name: str):
    """
    Context manager to log the execution time of operations.

    Args:
        operation_name: Name of the operation being timed
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"{operation_name} completed in {duration:.2f} seconds")