#!/usr/bin/env python3
"""
PostgreSQL backend with pgvector extension for vector storage.

This backend uses the pgvector extension for efficient vector similarity search.
It supports both cosine similarity and L2 distance metrics.

Requirements:
    - PostgreSQL 12+ with pgvector extension installed
    - psycopg2 or psycopg (pip install psycopg2-binary or psycopg[binary])

Environment variables:
    - POSTGRES_CONNECTION_STRING: Full connection string
    - Or individual: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""

import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from exporters.vector.backends.base import VectorStoreBackend, VectorRecord, SearchResult


class PostgreSQLBackend(VectorStoreBackend):
    """
    PostgreSQL vector store backend using pgvector.

    Supports efficient vector similarity search with cosine similarity
    or L2 distance metrics. Uses HNSW or IVFFlat indexes for fast retrieval.
    """

    DEFAULT_TABLE_NAME = "sfs_vectors"
    DEFAULT_INDEX_TYPE = "hnsw"  # or "ivfflat"

    def __init__(
        self,
        connection_string: Optional[str] = None,
        host: Optional[str] = None,
        port: int = 5432,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        table_name: str = DEFAULT_TABLE_NAME,
        index_type: str = DEFAULT_INDEX_TYPE,
        distance_metric: str = "cosine"  # "cosine", "l2", "inner_product"
    ):
        """
        Initialize PostgreSQL backend.

        Args:
            connection_string: Full PostgreSQL connection string
            host: Database host (if not using connection_string)
            port: Database port (default: 5432)
            database: Database name
            user: Database user
            password: Database password
            table_name: Name of the vector table
            index_type: Type of index ("hnsw" or "ivfflat")
            distance_metric: Distance metric for similarity search
        """
        self.table_name = table_name
        self.index_type = index_type
        self.distance_metric = distance_metric
        self._dimensions = None
        self._conn = None

        # Build connection string
        if connection_string:
            self.connection_string = connection_string
        else:
            self.connection_string = self._build_connection_string(
                host or os.environ.get('POSTGRES_HOST', 'localhost'),
                port or int(os.environ.get('POSTGRES_PORT', '5432')),
                database or os.environ.get('POSTGRES_DB', 'sfs_vectors'),
                user or os.environ.get('POSTGRES_USER', 'postgres'),
                password or os.environ.get('POSTGRES_PASSWORD', '')
            )

    def _build_connection_string(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str
    ) -> str:
        """Build PostgreSQL connection string."""
        if password:
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        return f"postgresql://{user}@{host}:{port}/{database}"

    def _get_connection(self):
        """Get or create database connection."""
        if self._conn is None:
            try:
                import psycopg2
                self._conn = psycopg2.connect(self.connection_string)
            except ImportError:
                try:
                    import psycopg
                    self._conn = psycopg.connect(self.connection_string)
                except ImportError:
                    raise ImportError(
                        "PostgreSQL driver not installed. Install with: "
                        "pip install psycopg2-binary or pip install psycopg[binary]"
                    )
        return self._conn

    def _get_distance_operator(self) -> str:
        """Get the pgvector distance operator for the configured metric."""
        operators = {
            "cosine": "<=>",      # Cosine distance
            "l2": "<->",          # L2 distance
            "inner_product": "<#>"  # Inner product (negative)
        }
        return operators.get(self.distance_metric, "<=>")

    def initialize(self, dimensions: int, **kwargs) -> None:
        """
        Initialize the database schema.

        Creates the pgvector extension, table, and index if they don't exist.

        Args:
            dimensions: Vector dimensionality
            **kwargs: Additional options (e.g., index_lists for IVFFlat)
        """
        self._dimensions = dimensions
        conn = self._get_connection()

        with conn.cursor() as cur:
            # Create pgvector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Create table
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id TEXT PRIMARY KEY,
                    vector vector({dimensions}),
                    content TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    document_title TEXT,
                    chunk_index INTEGER DEFAULT 0,
                    total_chunks INTEGER DEFAULT 1,
                    chapter TEXT,
                    paragraph TEXT,
                    section_type TEXT,
                    departement TEXT,
                    effective_date DATE,
                    issued_date DATE,
                    repealed BOOLEAN DEFAULT FALSE,
                    expiration_date DATE,
                    embedding_model TEXT,
                    dimensions INTEGER DEFAULT {dimensions},
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB DEFAULT '{{}}'::jsonb
                )
            """)

            # Create index on document_id for efficient deletion
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_document_id
                ON {self.table_name} (document_id)
            """)

            # Create vector index
            if self.index_type == "hnsw":
                # HNSW index - better for most use cases
                op_class = self._get_op_class()
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_vector_hnsw
                    ON {self.table_name}
                    USING hnsw (vector {op_class})
                    WITH (m = 16, ef_construction = 64)
                """)
            elif self.index_type == "ivfflat":
                # IVFFlat index - faster to build, slower to query
                lists = kwargs.get('index_lists', 100)
                op_class = self._get_op_class()
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_vector_ivfflat
                    ON {self.table_name}
                    USING ivfflat (vector {op_class})
                    WITH (lists = {lists})
                """)

            conn.commit()
            print(f"PostgreSQL backend initialized with {dimensions}-dimensional vectors")

    def _get_op_class(self) -> str:
        """Get the operator class for index creation."""
        op_classes = {
            "cosine": "vector_cosine_ops",
            "l2": "vector_l2_ops",
            "inner_product": "vector_ip_ops"
        }
        return op_classes.get(self.distance_metric, "vector_cosine_ops")

    def insert(self, record: VectorRecord) -> None:
        """Insert a single record."""
        self.insert_batch([record])

    def insert_batch(self, records: List[VectorRecord]) -> int:
        """Insert multiple records in a batch."""
        if not records:
            return 0

        conn = self._get_connection()
        inserted = 0

        with conn.cursor() as cur:
            for record in records:
                try:
                    # Convert vector to string format for pgvector
                    vector_str = '[' + ','.join(str(v) for v in record.vector) + ']'

                    cur.execute(f"""
                        INSERT INTO {self.table_name} (
                            id, vector, content, document_id, document_title,
                            chunk_index, total_chunks, chapter, paragraph,
                            section_type, departement, effective_date, issued_date,
                            repealed, expiration_date,
                            embedding_model, dimensions, created_at, metadata
                        ) VALUES (
                            %s, %s::vector, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s,
                            %s, %s, %s, %s
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            vector = EXCLUDED.vector,
                            content = EXCLUDED.content,
                            document_title = EXCLUDED.document_title,
                            chunk_index = EXCLUDED.chunk_index,
                            total_chunks = EXCLUDED.total_chunks,
                            chapter = EXCLUDED.chapter,
                            paragraph = EXCLUDED.paragraph,
                            section_type = EXCLUDED.section_type,
                            departement = EXCLUDED.departement,
                            effective_date = EXCLUDED.effective_date,
                            issued_date = EXCLUDED.issued_date,
                            repealed = EXCLUDED.repealed,
                            expiration_date = EXCLUDED.expiration_date,
                            embedding_model = EXCLUDED.embedding_model,
                            created_at = EXCLUDED.created_at,
                            metadata = EXCLUDED.metadata
                    """, (
                        record.id,
                        vector_str,
                        record.content,
                        record.document_id,
                        record.document_title,
                        record.chunk_index,
                        record.total_chunks,
                        record.chapter,
                        record.paragraph,
                        record.section_type,
                        record.departement,
                        record.effective_date,
                        record.issued_date,
                        record.repealed,
                        record.expiration_date,
                        record.embedding_model,
                        record.dimensions,
                        record.created_at or datetime.now(),
                        json.dumps(record.metadata)
                    ))
                    inserted += 1
                except Exception as e:
                    print(f"Error inserting record {record.id}: {e}")
                    continue

            conn.commit()

        return inserted

    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar vectors."""
        conn = self._get_connection()
        results = []

        vector_str = '[' + ','.join(str(v) for v in query_vector) + ']'
        operator = self._get_distance_operator()

        # Build WHERE clause from filters
        where_clauses = []
        params = [vector_str]

        if filters:
            for key, value in filters.items():
                if key in ['document_id', 'chapter', 'paragraph', 'section_type', 'departement']:
                    where_clauses.append(f"{key} = %s")
                    params.append(value)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        params.append(limit)

        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT
                    id, vector, content, document_id, document_title,
                    chunk_index, total_chunks, chapter, paragraph,
                    section_type, departement, effective_date, issued_date,
                    repealed, expiration_date,
                    embedding_model, dimensions, created_at, metadata,
                    vector {operator} %s::vector AS distance
                FROM {self.table_name}
                {where_sql}
                ORDER BY distance
                LIMIT %s
            """, params)

            for row in cur.fetchall():
                record = VectorRecord(
                    id=row[0],
                    vector=list(row[1]) if row[1] else [],
                    content=row[2],
                    document_id=row[3],
                    document_title=row[4],
                    chunk_index=row[5],
                    total_chunks=row[6],
                    chapter=row[7],
                    paragraph=row[8],
                    section_type=row[9],
                    departement=row[10],
                    effective_date=row[11],
                    issued_date=row[12],
                    repealed=row[13],
                    expiration_date=row[14],
                    embedding_model=row[15],
                    dimensions=row[16],
                    created_at=row[17],
                    metadata=row[18] or {}
                )
                distance = float(row[19])

                # Convert distance to similarity score
                if self.distance_metric == "cosine":
                    score = 1 - distance  # Cosine similarity
                elif self.distance_metric == "inner_product":
                    score = -distance  # Inner product is negated in pgvector
                else:
                    score = 1 / (1 + distance)  # L2 to similarity

                results.append(SearchResult(
                    record=record,
                    score=score,
                    distance=distance
                ))

        return results

    def delete_by_document(self, document_id: str) -> int:
        """Delete all records for a document."""
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {self.table_name} WHERE document_id = %s",
                (document_id,)
            )
            deleted = cur.rowcount
            conn.commit()

        return deleted

    def get_by_id(self, record_id: str) -> Optional[VectorRecord]:
        """Get a record by ID."""
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT
                    id, vector, content, document_id, document_title,
                    chunk_index, total_chunks, chapter, paragraph,
                    section_type, departement, effective_date, issued_date,
                    repealed, expiration_date,
                    embedding_model, dimensions, created_at, metadata
                FROM {self.table_name}
                WHERE id = %s
            """, (record_id,))

            row = cur.fetchone()
            if not row:
                return None

            return VectorRecord(
                id=row[0],
                vector=list(row[1]) if row[1] else [],
                content=row[2],
                document_id=row[3],
                document_title=row[4],
                chunk_index=row[5],
                total_chunks=row[6],
                chapter=row[7],
                paragraph=row[8],
                section_type=row[9],
                departement=row[10],
                effective_date=row[11],
                issued_date=row[12],
                repealed=row[13],
                expiration_date=row[14],
                embedding_model=row[15],
                dimensions=row[16],
                created_at=row[17],
                metadata=row[18] or {}
            )

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records in the store."""
        conn = self._get_connection()

        where_clauses = []
        params = []

        if filters:
            for key, value in filters.items():
                if key in ['document_id', 'chapter', 'paragraph', 'section_type', 'departement']:
                    where_clauses.append(f"{key} = %s")
                    params.append(value)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self.table_name} {where_sql}", params)
            return cur.fetchone()[0]

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def health_check(self) -> Tuple[bool, str]:
        """Check database connectivity."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                count = cur.fetchone()[0]
            return True, f"PostgreSQL connected, {count} records in {self.table_name}"
        except Exception as e:
            return False, f"PostgreSQL error: {e}"
