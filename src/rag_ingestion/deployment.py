"""
Deployment validation module for the RAG Book Ingestion Pipeline.
Handles validation of deployment configurations and external service connectivity.
"""

import requests
from typing import Optional
from urllib.parse import urljoin

from config.settings import settings


def validate_book_site_accessibility(base_url: str = None) -> bool:
    """
    Validate that the target book site is accessible.

    Args:
        base_url: The base URL to validate. If None, uses settings.BOOK_BASE_URL

    Returns:
        bool: True if the site is accessible, False otherwise
    """
    if base_url is None:
        base_url = settings.BOOK_BASE_URL

    try:
        response = requests.head(base_url, timeout=settings.REQUEST_TIMEOUT)
        return response.status_code == 200
    except requests.RequestException:
        return False


def validate_cohere_accessibility() -> bool:
    """
    Validate that Cohere API is accessible with the provided API key.

    Returns:
        bool: True if Cohere API is accessible, False otherwise
    """
    try:
        import cohere

        co = cohere.Client(settings.COHERE_API_KEY)
        # Try a simple model list call to validate the API key
        co.models.list()
        return True
    except Exception:
        return False


def validate_qdrant_accessibility() -> bool:
    """
    Validate that Qdrant is accessible with the provided credentials.

    Returns:
        bool: True if Qdrant is accessible, False otherwise
    """
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=settings.REQUEST_TIMEOUT
        )
        # Try to get collections list to validate connection
        client.get_collections()
        return True
    except Exception:
        return False


def validate_deployment() -> dict:
    """
    Validate the entire deployment setup.

    Returns:
        dict: A dictionary with validation results for each service
    """
    results = {
        "book_site": validate_book_site_accessibility(),
        "cohere": validate_cohere_accessibility(),
        "qdrant": validate_qdrant_accessibility(),
    }

    return results


def ensure_environment_ready() -> bool:
    """
    Ensure all required services are accessible before starting ingestion.

    Returns:
        bool: True if all services are accessible, False otherwise
    """
    validation_results = validate_deployment()

    all_ready = all(validation_results.values())

    if not all_ready:
        print("Deployment validation failed:")
        for service, is_ready in validation_results.items():
            status = "✓" if is_ready else "✗"
            print(f"  {status} {service}: {'Ready' if is_ready else 'Not accessible'}")

    return all_ready


if __name__ == "__main__":
    # Test the deployment validation
    print("Validating deployment setup...")
    results = validate_deployment()

    print("\nResults:")
    for service, is_ready in results.items():
        status = "✓" if is_ready else "✗"
        print(f"  {status} {service}: {'Ready' if is_ready else 'Not accessible'}")

    all_ready = ensure_environment_ready()
    print(f"\nOverall: {'All services ready' if all_ready else 'Some services not ready'}")