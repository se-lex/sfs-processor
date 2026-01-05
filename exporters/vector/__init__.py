#!/usr/bin/env python3
"""
Vector export functionality for SFS documents.

This module provides tools for converting Swedish legal documents (SFS)
to vector embeddings suitable for semantic search and retrieval.

The vector exporter applies temporal filtering (like md/html mode) to ensure
only current regulations are included in the vector store.
"""

from exporters.vector.vector_export import create_vector_documents, VectorExportConfig
from exporters.vector.chunking import chunk_document, ChunkingStrategy
from exporters.vector.embeddings import EmbeddingProvider, get_embedding_provider

__all__ = [
    'create_vector_documents',
    'VectorExportConfig',
    'chunk_document',
    'ChunkingStrategy',
    'EmbeddingProvider',
    'get_embedding_provider',
]
