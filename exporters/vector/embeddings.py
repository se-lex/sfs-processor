#!/usr/bin/env python3
"""
Embedding module for SFS documents.

This module provides embedding functionality using state-of-the-art embedding models.
Currently supports:
- OpenAI text-embedding-3-large (best quality, 3072 dimensions)
- OpenAI text-embedding-3-small (faster, cheaper, 1536 dimensions)

The embeddings are optimized for Swedish legal text retrieval.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Union
import time


class EmbeddingModel(Enum):
    """Available embedding models."""
    # OpenAI models - text-embedding-3 series (best for multilingual including Swedish)
    OPENAI_3_LARGE = "text-embedding-3-large"   # 3072 dims, best quality
    OPENAI_3_SMALL = "text-embedding-3-small"   # 1536 dims, faster/cheaper

    # Legacy OpenAI model (for reference)
    OPENAI_ADA_002 = "text-embedding-ada-002"   # 1536 dims, older model


@dataclass
class EmbeddingResult:
    """Result of an embedding operation."""
    text: str                           # Original text
    embedding: List[float]              # The embedding vector
    model: str                          # Model used
    dimensions: int                     # Vector dimensions
    tokens_used: int                    # Tokens consumed
    metadata: Optional[dict] = None     # Additional metadata


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> EmbeddingResult:
        """Generate embedding for a single text."""
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[EmbeddingResult]:
        """Generate embeddings for multiple texts (batch)."""
        pass

    @abstractmethod
    def get_dimensions(self) -> int:
        """Return the embedding vector dimensions."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider using text-embedding-3 models.

    The text-embedding-3-large model is recommended for best quality
    Swedish legal text retrieval. It has 3072 dimensions and excellent
    multilingual support.

    Environment variables:
        OPENAI_API_KEY: Your OpenAI API key
    """

    # Dimension mappings for each model
    MODEL_DIMENSIONS = {
        EmbeddingModel.OPENAI_3_LARGE.value: 3072,
        EmbeddingModel.OPENAI_3_SMALL.value: 1536,
        EmbeddingModel.OPENAI_ADA_002.value: 1536,
    }

    # Token limits per model (for reference)
    MODEL_MAX_TOKENS = {
        EmbeddingModel.OPENAI_3_LARGE.value: 8191,
        EmbeddingModel.OPENAI_3_SMALL.value: 8191,
        EmbeddingModel.OPENAI_ADA_002.value: 8191,
    }

    def __init__(
        self,
        model: EmbeddingModel = EmbeddingModel.OPENAI_3_LARGE,
        api_key: Optional[str] = None,
        dimensions: Optional[int] = None,
        batch_size: int = 100,
        retry_attempts: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize the OpenAI embedding provider.

        Args:
            model: The embedding model to use
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            dimensions: Optional reduced dimensions (for text-embedding-3 models)
            batch_size: Number of texts to embed in one API call
            retry_attempts: Number of retry attempts on failure
            retry_delay: Base delay between retries (exponential backoff)
        """
        self.model = model
        self.model_name = model.value
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.batch_size = batch_size
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        # Handle custom dimensions (text-embedding-3 supports dimension reduction)
        if dimensions is not None:
            if model not in [EmbeddingModel.OPENAI_3_LARGE, EmbeddingModel.OPENAI_3_SMALL]:
                raise ValueError(f"Custom dimensions not supported for {model.value}")
            max_dims = self.MODEL_DIMENSIONS[self.model_name]
            if dimensions > max_dims:
                raise ValueError(f"Dimensions cannot exceed {max_dims} for {model.value}")
            self._dimensions = dimensions
        else:
            self._dimensions = self.MODEL_DIMENSIONS[self.model_name]

        self._client = None

    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                    "or pass api_key to the constructor."
                )
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "OpenAI package not installed. Install with: pip install openai"
                )
        return self._client

    def embed_text(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            EmbeddingResult with the embedding vector
        """
        results = self.embed_texts([text])
        return results[0]

    def embed_texts(self, texts: List[str]) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.

        Uses batching for efficiency with automatic retry on failures.

        Args:
            texts: List of texts to embed

        Returns:
            List of EmbeddingResult objects
        """
        client = self._get_client()
        results = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_results = self._embed_batch_with_retry(client, batch)
            results.extend(batch_results)

        return results

    def _embed_batch_with_retry(self, client, texts: List[str]) -> List[EmbeddingResult]:
        """Embed a batch of texts with retry logic."""
        last_error = None

        for attempt in range(self.retry_attempts):
            try:
                return self._embed_batch(client, texts)
            except Exception as e:
                last_error = e
                if attempt < self.retry_attempts - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Embedding attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)

        raise RuntimeError(f"Failed to embed texts after {self.retry_attempts} attempts: {last_error}")

    def _embed_batch(self, client, texts: List[str]) -> List[EmbeddingResult]:
        """Embed a batch of texts."""
        # Build request parameters
        params = {
            "model": self.model_name,
            "input": texts,
        }

        # Add dimensions parameter for text-embedding-3 models if custom
        if self._dimensions != self.MODEL_DIMENSIONS[self.model_name]:
            params["dimensions"] = self._dimensions

        response = client.embeddings.create(**params)

        results = []
        for i, item in enumerate(response.data):
            results.append(EmbeddingResult(
                text=texts[i],
                embedding=item.embedding,
                model=self.model_name,
                dimensions=len(item.embedding),
                tokens_used=response.usage.total_tokens // len(texts),  # Approximate per-text
                metadata={
                    "index": item.index,
                }
            ))

        return results

    def get_dimensions(self) -> int:
        """Return the embedding vector dimensions."""
        return self._dimensions

    def get_model_name(self) -> str:
        """Return the model name."""
        return self.model_name


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Mock embedding provider for testing without API calls.

    Generates deterministic pseudo-random vectors based on text content.
    """

    def __init__(self, dimensions: int = 3072, **kwargs):
        """
        Initialize mock provider.

        Args:
            dimensions: Number of dimensions for mock vectors
            **kwargs: Ignored (for compatibility with other providers)
        """
        self._dimensions = dimensions

    def embed_text(self, text: str) -> EmbeddingResult:
        """Generate a mock embedding for testing."""
        # Generate deterministic pseudo-random vector based on text hash
        import hashlib
        text_hash = hashlib.sha256(text.encode()).hexdigest()

        # Convert hash to floats
        embedding = []
        for i in range(self._dimensions):
            # Use different parts of the hash
            idx = (i * 4) % 64
            hex_chunk = text_hash[idx:idx+4] or text_hash[:4]
            value = (int(hex_chunk, 16) / 65535) * 2 - 1  # Normalize to [-1, 1]
            embedding.append(value)

        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model="mock",
            dimensions=self._dimensions,
            tokens_used=len(text) // 4,  # Rough estimate
            metadata={"is_mock": True}
        )

    def embed_texts(self, texts: List[str]) -> List[EmbeddingResult]:
        """Generate mock embeddings for multiple texts."""
        return [self.embed_text(text) for text in texts]

    def get_dimensions(self) -> int:
        """Return the embedding vector dimensions."""
        return self._dimensions

    def get_model_name(self) -> str:
        """Return the model name."""
        return "mock"


def get_embedding_provider(
    provider: str = "openai",
    model: Optional[Union[str, EmbeddingModel]] = None,
    **kwargs
) -> EmbeddingProvider:
    """
    Factory function to get an embedding provider.

    Args:
        provider: Provider name ("openai" or "mock")
        model: Model to use (for OpenAI: "text-embedding-3-large", etc.)
        **kwargs: Additional arguments passed to the provider

    Returns:
        An EmbeddingProvider instance

    Example:
        # Best quality embeddings
        provider = get_embedding_provider("openai", model="text-embedding-3-large")

        # Faster/cheaper embeddings
        provider = get_embedding_provider("openai", model="text-embedding-3-small")

        # Testing without API
        provider = get_embedding_provider("mock")
    """
    if provider == "openai":
        if model is None:
            model = EmbeddingModel.OPENAI_3_LARGE
        elif isinstance(model, str):
            # Convert string to enum
            model_map = {m.value: m for m in EmbeddingModel}
            if model not in model_map:
                raise ValueError(f"Unknown model: {model}. Available: {list(model_map.keys())}")
            model = model_map[model]

        return OpenAIEmbeddingProvider(model=model, **kwargs)

    elif provider == "mock":
        return MockEmbeddingProvider(**kwargs)

    else:
        raise ValueError(f"Unknown provider: {provider}. Available: openai, mock")


# Convenience functions for common use cases

def embed_document_chunks(
    chunks: List['DocumentChunk'],
    provider: Optional[EmbeddingProvider] = None,
    show_progress: bool = True
) -> List[tuple]:
    """
    Embed a list of document chunks.

    Args:
        chunks: List of DocumentChunk objects
        provider: Embedding provider (defaults to OpenAI text-embedding-3-large)
        show_progress: Whether to show progress indicator

    Returns:
        List of (chunk, embedding_result) tuples
    """
    if provider is None:
        provider = get_embedding_provider("openai")

    texts = [chunk.content for chunk in chunks]
    total = len(texts)

    if show_progress:
        print(f"Embedding {total} chunks using {provider.get_model_name()}...")

    results = provider.embed_texts(texts)

    if show_progress:
        print(f"Completed embedding {total} chunks")

    return list(zip(chunks, results))
