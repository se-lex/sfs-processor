#!/usr/bin/env python3
"""
Base class and interfaces for vector store backends.

This module defines the abstract interface that all vector store
backends must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime


@dataclass
class VectorRecord:
    """
    A record to be stored in the vector database.

    Contains the embedding vector along with metadata for retrieval.
    """
    # Unique identifier for this record
    id: str

    # The embedding vector
    vector: List[float]

    # Content that was embedded
    content: str

    # Document reference
    document_id: str                     # beteckning (e.g., "2024:100")
    document_title: Optional[str] = None  # rubrik

    # Structural metadata
    chunk_index: int = 0
    total_chunks: int = 1
    chapter: Optional[str] = None        # e.g., "1 kap."
    paragraph: Optional[str] = None      # e.g., "1 §"
    section_type: Optional[str] = None   # kapitel, paragraf, etc.

    # Document metadata
    departement: Optional[str] = None
    effective_date: Optional[str] = None    # ikraft_datum - when regulation takes effect
    issued_date: Optional[str] = None       # utfardad_datum - when regulation was issued
    repealed: bool = False                  # upphavd - if regulation is repealed
    expiration_date: Optional[str] = None   # upphor_datum - when regulation expires

    # Technical metadata
    embedding_model: Optional[str] = None
    dimensions: int = 0
    created_at: Optional[datetime] = None

    # Additional metadata as dict
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary for serialization."""
        return {
            'id': self.id,
            'vector': self.vector,
            'content': self.content,
            'document_id': self.document_id,
            'document_title': self.document_title,
            'chunk_index': self.chunk_index,
            'total_chunks': self.total_chunks,
            'chapter': self.chapter,
            'paragraph': self.paragraph,
            'section_type': self.section_type,
            'departement': self.departement,
            'effective_date': self.effective_date,
            'issued_date': self.issued_date,
            'repealed': self.repealed,
            'expiration_date': self.expiration_date,
            'embedding_model': self.embedding_model,
            'dimensions': self.dimensions,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VectorRecord':
        """Create a VectorRecord from a dictionary."""
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            id=data['id'],
            vector=data['vector'],
            content=data['content'],
            document_id=data['document_id'],
            document_title=data.get('document_title'),
            chunk_index=data.get('chunk_index', 0),
            total_chunks=data.get('total_chunks', 1),
            chapter=data.get('chapter'),
            paragraph=data.get('paragraph'),
            section_type=data.get('section_type'),
            departement=data.get('departement'),
            effective_date=data.get('effective_date'),
            issued_date=data.get('issued_date'),
            repealed=data.get('repealed', False),
            expiration_date=data.get('expiration_date'),
            embedding_model=data.get('embedding_model'),
            dimensions=data.get('dimensions', 0),
            created_at=created_at,
            metadata=data.get('metadata', {}),
        )


@dataclass
class SearchResult:
    """Result from a vector similarity search."""
    record: VectorRecord
    score: float                         # Similarity score
    distance: Optional[float] = None     # Distance metric (if applicable)


class VectorStoreBackend(ABC):
    """
    Abstract base class for vector store backends.

    All backend implementations must implement these methods
    to provide a consistent interface for storing and searching vectors.
    """

    @abstractmethod
    def initialize(self, dimensions: int, **kwargs) -> None:
        """
        Initialize the backend (create tables, indices, etc.).

        Args:
            dimensions: The dimensionality of vectors to store
            **kwargs: Backend-specific initialization options
        """
        pass

    @abstractmethod
    def insert(self, record: VectorRecord) -> None:
        """
        Insert a single record into the store.

        Args:
            record: The VectorRecord to insert
        """
        pass

    @abstractmethod
    def insert_batch(self, records: List[VectorRecord]) -> int:
        """
        Insert multiple records in a batch.

        Args:
            records: List of VectorRecords to insert

        Returns:
            Number of records successfully inserted
        """
        pass

    @abstractmethod
    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for similar vectors.

        Args:
            query_vector: The vector to search for
            limit: Maximum number of results to return
            filters: Optional filters to apply (e.g., {"document_id": "2024:100"})

        Returns:
            List of SearchResult objects ordered by similarity
        """
        pass

    @abstractmethod
    def delete_by_document(self, document_id: str) -> int:
        """
        Delete all records for a specific document.

        Args:
            document_id: The document identifier (beteckning)

        Returns:
            Number of records deleted
        """
        pass

    @abstractmethod
    def get_by_id(self, record_id: str) -> Optional[VectorRecord]:
        """
        Retrieve a specific record by ID.

        Args:
            record_id: The record identifier

        Returns:
            The VectorRecord if found, None otherwise
        """
        pass

    @abstractmethod
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records in the store.

        Args:
            filters: Optional filters to apply

        Returns:
            Number of records matching the filters
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close any open connections."""
        pass

    def upsert(self, record: VectorRecord) -> None:
        """
        Insert or update a record.

        Default implementation deletes existing and inserts new.
        Backends may override with more efficient implementations.

        Args:
            record: The VectorRecord to upsert
        """
        existing = self.get_by_id(record.id)
        if existing:
            self.delete_by_document(record.document_id)
        self.insert(record)

    def upsert_batch(self, records: List[VectorRecord]) -> int:
        """
        Insert or update multiple records.

        Default implementation processes records individually.
        Backends may override with more efficient implementations.

        Args:
            records: List of VectorRecords to upsert

        Returns:
            Number of records successfully upserted
        """
        # Group by document_id for efficient deletion
        doc_ids = set(r.document_id for r in records)
        for doc_id in doc_ids:
            self.delete_by_document(doc_id)

        return self.insert_batch(records)

    def health_check(self) -> Tuple[bool, str]:
        """
        Check if the backend is healthy and accessible.

        Returns:
            Tuple of (is_healthy, message)
        """
        try:
            count = self.count()
            return True, f"Backend healthy, {count} records"
        except Exception as e:
            return False, f"Backend error: {e}"
