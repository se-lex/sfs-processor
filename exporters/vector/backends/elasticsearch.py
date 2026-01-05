#!/usr/bin/env python3
"""
Elasticsearch backend for vector storage.

This backend uses Elasticsearch's dense_vector field type for vector similarity search.
Supports both exact and approximate (HNSW) similarity search.

Requirements:
    - Elasticsearch 8.0+ (for native kNN support)
    - elasticsearch-py (pip install elasticsearch)

Environment variables:
    - ELASTICSEARCH_HOSTS: Comma-separated list of hosts
    - ELASTICSEARCH_API_KEY: API key for authentication
    - ELASTICSEARCH_USERNAME / ELASTICSEARCH_PASSWORD: Basic auth
"""

import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from exporters.vector.backends.base import VectorStoreBackend, VectorRecord, SearchResult


class ElasticsearchBackend(VectorStoreBackend):
    """
    Elasticsearch vector store backend using dense_vector fields.

    Supports both exact kNN and approximate (HNSW) similarity search
    with cosine, dot_product, or l2_norm similarity metrics.
    """

    DEFAULT_INDEX_NAME = "sfs_vectors"

    def __init__(
        self,
        hosts: Optional[List[str]] = None,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        cloud_id: Optional[str] = None,
        index_name: str = DEFAULT_INDEX_NAME,
        similarity: str = "cosine",  # "cosine", "dot_product", "l2_norm"
        use_approximate_knn: bool = True
    ):
        """
        Initialize Elasticsearch backend.

        Args:
            hosts: List of Elasticsearch hosts
            api_key: API key for authentication
            username: Username for basic auth
            password: Password for basic auth
            cloud_id: Elastic Cloud ID (alternative to hosts)
            index_name: Name of the index
            similarity: Similarity metric
            use_approximate_knn: Use HNSW for approximate kNN (faster)
        """
        self.index_name = index_name
        self.similarity = similarity
        self.use_approximate_knn = use_approximate_knn
        self._dimensions = None
        self._client = None

        # Build connection config
        self._hosts = hosts or self._parse_hosts(
            os.environ.get('ELASTICSEARCH_HOSTS', 'http://localhost:9200')
        )
        self._api_key = api_key or os.environ.get('ELASTICSEARCH_API_KEY')
        self._username = username or os.environ.get('ELASTICSEARCH_USERNAME')
        self._password = password or os.environ.get('ELASTICSEARCH_PASSWORD')
        self._cloud_id = cloud_id or os.environ.get('ELASTICSEARCH_CLOUD_ID')

    def _parse_hosts(self, hosts_str: str) -> List[str]:
        """Parse comma-separated hosts string."""
        return [h.strip() for h in hosts_str.split(',') if h.strip()]

    def _get_client(self):
        """Get or create Elasticsearch client."""
        if self._client is None:
            try:
                from elasticsearch import Elasticsearch
            except ImportError:
                raise ImportError(
                    "Elasticsearch package not installed. Install with: "
                    "pip install elasticsearch"
                )

            # Build client with available credentials
            client_kwargs = {}

            if self._cloud_id:
                client_kwargs['cloud_id'] = self._cloud_id
            else:
                client_kwargs['hosts'] = self._hosts

            if self._api_key:
                client_kwargs['api_key'] = self._api_key
            elif self._username and self._password:
                client_kwargs['basic_auth'] = (self._username, self._password)

            self._client = Elasticsearch(**client_kwargs)

        return self._client

    def initialize(self, dimensions: int, **kwargs) -> None:
        """
        Initialize the Elasticsearch index.

        Creates the index with appropriate mappings for vector search.

        Args:
            dimensions: Vector dimensionality
            **kwargs: Additional options (e.g., number_of_shards)
        """
        self._dimensions = dimensions
        client = self._get_client()

        # Check if index exists
        if client.indices.exists(index=self.index_name):
            print(f"Elasticsearch index '{self.index_name}' already exists")
            return

        # Build index settings
        settings = {
            "number_of_shards": kwargs.get('number_of_shards', 1),
            "number_of_replicas": kwargs.get('number_of_replicas', 0)
        }

        # Build mappings
        mappings = {
            "properties": {
                "id": {"type": "keyword"},
                "vector": {
                    "type": "dense_vector",
                    "dims": dimensions,
                    "index": self.use_approximate_knn,
                    "similarity": self.similarity
                },
                "content": {
                    "type": "text",
                    "analyzer": "swedish"  # Use Swedish analyzer
                },
                "document_id": {"type": "keyword"},
                "document_title": {"type": "text"},
                "chunk_index": {"type": "integer"},
                "total_chunks": {"type": "integer"},
                "chapter": {"type": "keyword"},
                "paragraph": {"type": "keyword"},
                "section_type": {"type": "keyword"},
                "departement": {"type": "keyword"},
                "ikraft_datum": {"type": "date", "format": "yyyy-MM-dd||strict_date"},
                "utfardad_datum": {"type": "date", "format": "yyyy-MM-dd||strict_date"},
                "embedding_model": {"type": "keyword"},
                "dimensions": {"type": "integer"},
                "created_at": {"type": "date"},
                "metadata": {"type": "object", "enabled": False}
            }
        }

        # Create index
        client.indices.create(
            index=self.index_name,
            settings=settings,
            mappings=mappings
        )

        print(f"Elasticsearch index '{self.index_name}' created with {dimensions}-dimensional vectors")

    def _record_to_doc(self, record: VectorRecord) -> Dict[str, Any]:
        """Convert VectorRecord to Elasticsearch document."""
        doc = {
            "id": record.id,
            "vector": record.vector,
            "content": record.content,
            "document_id": record.document_id,
            "document_title": record.document_title,
            "chunk_index": record.chunk_index,
            "total_chunks": record.total_chunks,
            "chapter": record.chapter,
            "paragraph": record.paragraph,
            "section_type": record.section_type,
            "departement": record.departement,
            "embedding_model": record.embedding_model,
            "dimensions": record.dimensions,
            "created_at": record.created_at.isoformat() if record.created_at else datetime.now().isoformat(),
            "metadata": record.metadata
        }

        # Handle date fields (Elasticsearch expects proper format or null)
        if record.ikraft_datum:
            doc["ikraft_datum"] = record.ikraft_datum
        if record.utfardad_datum:
            doc["utfardad_datum"] = record.utfardad_datum

        return doc

    def _doc_to_record(self, doc: Dict[str, Any]) -> VectorRecord:
        """Convert Elasticsearch document to VectorRecord."""
        source = doc.get('_source', doc)

        created_at = source.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                created_at = None

        return VectorRecord(
            id=source.get('id', doc.get('_id', '')),
            vector=source.get('vector', []),
            content=source.get('content', ''),
            document_id=source.get('document_id', ''),
            document_title=source.get('document_title'),
            chunk_index=source.get('chunk_index', 0),
            total_chunks=source.get('total_chunks', 1),
            chapter=source.get('chapter'),
            paragraph=source.get('paragraph'),
            section_type=source.get('section_type'),
            departement=source.get('departement'),
            ikraft_datum=source.get('ikraft_datum'),
            utfardad_datum=source.get('utfardad_datum'),
            embedding_model=source.get('embedding_model'),
            dimensions=source.get('dimensions', 0),
            created_at=created_at,
            metadata=source.get('metadata', {})
        )

    def insert(self, record: VectorRecord) -> None:
        """Insert a single record."""
        self.insert_batch([record])

    def insert_batch(self, records: List[VectorRecord]) -> int:
        """Insert multiple records using bulk API."""
        if not records:
            return 0

        client = self._get_client()

        # Build bulk operations
        operations = []
        for record in records:
            operations.append({"index": {"_index": self.index_name, "_id": record.id}})
            operations.append(self._record_to_doc(record))

        # Execute bulk request
        response = client.bulk(operations=operations, refresh=True)

        # Count successful inserts
        inserted = sum(1 for item in response['items'] if item['index'].get('result') in ['created', 'updated'])

        if response.get('errors'):
            errors = [
                item['index']['error']
                for item in response['items']
                if 'error' in item.get('index', {})
            ]
            for error in errors[:5]:  # Show first 5 errors
                print(f"Elasticsearch error: {error}")

        return inserted

    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar vectors using kNN."""
        client = self._get_client()

        # Build filter query
        filter_query = []
        if filters:
            for key, value in filters.items():
                if key in ['document_id', 'chapter', 'paragraph', 'section_type', 'departement']:
                    filter_query.append({"term": {key: value}})

        # Build kNN query
        knn = {
            "field": "vector",
            "query_vector": query_vector,
            "k": limit,
            "num_candidates": limit * 10  # Search more candidates for better accuracy
        }

        if filter_query:
            knn["filter"] = {"bool": {"must": filter_query}}

        # Execute search
        response = client.search(
            index=self.index_name,
            knn=knn,
            size=limit,
            _source=True
        )

        # Convert results
        results = []
        for hit in response['hits']['hits']:
            record = self._doc_to_record(hit)
            score = hit.get('_score', 0)

            results.append(SearchResult(
                record=record,
                score=score,
                distance=1 - score if self.similarity == "cosine" else None
            ))

        return results

    def delete_by_document(self, document_id: str) -> int:
        """Delete all records for a document."""
        client = self._get_client()

        response = client.delete_by_query(
            index=self.index_name,
            query={"term": {"document_id": document_id}},
            refresh=True
        )

        return response.get('deleted', 0)

    def get_by_id(self, record_id: str) -> Optional[VectorRecord]:
        """Get a record by ID."""
        client = self._get_client()

        try:
            response = client.get(index=self.index_name, id=record_id)
            return self._doc_to_record(response)
        except Exception:
            return None

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records in the index."""
        client = self._get_client()

        query = {"match_all": {}}
        if filters:
            must = []
            for key, value in filters.items():
                if key in ['document_id', 'chapter', 'paragraph', 'section_type', 'departement']:
                    must.append({"term": {key: value}})
            if must:
                query = {"bool": {"must": must}}

        response = client.count(index=self.index_name, query=query)
        return response.get('count', 0)

    def close(self) -> None:
        """Close Elasticsearch client."""
        if self._client:
            self._client.close()
            self._client = None

    def health_check(self) -> Tuple[bool, str]:
        """Check Elasticsearch connectivity."""
        try:
            client = self._get_client()
            health = client.cluster.health()
            status = health.get('status', 'unknown')
            count = self.count()
            return True, f"Elasticsearch status: {status}, {count} records in {self.index_name}"
        except Exception as e:
            return False, f"Elasticsearch error: {e}"

    def hybrid_search(
        self,
        query_vector: List[float],
        query_text: str,
        limit: int = 10,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining vector similarity and text search.

        This is useful for Swedish legal documents where exact term matching
        can complement semantic search.

        Args:
            query_vector: Vector embedding of the query
            query_text: Text query for BM25 matching
            limit: Number of results to return
            vector_weight: Weight for vector similarity (0-1)
            text_weight: Weight for text similarity (0-1)
            filters: Optional filters

        Returns:
            List of SearchResult objects
        """
        client = self._get_client()

        # Build filter
        filter_query = []
        if filters:
            for key, value in filters.items():
                if key in ['document_id', 'chapter', 'paragraph', 'section_type', 'departement']:
                    filter_query.append({"term": {key: value}})

        # Build hybrid query using script_score
        # This combines kNN similarity with BM25 text relevance
        query_body = {
            "query": {
                "script_score": {
                    "query": {
                        "bool": {
                            "should": [
                                {
                                    "match": {
                                        "content": {
                                            "query": query_text,
                                            "boost": text_weight
                                        }
                                    }
                                }
                            ],
                            "filter": filter_query if filter_query else []
                        }
                    },
                    "script": {
                        "source": f"""
                            double vector_score = cosineSimilarity(params.query_vector, 'vector') + 1.0;
                            double text_score = _score;
                            return {vector_weight} * vector_score + {text_weight} * text_score;
                        """,
                        "params": {
                            "query_vector": query_vector
                        }
                    }
                }
            },
            "size": limit
        }

        response = client.search(index=self.index_name, body=query_body)

        results = []
        for hit in response['hits']['hits']:
            record = self._doc_to_record(hit)
            results.append(SearchResult(
                record=record,
                score=hit.get('_score', 0),
                distance=None
            ))

        return results
