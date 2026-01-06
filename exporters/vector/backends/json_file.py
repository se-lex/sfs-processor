#!/usr/bin/env python3
"""
JSON file backend for vector storage.

This is a simple file-based backend for testing and development.
It stores vectors in a JSON file and performs brute-force similarity search.

Not recommended for production use with large datasets.
"""

import json
import os
import math
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from exporters.vector.backends.base import VectorStoreBackend, VectorRecord, SearchResult


class JSONFileBackend(VectorStoreBackend):
    """
    JSON file-based vector store for testing and development.

    Stores all records in a single JSON file and performs brute-force
    similarity search. Suitable for small datasets and testing.
    """

    def __init__(
        self,
        file_path: str = "sfs_vectors.json",
        similarity: str = "cosine",  # "cosine", "euclidean", "dot_product"
        pretty_print: bool = True
    ):
        """
        Initialize JSON file backend.

        Args:
            file_path: Path to the JSON file
            similarity: Similarity metric for search
            pretty_print: Whether to format JSON with indentation
        """
        self.file_path = Path(file_path)
        self.similarity = similarity
        self.pretty_print = pretty_print
        self._dimensions = None
        self._data = None

    def _load_data(self) -> Dict[str, Any]:
        """Load data from JSON file."""
        if self._data is not None:
            return self._data

        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            except json.JSONDecodeError:
                self._data = {"records": {}, "metadata": {}}
        else:
            self._data = {"records": {}, "metadata": {}}

        return self._data

    def _save_data(self) -> None:
        """Save data to JSON file."""
        if self._data is None:
            return

        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        indent = 2 if self.pretty_print else None
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=indent, default=str)

    def initialize(self, dimensions: int, **kwargs) -> None:
        """Initialize the backend."""
        self._dimensions = dimensions
        data = self._load_data()
        data['metadata'] = {
            "dimensions": dimensions,
            "similarity": self.similarity,
            "created_at": datetime.now().isoformat()
        }
        self._save_data()
        print(f"JSON file backend initialized at {self.file_path}")

    def insert(self, record: VectorRecord) -> None:
        """Insert a single record."""
        self.insert_batch([record])

    def insert_batch(self, records: List[VectorRecord]) -> int:
        """Insert multiple records."""
        if not records:
            return 0

        data = self._load_data()

        for record in records:
            data['records'][record.id] = record.to_dict()

        self._save_data()
        return len(records)

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _euclidean_distance(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate Euclidean distance between two vectors."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec1, vec2)))

    def _dot_product(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate dot product between two vectors."""
        return sum(a * b for a, b in zip(vec1, vec2))

    def _calculate_similarity(self, vec1: List[float], vec2: List[float]) -> Tuple[float, float]:
        """Calculate similarity and distance between vectors."""
        if self.similarity == "cosine":
            sim = self._cosine_similarity(vec1, vec2)
            dist = 1 - sim
        elif self.similarity == "euclidean":
            dist = self._euclidean_distance(vec1, vec2)
            sim = 1 / (1 + dist)
        elif self.similarity == "dot_product":
            sim = self._dot_product(vec1, vec2)
            dist = -sim
        else:
            sim = self._cosine_similarity(vec1, vec2)
            dist = 1 - sim

        return sim, dist

    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar vectors using brute force."""
        data = self._load_data()
        results = []

        for record_id, record_dict in data.get('records', {}).items():
            # Apply filters
            if filters:
                skip = False
                for key, value in filters.items():
                    if record_dict.get(key) != value:
                        skip = True
                        break
                if skip:
                    continue

            record = VectorRecord.from_dict(record_dict)
            score, distance = self._calculate_similarity(query_vector, record.vector)

            results.append(SearchResult(
                record=record,
                score=score,
                distance=distance
            ))

        # Sort by score (descending) and return top k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def delete_by_document(self, document_id: str) -> int:
        """Delete all records for a document."""
        data = self._load_data()
        deleted = 0

        # Find and delete records with matching document_id
        to_delete = [
            record_id for record_id, record_dict in data.get('records', {}).items()
            if record_dict.get('document_id') == document_id
        ]

        for record_id in to_delete:
            del data['records'][record_id]
            deleted += 1

        if deleted > 0:
            self._save_data()

        return deleted

    def get_by_id(self, record_id: str) -> Optional[VectorRecord]:
        """Get a record by ID."""
        data = self._load_data()
        record_dict = data.get('records', {}).get(record_id)

        if record_dict:
            return VectorRecord.from_dict(record_dict)
        return None

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records in the store."""
        data = self._load_data()

        if not filters:
            return len(data.get('records', {}))

        count = 0
        for record_dict in data.get('records', {}).values():
            match = True
            for key, value in filters.items():
                if record_dict.get(key) != value:
                    match = False
                    break
            if match:
                count += 1

        return count

    def close(self) -> None:
        """Close and save any pending data."""
        if self._data is not None:
            self._save_data()
        self._data = None

    def health_check(self) -> Tuple[bool, str]:
        """Check backend health."""
        try:
            data = self._load_data()
            count = len(data.get('records', {}))
            return True, f"JSON file backend at {self.file_path}, {count} records"
        except Exception as e:
            return False, f"JSON file error: {e}"

    def export_for_import(self, output_path: Optional[str] = None) -> str:
        """
        Export data in a format suitable for importing into other backends.

        Args:
            output_path: Path for export file (defaults to {file_path}_export.json)

        Returns:
            Path to the exported file
        """
        if output_path is None:
            output_path = str(self.file_path).replace('.json', '_export.json')

        data = self._load_data()

        # Export records as a list for easier importing
        export_data = {
            "metadata": data.get('metadata', {}),
            "records": list(data.get('records', {}).values())
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

        print(f"Exported {len(export_data['records'])} records to {output_path}")
        return output_path
