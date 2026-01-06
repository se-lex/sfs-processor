#!/usr/bin/env python3
"""
Vector export functionality for SFS documents.

This module converts Swedish legal documents (SFS) to vector embeddings
suitable for semantic search and retrieval.

The vector exporter:
1. Applies temporal filtering to get only current regulations (like md/html mode)
2. Chunks documents intelligently (by paragraph, chapter, or semantically)
3. Generates embeddings using state-of-the-art models (OpenAI text-embedding-3)
4. Stores vectors in the chosen backend (PostgreSQL, Elasticsearch, or JSON)

Usage:
    from exporters.vector import create_vector_documents, VectorExportConfig

    # Configure export
    config = VectorExportConfig(
        embedding_provider="openai",
        embedding_model="text-embedding-3-large",
        backend_type="postgresql",
        chunking_strategy="paragraph"
    )

    # Export document
    create_vector_documents(data, output_dir, config, target_date="2024-01-01")
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from exporters.vector.chunking import (
    chunk_document,
    ChunkingStrategy,
    DocumentChunk
)
from exporters.vector.embeddings import (
    EmbeddingProvider,
    EmbeddingModel,
    get_embedding_provider,
    embed_document_chunks
)
from exporters.vector.backends import (
    VectorStoreBackend,
    VectorRecord,
    get_backend
)


@dataclass
class VectorExportConfig:
    """Configuration for vector export."""

    # Embedding settings
    embedding_provider: str = "openai"          # "openai" or "mock"
    embedding_model: str = "text-embedding-3-large"  # Best quality model
    embedding_dimensions: Optional[int] = None  # Custom dimensions (for text-embedding-3)
    embedding_batch_size: int = 100             # Batch size for embedding API

    # Backend settings
    backend_type: str = "json"                  # "postgresql", "elasticsearch", "json"
    backend_config: Dict[str, Any] = field(default_factory=dict)

    # Chunking settings
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.PARAGRAPH
    max_chunk_size: int = 512                   # Max tokens per chunk
    overlap_size: int = 50                      # Overlap tokens between chunks

    # Output settings
    save_json_export: bool = True               # Also save as JSON file
    verbose: bool = False                       # Verbose output

    def get_embedding_provider(self) -> EmbeddingProvider:
        """Create embedding provider from config."""
        kwargs = {
            "batch_size": self.embedding_batch_size
        }
        if self.embedding_dimensions:
            kwargs["dimensions"] = self.embedding_dimensions

        return get_embedding_provider(
            provider=self.embedding_provider,
            model=self.embedding_model,
            **kwargs
        )

    def get_backend(self) -> VectorStoreBackend:
        """Create backend from config."""
        return get_backend(self.backend_type, **self.backend_config)


def create_vector_documents(
    data: Dict[str, Any],
    output_dir: Path,
    config: Optional[VectorExportConfig] = None,
    target_date: Optional[str] = None,
    backend: Optional[VectorStoreBackend] = None,
    embedding_provider: Optional[EmbeddingProvider] = None
) -> List[VectorRecord]:
    """
    Create vector documents from SFS JSON data.

    This is the main entry point for vector export. It:
    1. Converts JSON to markdown
    2. Applies temporal filtering for the target date
    3. Chunks the document
    4. Generates embeddings
    5. Stores in the configured backend

    Args:
        data: JSON data containing document information
        output_dir: Directory for output files (used for JSON export)
        config: Vector export configuration
        target_date: Target date for temporal filtering (YYYY-MM-DD)
                    If None, uses today's date
        backend: Pre-configured backend (overrides config.backend_type)
        embedding_provider: Pre-configured embedding provider

    Returns:
        List of VectorRecord objects that were created

    Example:
        config = VectorExportConfig(
            embedding_provider="openai",
            backend_type="postgresql",
            backend_config={"connection_string": "postgresql://..."}
        )
        records = create_vector_documents(data, output_dir, config)
    """
    if config is None:
        config = VectorExportConfig()

    # Default target_date to today
    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')

    # Extract beteckning for logging
    beteckning = data.get('beteckning')
    if not beteckning:
        print("Varning: Beteckning saknas i dokumentdata")
        return []

    # Skip agency regulations (N-beteckningar)
    if beteckning.startswith('N'):
        if config.verbose:
            print(f"Hoppar över myndighetsföreskrift: {beteckning}")
        return []

    if config.verbose:
        print(f"Skapar vektordata för {beteckning} (target_date: {target_date})")

    # Step 1: Convert to markdown with temporal filtering
    markdown_content = _prepare_document_content(data, target_date, config.verbose)

    if not markdown_content:
        print(f"Varning: Inget innehåll för {beteckning} efter temporal processing")
        return []

    # Step 2: Chunk the document
    chunks = chunk_document(
        content=markdown_content,
        document_id=beteckning,
        strategy=config.chunking_strategy,
        max_chunk_size=config.max_chunk_size,
        overlap_size=config.overlap_size,
        metadata={
            "target_date": target_date,
            "export_timestamp": datetime.now().isoformat()
        }
    )

    if not chunks:
        print(f"Varning: Inga chunks skapades för {beteckning}")
        return []

    if config.verbose:
        print(f"  Skapade {len(chunks)} chunks")

    # Step 3: Generate embeddings
    provider = embedding_provider or config.get_embedding_provider()

    if config.verbose:
        print(f"  Genererar embeddings med {provider.get_model_name()}...")

    chunk_embeddings = embed_document_chunks(
        chunks=chunks,
        provider=provider,
        show_progress=config.verbose
    )

    # Step 4: Create VectorRecords
    records = []
    for chunk, embedding_result in chunk_embeddings:
        record = VectorRecord(
            id=chunk.chunk_id,
            vector=embedding_result.embedding,
            content=chunk.content,
            document_id=chunk.document_id,
            document_title=chunk.rubrik,
            chunk_index=chunk.chunk_index,
            total_chunks=chunk.total_chunks,
            chapter=chunk.chapter,
            paragraph=chunk.paragraph,
            section_type=chunk.section_type,
            departement=chunk.departement,
            effective_date=chunk.effective_date,
            issued_date=chunk.issued_date,
            repealed=chunk.repealed,
            expiration_date=chunk.expiration_date,
            embedding_model=embedding_result.model,
            dimensions=embedding_result.dimensions,
            created_at=datetime.now(),
            metadata={
                "target_date": target_date,
                "char_count": chunk.char_count,
                "estimated_tokens": chunk.estimated_tokens,
                "tokens_used": embedding_result.tokens_used
            }
        )
        records.append(record)

    # Step 5: Store in backend
    store = backend or config.get_backend()

    # Initialize backend if needed
    if records:
        dimensions = records[0].dimensions
        store.initialize(dimensions)

    # Delete existing records for this document
    deleted = store.delete_by_document(beteckning)
    if deleted > 0 and config.verbose:
        print(f"  Tog bort {deleted} befintliga records")

    # Insert new records
    inserted = store.insert_batch(records)

    if config.verbose:
        print(f"  Infogade {inserted} records i {config.backend_type}")

    # Step 6: Optionally save JSON export
    if config.save_json_export:
        _save_json_export(records, output_dir, beteckning)

    return records


def _prepare_document_content(
    data: Dict[str, Any],
    target_date: str,
    verbose: bool = False
) -> Optional[str]:
    """
    Prepare document content with temporal filtering.

    This mimics the processing done in md/html mode to ensure
    only current regulations are included.

    Args:
        data: JSON document data
        target_date: Target date for temporal filtering
        verbose: Enable verbose output

    Returns:
        Markdown content with temporal rules applied, or None if empty
    """
    # Import processing functions
    from sfs_processor import convert_to_markdown
    from temporal.apply_temporal import apply_temporal, is_document_content_empty
    from temporal.title_temporal import title_temporal
    from formatters.format_sfs_text import normalize_heading_levels

    # Apply temporal title processing
    if data.get('rubrik'):
        rubrik_after_temporal = title_temporal(data['rubrik'], target_date)
        data = data.copy()
        data['rubrik_after_temporal'] = rubrik_after_temporal

    # Convert to markdown
    try:
        markdown_content = convert_to_markdown(data, fetch_predocs_from_api=False, apply_links=False)
    except ValueError as e:
        if verbose:
            print(f"Varning: Kunde inte konvertera dokument: {e}")
        return None

    # Normalize heading levels
    markdown_content = normalize_heading_levels(markdown_content)

    # Apply temporal filtering
    markdown_content = apply_temporal(markdown_content, target_date, verbose=verbose)

    # Check if document is empty after temporal processing
    if is_document_content_empty(markdown_content):
        if verbose:
            print("Dokumentet är tomt efter temporal processing")
        return None

    return markdown_content


def _save_json_export(
    records: List[VectorRecord],
    output_dir: Path,
    beteckning: str
) -> Path:
    """
    Save records as JSON file for portability.

    Args:
        records: List of VectorRecords
        output_dir: Output directory
        beteckning: Document identifier

    Returns:
        Path to the saved JSON file
    """
    # Create vector output directory
    vector_dir = output_dir / "vectors"
    vector_dir.mkdir(parents=True, exist_ok=True)

    # Create safe filename
    safe_beteckning = beteckning.replace(':', '-')
    json_file = vector_dir / f"sfs-{safe_beteckning}-vectors.json"

    # Convert records to dict (without vectors for readability)
    export_data = {
        "document_id": beteckning,
        "export_timestamp": datetime.now().isoformat(),
        "total_records": len(records),
        "records": [
            {
                "id": r.id,
                "content": r.content,
                "document_title": r.document_title,
                "chunk_index": r.chunk_index,
                "total_chunks": r.total_chunks,
                "chapter": r.chapter,
                "paragraph": r.paragraph,
                "section_type": r.section_type,
                "embedding_model": r.embedding_model,
                "dimensions": r.dimensions,
                "vector_preview": r.vector[:5] + ["..."] + r.vector[-5:] if len(r.vector) > 10 else r.vector,
                "metadata": r.metadata
            }
            for r in records
        ]
    }

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

    return json_file


def batch_create_vector_documents(
    json_files: List[Path],
    output_dir: Path,
    config: Optional[VectorExportConfig] = None,
    target_date: Optional[str] = None,
    show_progress: bool = True
) -> Dict[str, List[VectorRecord]]:
    """
    Create vector documents for multiple JSON files.

    Efficiently processes multiple documents using batched embedding calls
    and shared backend connections.

    Args:
        json_files: List of JSON file paths
        output_dir: Output directory
        config: Vector export configuration
        target_date: Target date for temporal filtering
        show_progress: Show progress indicator

    Returns:
        Dictionary mapping beteckning to list of VectorRecords
    """
    if config is None:
        config = VectorExportConfig()

    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')

    # Create shared resources
    embedding_provider = config.get_embedding_provider()
    backend = config.get_backend()

    results = {}
    total = len(json_files)

    for i, json_file in enumerate(json_files):
        if show_progress:
            print(f"[{i+1}/{total}] Bearbetar {json_file.name}...")

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Fel vid läsning av {json_file}: {e}")
            continue

        beteckning = data.get('beteckning', json_file.stem)

        records = create_vector_documents(
            data=data,
            output_dir=output_dir,
            config=config,
            target_date=target_date,
            backend=backend,
            embedding_provider=embedding_provider
        )

        if records:
            results[beteckning] = records

    # Close backend connection
    backend.close()

    if show_progress:
        total_records = sum(len(r) for r in results.values())
        print(f"\nKlar! Skapade {total_records} vektorer för {len(results)} dokument")

    return results


# CLI interface
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description='Export SFS documents to vector format'
    )
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input JSON file or directory'
    )
    parser.add_argument(
        '--output', '-o',
        default='./vector-export',
        help='Output directory'
    )
    parser.add_argument(
        '--target-date',
        default=None,
        help='Target date for temporal filtering (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--backend',
        default='json',
        choices=['postgresql', 'elasticsearch', 'json'],
        help='Vector store backend'
    )
    parser.add_argument(
        '--embedding-model',
        default='text-embedding-3-large',
        help='Embedding model to use'
    )
    parser.add_argument(
        '--chunking',
        default='paragraph',
        choices=['paragraph', 'chapter', 'section', 'semantic', 'fixed_size'],
        help='Chunking strategy'
    )
    parser.add_argument(
        '--mock-embeddings',
        action='store_true',
        help='Use mock embeddings (for testing without API)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Build config
    config = VectorExportConfig(
        embedding_provider="mock" if args.mock_embeddings else "openai",
        embedding_model=args.embedding_model,
        backend_type=args.backend,
        chunking_strategy=ChunkingStrategy(args.chunking),
        verbose=args.verbose
    )

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path.is_file():
        # Single file
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        records = create_vector_documents(
            data=data,
            output_dir=output_dir,
            config=config,
            target_date=args.target_date
        )
        print(f"Skapade {len(records)} vektorer")
    else:
        # Directory
        json_files = list(input_path.glob('*.json'))
        if not json_files:
            print(f"Inga JSON-filer hittades i {input_path}")
            sys.exit(1)

        results = batch_create_vector_documents(
            json_files=json_files,
            output_dir=output_dir,
            config=config,
            target_date=args.target_date
        )
