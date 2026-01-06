#!/usr/bin/env python3
"""
Vector store backends for SFS documents.

Supported backends:
- PostgreSQL with pgvector extension
- Elasticsearch with dense_vector
- JSON file (for testing/development)
"""

from exporters.vector.backends.base import VectorStoreBackend, VectorRecord
from exporters.vector.backends.postgresql import PostgreSQLBackend
from exporters.vector.backends.elasticsearch import ElasticsearchBackend
from exporters.vector.backends.json_file import JSONFileBackend

__all__ = [
    'VectorStoreBackend',
    'VectorRecord',
    'PostgreSQLBackend',
    'ElasticsearchBackend',
    'JSONFileBackend',
]


def get_backend(backend_type: str, **kwargs) -> VectorStoreBackend:
    """
    Factory function to get a vector store backend.

    Args:
        backend_type: Type of backend ("postgresql", "elasticsearch", "json")
        **kwargs: Backend-specific configuration

    Returns:
        A VectorStoreBackend instance

    Example:
        # PostgreSQL with pgvector
        backend = get_backend("postgresql", connection_string="postgresql://...")

        # Elasticsearch
        backend = get_backend("elasticsearch", hosts=["http://localhost:9200"])

        # JSON file for testing
        backend = get_backend("json", file_path="vectors.json")
    """
    backends = {
        "postgresql": PostgreSQLBackend,
        "postgres": PostgreSQLBackend,
        "pgvector": PostgreSQLBackend,
        "elasticsearch": ElasticsearchBackend,
        "elastic": ElasticsearchBackend,
        "es": ElasticsearchBackend,
        "json": JSONFileBackend,
        "file": JSONFileBackend,
    }

    backend_type_lower = backend_type.lower()
    if backend_type_lower not in backends:
        available = list(set(backends.values()))
        raise ValueError(
            f"Unknown backend type: {backend_type}. "
            f"Available: postgresql, elasticsearch, json"
        )

    return backends[backend_type_lower](**kwargs)
