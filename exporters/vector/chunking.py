#!/usr/bin/env python3
"""
Text chunking module for SFS documents.

This module provides intelligent chunking strategies for Swedish legal documents,
optimized for vector embedding and retrieval.

Chunking strategies:
- PARAGRAPH: Split by paragraf (§) - preserves legal structure
- CHAPTER: Split by kapitel - larger context
- SECTION: Split by logical sections (marked with selex tags)
- SEMANTIC: Split by semantic boundaries with overlap
- FIXED_SIZE: Split by token count with overlap
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


class ChunkingStrategy(Enum):
    """Available chunking strategies for legal documents."""
    PARAGRAPH = "paragraph"      # Split by § (paragraf)
    CHAPTER = "chapter"          # Split by kapitel
    SECTION = "section"          # Split by selex section tags
    SEMANTIC = "semantic"        # Semantic boundaries with overlap
    FIXED_SIZE = "fixed_size"    # Fixed token count with overlap


@dataclass
class DocumentChunk:
    """Represents a chunk of a document with metadata."""
    content: str                          # The actual text content
    chunk_id: str                         # Unique identifier for this chunk
    document_id: str                      # Reference to parent document (beteckning)
    chunk_index: int                      # Position within document
    total_chunks: int                     # Total chunks in document

    # Structural metadata
    chapter: Optional[str] = None         # Chapter reference (e.g., "1 kap.")
    paragraph: Optional[str] = None       # Paragraph reference (e.g., "1 §")
    section_type: Optional[str] = None    # Type of section (kapitel, paragraf, etc.)

    # Document metadata
    rubrik: Optional[str] = None          # Document title
    departement: Optional[str] = None     # Responsible department
    effective_date: Optional[str] = None  # Entry into force date (ikraft_datum)
    issued_date: Optional[str] = None     # Issued date (utfardad_datum)
    repealed: bool = False                # If regulation is repealed (upphavd)
    expiration_date: Optional[str] = None # Expiration date (upphor_datum)

    # Chunk-specific metadata
    char_count: int = 0                   # Character count
    estimated_tokens: int = 0             # Estimated token count

    # Additional metadata as dict
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary for serialization."""
        return {
            'content': self.content,
            'chunk_id': self.chunk_id,
            'document_id': self.document_id,
            'chunk_index': self.chunk_index,
            'total_chunks': self.total_chunks,
            'chapter': self.chapter,
            'paragraph': self.paragraph,
            'section_type': self.section_type,
            'rubrik': self.rubrik,
            'departement': self.departement,
            'effective_date': self.effective_date,
            'issued_date': self.issued_date,
            'repealed': self.repealed,
            'expiration_date': self.expiration_date,
            'char_count': self.char_count,
            'estimated_tokens': self.estimated_tokens,
            'metadata': self.metadata,
        }


def estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a text.

    Uses a simple heuristic: ~4 characters per token for Swedish text.
    This is a rough estimate; actual token count depends on the tokenizer.

    Args:
        text: The text to estimate tokens for

    Returns:
        Estimated token count
    """
    # Swedish text averages about 4-5 characters per token
    # Using 4 to be conservative (better to overestimate)
    return len(text) // 4


def _normalize_metadata_fields(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize metadata field names from Swedish to English.

    Maps Swedish field names to English equivalents for consistency
    in vector export artifacts (JSON, SQL tables, etc.).

    Args:
        metadata: Dictionary with Swedish field names

    Returns:
        Dictionary with normalized English field names
    """
    normalized = metadata.copy()

    # Map Swedish to English field names
    field_mapping = {
        'ikraft_datum': 'effective_date',
        'utfardad_datum': 'issued_date',
        'upphor_datum': 'expiration_date',
        'upphavd': 'repealed',
    }

    for swedish, english in field_mapping.items():
        if swedish in normalized:
            normalized[english] = normalized.pop(swedish)

    return normalized


def chunk_document(
    content: str,
    document_id: str,
    strategy: ChunkingStrategy = ChunkingStrategy.PARAGRAPH,
    max_chunk_size: int = 512,
    overlap_size: int = 50,
    metadata: Optional[Dict[str, Any]] = None
) -> List[DocumentChunk]:
    """
    Split a document into chunks using the specified strategy.

    Args:
        content: The markdown content to chunk (after temporal processing)
        document_id: The document identifier (beteckning)
        strategy: The chunking strategy to use
        max_chunk_size: Maximum tokens per chunk (for fixed_size/semantic)
        overlap_size: Number of tokens to overlap between chunks
        metadata: Additional metadata to attach to all chunks

    Returns:
        List of DocumentChunk objects
    """
    if metadata is None:
        metadata = {}

    # Extract document-level metadata from frontmatter
    doc_metadata = _extract_frontmatter_metadata(content)
    doc_metadata.update(metadata)
    # Normalize field names from Swedish to English
    doc_metadata = _normalize_metadata_fields(doc_metadata)

    # Remove frontmatter for chunking
    content_body = _remove_frontmatter(content)

    # Clean selex tags but preserve structure for chunking
    # We keep the structural information for metadata extraction

    if strategy == ChunkingStrategy.PARAGRAPH:
        chunks = _chunk_by_paragraph(content_body, document_id, doc_metadata)
    elif strategy == ChunkingStrategy.CHAPTER:
        chunks = _chunk_by_chapter(content_body, document_id, doc_metadata)
    elif strategy == ChunkingStrategy.SECTION:
        chunks = _chunk_by_section(content_body, document_id, doc_metadata)
    elif strategy == ChunkingStrategy.SEMANTIC:
        chunks = _chunk_semantic(content_body, document_id, doc_metadata, max_chunk_size, overlap_size)
    elif strategy == ChunkingStrategy.FIXED_SIZE:
        chunks = _chunk_fixed_size(content_body, document_id, doc_metadata, max_chunk_size, overlap_size)
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")

    # Update total_chunks for all chunks
    total = len(chunks)
    for chunk in chunks:
        chunk.total_chunks = total

    return chunks


def _extract_frontmatter_metadata(content: str) -> Dict[str, Any]:
    """Extract metadata from YAML frontmatter and selex attributes."""
    metadata = {}

    # Find frontmatter between --- markers
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not frontmatter_match:
        return metadata

    frontmatter_text = frontmatter_match.group(1)

    # Extract key fields from frontmatter
    for field in ['rubrik', 'departement', 'ikraft_datum', 'utfardad_datum', 'upphor_datum', 'beteckning']:
        match = re.search(rf'^{field}:\s*(.+)$', frontmatter_text, re.MULTILINE)
        if match:
            value = match.group(1).strip()
            # Remove quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            metadata[field] = value

    # Also extract from selex attributes in article tag if not in frontmatter
    article_match = re.search(r'<article([^>]*)>', content)
    if article_match:
        article_attrs = article_match.group(1)

        # Extract ikraft_datum from selex:ikraft_datum if not in frontmatter
        if 'ikraft_datum' not in metadata:
            ikraft_match = re.search(r'selex:ikraft_datum="([^"]+)"', article_attrs)
            if ikraft_match:
                metadata['ikraft_datum'] = ikraft_match.group(1)

        # Extract utfardad_datum from selex:utfardad_datum if not in frontmatter
        if 'utfardad_datum' not in metadata:
            utfardad_match = re.search(r'selex:utfardad_datum="([^"]+)"', article_attrs)
            if utfardad_match:
                metadata['utfardad_datum'] = utfardad_match.group(1)

        # Extract upphor_datum from selex:upphor_datum if not in frontmatter
        if 'upphor_datum' not in metadata:
            upphor_match = re.search(r'selex:upphor_datum="([^"]+)"', article_attrs)
            if upphor_match:
                metadata['upphor_datum'] = upphor_match.group(1)

        # Check if upphavd flag is present
        if 'selex:upphavd="true"' in article_attrs:
            metadata['upphavd'] = True

    return metadata


def _remove_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from content."""
    # Match frontmatter between --- markers
    result = re.sub(r'^---\s*\n.*?\n---\s*\n?', '', content, flags=re.DOTALL)
    return result.strip()


def _clean_text_for_embedding(text: str) -> str:
    """Clean text for embedding, removing tags but preserving readability."""
    # Remove section/article tags but keep content
    cleaned = re.sub(r'</?(?:section|article)[^>]*>', '', text)
    # Normalize whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(r' +', ' ', cleaned)
    return cleaned.strip()


def _chunk_by_paragraph(content: str, document_id: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
    """
    Chunk document by paragraph (§).

    Each paragraf becomes its own chunk, which preserves the natural
    legal structure of Swedish law.
    """
    chunks = []
    current_chapter = None

    # Pattern to find paragraf sections
    # Matches sections marked as class="paragraf" or containing § in heading
    paragraf_pattern = re.compile(
        r'<section[^>]*class="paragraf"[^>]*>(.*?)</section>',
        re.DOTALL
    )

    # Also find chapter headings
    chapter_pattern = re.compile(r'##\s*(\d+\s*kap\.?[^#\n]*)', re.IGNORECASE)

    # Find all paragraf sections
    matches = list(paragraf_pattern.finditer(content))

    if not matches:
        # Fallback: split by § headings
        return _chunk_by_paragraph_headings(content, document_id, metadata)

    for i, match in enumerate(matches):
        section_content = match.group(1)

        # Extract paragraph number from heading
        para_match = re.search(r'#+\s*(\d+\s*[a-z]?\s*§)', section_content)
        paragraph_ref = para_match.group(1) if para_match else None

        # Find which chapter this belongs to
        content_before = content[:match.start()]
        chapter_matches = list(chapter_pattern.finditer(content_before))
        if chapter_matches:
            current_chapter = chapter_matches[-1].group(1).strip()

        # Clean the content
        clean_content = _clean_text_for_embedding(section_content)

        if clean_content:
            chunk = DocumentChunk(
                content=clean_content,
                chunk_id=f"{document_id}_p{i}",
                document_id=document_id,
                chunk_index=i,
                total_chunks=0,  # Will be updated later
                chapter=current_chapter,
                paragraph=paragraph_ref,
                section_type="paragraf",
                rubrik=metadata.get('rubrik'),
                departement=metadata.get('departement'),
                effective_date=metadata.get('effective_date'),
                issued_date=metadata.get('issued_date'),
                repealed=metadata.get('repealed', False),
                expiration_date=metadata.get('expiration_date'),
                char_count=len(clean_content),
                estimated_tokens=estimate_tokens(clean_content),
                metadata=metadata.copy()
            )
            chunks.append(chunk)

    return chunks


def _chunk_by_paragraph_headings(content: str, document_id: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
    """Fallback: chunk by § headings when no section tags are present."""
    chunks = []
    current_chapter = None

    # Split by paragraph headings (#### N § or ### N §)
    parts = re.split(r'(#{3,4}\s*\d+\s*[a-z]?\s*§[^\n]*)', content)

    current_paragraph = None
    current_content = []
    chunk_index = 0

    for part in parts:
        para_match = re.match(r'#{3,4}\s*(\d+\s*[a-z]?\s*§)', part)
        if para_match:
            # Save previous chunk if exists
            if current_content:
                clean_content = _clean_text_for_embedding('\n'.join(current_content))
                if clean_content.strip():
                    chunk = DocumentChunk(
                        content=clean_content,
                        chunk_id=f"{document_id}_p{chunk_index}",
                        document_id=document_id,
                        chunk_index=chunk_index,
                        total_chunks=0,
                        chapter=current_chapter,
                        paragraph=current_paragraph,
                        section_type="paragraf",
                        rubrik=metadata.get('rubrik'),
                        departement=metadata.get('departement'),
                        effective_date=metadata.get('effective_date'),
                issued_date=metadata.get('issued_date'),
                repealed=metadata.get('repealed', False),
                expiration_date=metadata.get('expiration_date'),
                        char_count=len(clean_content),
                        estimated_tokens=estimate_tokens(clean_content),
                        metadata=metadata.copy()
                    )
                    chunks.append(chunk)
                    chunk_index += 1

            current_paragraph = para_match.group(1)
            current_content = [part]
        else:
            # Check for chapter heading
            chapter_match = re.search(r'##\s*(\d+\s*kap\.?[^#\n]*)', part, re.IGNORECASE)
            if chapter_match:
                current_chapter = chapter_match.group(1).strip()
            current_content.append(part)

    # Don't forget the last chunk
    if current_content:
        clean_content = _clean_text_for_embedding('\n'.join(current_content))
        if clean_content.strip():
            chunk = DocumentChunk(
                content=clean_content,
                chunk_id=f"{document_id}_p{chunk_index}",
                document_id=document_id,
                chunk_index=chunk_index,
                total_chunks=0,
                chapter=current_chapter,
                paragraph=current_paragraph,
                section_type="paragraf",
                rubrik=metadata.get('rubrik'),
                departement=metadata.get('departement'),
                effective_date=metadata.get('effective_date'),
                issued_date=metadata.get('issued_date'),
                repealed=metadata.get('repealed', False),
                expiration_date=metadata.get('expiration_date'),
                char_count=len(clean_content),
                estimated_tokens=estimate_tokens(clean_content),
                metadata=metadata.copy()
            )
            chunks.append(chunk)

    return chunks


def _chunk_by_chapter(content: str, document_id: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
    """
    Chunk document by chapter (kapitel).

    Each chapter becomes its own chunk, providing larger context
    but fewer chunks per document.
    """
    chunks = []

    # Pattern to find kapitel sections
    kapitel_pattern = re.compile(
        r'<section[^>]*class="kapitel"[^>]*>(.*?)</section>',
        re.DOTALL
    )

    matches = list(kapitel_pattern.finditer(content))

    if not matches:
        # Fallback: split by chapter headings
        return _chunk_by_chapter_headings(content, document_id, metadata)

    for i, match in enumerate(matches):
        section_content = match.group(1)

        # Extract chapter reference from heading
        chapter_match = re.search(r'##\s*(\d+\s*kap\.?[^\n]*)', section_content, re.IGNORECASE)
        chapter_ref = chapter_match.group(1).strip() if chapter_match else f"Kapitel {i+1}"

        clean_content = _clean_text_for_embedding(section_content)

        if clean_content:
            chunk = DocumentChunk(
                content=clean_content,
                chunk_id=f"{document_id}_ch{i}",
                document_id=document_id,
                chunk_index=i,
                total_chunks=0,
                chapter=chapter_ref,
                paragraph=None,
                section_type="kapitel",
                rubrik=metadata.get('rubrik'),
                departement=metadata.get('departement'),
                effective_date=metadata.get('effective_date'),
                issued_date=metadata.get('issued_date'),
                repealed=metadata.get('repealed', False),
                expiration_date=metadata.get('expiration_date'),
                char_count=len(clean_content),
                estimated_tokens=estimate_tokens(clean_content),
                metadata=metadata.copy()
            )
            chunks.append(chunk)

    return chunks


def _chunk_by_chapter_headings(content: str, document_id: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
    """Fallback: chunk by chapter headings when no section tags are present."""
    chunks = []

    # Split by chapter headings (## N kap.)
    parts = re.split(r'(##\s*\d+\s*kap\.?[^\n]*)', content, flags=re.IGNORECASE)

    current_chapter = None
    current_content = []
    chunk_index = 0

    for part in parts:
        chapter_match = re.match(r'##\s*(\d+\s*kap\.?[^\n]*)', part, re.IGNORECASE)
        if chapter_match:
            # Save previous chunk if exists
            if current_content and current_chapter:
                clean_content = _clean_text_for_embedding('\n'.join(current_content))
                if clean_content.strip():
                    chunk = DocumentChunk(
                        content=clean_content,
                        chunk_id=f"{document_id}_ch{chunk_index}",
                        document_id=document_id,
                        chunk_index=chunk_index,
                        total_chunks=0,
                        chapter=current_chapter,
                        paragraph=None,
                        section_type="kapitel",
                        rubrik=metadata.get('rubrik'),
                        departement=metadata.get('departement'),
                        effective_date=metadata.get('effective_date'),
                issued_date=metadata.get('issued_date'),
                repealed=metadata.get('repealed', False),
                expiration_date=metadata.get('expiration_date'),
                        char_count=len(clean_content),
                        estimated_tokens=estimate_tokens(clean_content),
                        metadata=metadata.copy()
                    )
                    chunks.append(chunk)
                    chunk_index += 1

            current_chapter = chapter_match.group(1).strip()
            current_content = [part]
        else:
            current_content.append(part)

    # Don't forget the last chunk
    if current_content and current_chapter:
        clean_content = _clean_text_for_embedding('\n'.join(current_content))
        if clean_content.strip():
            chunk = DocumentChunk(
                content=clean_content,
                chunk_id=f"{document_id}_ch{chunk_index}",
                document_id=document_id,
                chunk_index=chunk_index,
                total_chunks=0,
                chapter=current_chapter,
                paragraph=None,
                section_type="kapitel",
                rubrik=metadata.get('rubrik'),
                departement=metadata.get('departement'),
                effective_date=metadata.get('effective_date'),
                issued_date=metadata.get('issued_date'),
                repealed=metadata.get('repealed', False),
                expiration_date=metadata.get('expiration_date'),
                char_count=len(clean_content),
                estimated_tokens=estimate_tokens(clean_content),
                metadata=metadata.copy()
            )
            chunks.append(chunk)

    # If no chapters found, return entire document as one chunk
    if not chunks:
        clean_content = _clean_text_for_embedding(content)
        if clean_content.strip():
            chunks.append(DocumentChunk(
                content=clean_content,
                chunk_id=f"{document_id}_full",
                document_id=document_id,
                chunk_index=0,
                total_chunks=1,
                chapter=None,
                paragraph=None,
                section_type="document",
                rubrik=metadata.get('rubrik'),
                departement=metadata.get('departement'),
                effective_date=metadata.get('effective_date'),
                issued_date=metadata.get('issued_date'),
                repealed=metadata.get('repealed', False),
                expiration_date=metadata.get('expiration_date'),
                char_count=len(clean_content),
                estimated_tokens=estimate_tokens(clean_content),
                metadata=metadata.copy()
            ))

    return chunks


def _chunk_by_section(content: str, document_id: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
    """
    Chunk document by selex section tags.

    Uses all section tags (both kapitel and paragraf) to create chunks.
    """
    chunks = []

    # Pattern to find all sections with class attribute
    section_pattern = re.compile(
        r'<section[^>]*class="([^"]+)"[^>]*>(.*?)</section>',
        re.DOTALL
    )

    matches = list(section_pattern.finditer(content))

    if not matches:
        # Fallback to paragraph chunking
        return _chunk_by_paragraph(content, document_id, metadata)

    current_chapter = None

    for i, match in enumerate(matches):
        section_class = match.group(1)
        section_content = match.group(2)

        # Track chapters for context
        if section_class == "kapitel":
            chapter_match = re.search(r'##\s*(\d+\s*kap\.?[^\n]*)', section_content, re.IGNORECASE)
            if chapter_match:
                current_chapter = chapter_match.group(1).strip()

        # Extract paragraph reference if it's a paragraf
        paragraph_ref = None
        if section_class == "paragraf":
            para_match = re.search(r'#+\s*(\d+\s*[a-z]?\s*§)', section_content)
            if para_match:
                paragraph_ref = para_match.group(1)

        clean_content = _clean_text_for_embedding(section_content)

        if clean_content:
            chunk = DocumentChunk(
                content=clean_content,
                chunk_id=f"{document_id}_s{i}",
                document_id=document_id,
                chunk_index=i,
                total_chunks=0,
                chapter=current_chapter,
                paragraph=paragraph_ref,
                section_type=section_class,
                rubrik=metadata.get('rubrik'),
                departement=metadata.get('departement'),
                effective_date=metadata.get('effective_date'),
                issued_date=metadata.get('issued_date'),
                repealed=metadata.get('repealed', False),
                expiration_date=metadata.get('expiration_date'),
                char_count=len(clean_content),
                estimated_tokens=estimate_tokens(clean_content),
                metadata=metadata.copy()
            )
            chunks.append(chunk)

    return chunks


def _chunk_semantic(
    content: str,
    document_id: str,
    metadata: Dict[str, Any],
    max_chunk_size: int,
    overlap_size: int
) -> List[DocumentChunk]:
    """
    Chunk document by semantic boundaries with overlap.

    Tries to split at natural boundaries (paragraphs, sections)
    while respecting the max chunk size.
    """
    chunks = []
    clean_content = _clean_text_for_embedding(content)

    # Split into paragraphs first
    paragraphs = re.split(r'\n\n+', clean_content)

    current_chunk = []
    current_tokens = 0
    chunk_index = 0

    for para in paragraphs:
        para_tokens = estimate_tokens(para)

        if current_tokens + para_tokens > max_chunk_size and current_chunk:
            # Save current chunk
            chunk_text = '\n\n'.join(current_chunk)
            chunk = DocumentChunk(
                content=chunk_text,
                chunk_id=f"{document_id}_sem{chunk_index}",
                document_id=document_id,
                chunk_index=chunk_index,
                total_chunks=0,
                chapter=None,
                paragraph=None,
                section_type="semantic",
                rubrik=metadata.get('rubrik'),
                departement=metadata.get('departement'),
                effective_date=metadata.get('effective_date'),
                issued_date=metadata.get('issued_date'),
                repealed=metadata.get('repealed', False),
                expiration_date=metadata.get('expiration_date'),
                char_count=len(chunk_text),
                estimated_tokens=estimate_tokens(chunk_text),
                metadata=metadata.copy()
            )
            chunks.append(chunk)
            chunk_index += 1

            # Start new chunk with overlap
            overlap_paras = []
            overlap_tokens = 0
            for p in reversed(current_chunk):
                p_tokens = estimate_tokens(p)
                if overlap_tokens + p_tokens <= overlap_size:
                    overlap_paras.insert(0, p)
                    overlap_tokens += p_tokens
                else:
                    break

            current_chunk = overlap_paras
            current_tokens = overlap_tokens

        current_chunk.append(para)
        current_tokens += para_tokens

    # Don't forget the last chunk
    if current_chunk:
        chunk_text = '\n\n'.join(current_chunk)
        chunk = DocumentChunk(
            content=chunk_text,
            chunk_id=f"{document_id}_sem{chunk_index}",
            document_id=document_id,
            chunk_index=chunk_index,
            total_chunks=0,
            chapter=None,
            paragraph=None,
            section_type="semantic",
            rubrik=metadata.get('rubrik'),
            departement=metadata.get('departement'),
            effective_date=metadata.get('effective_date'),
                issued_date=metadata.get('issued_date'),
                repealed=metadata.get('repealed', False),
                expiration_date=metadata.get('expiration_date'),
            char_count=len(chunk_text),
            estimated_tokens=estimate_tokens(chunk_text),
            metadata=metadata.copy()
        )
        chunks.append(chunk)

    return chunks


def _chunk_fixed_size(
    content: str,
    document_id: str,
    metadata: Dict[str, Any],
    max_chunk_size: int,
    overlap_size: int
) -> List[DocumentChunk]:
    """
    Chunk document by fixed token count with overlap.

    Simple chunking that splits text at approximately max_chunk_size tokens
    with overlap_size tokens of overlap between chunks.
    """
    chunks = []
    clean_content = _clean_text_for_embedding(content)

    # Rough calculation: 4 chars per token
    chars_per_chunk = max_chunk_size * 4
    overlap_chars = overlap_size * 4

    start = 0
    chunk_index = 0

    while start < len(clean_content):
        end = start + chars_per_chunk

        # Try to break at a sentence boundary
        if end < len(clean_content):
            # Look for sentence end within last 100 chars
            search_start = max(start + chars_per_chunk - 100, start)
            search_end = min(end + 100, len(clean_content))
            search_text = clean_content[search_start:search_end]

            # Find last sentence boundary
            sentence_end = -1
            for pattern in ['. ', '.\n', '? ', '!\n', '! ']:
                pos = search_text.rfind(pattern)
                if pos > sentence_end:
                    sentence_end = pos

            if sentence_end > 0:
                end = search_start + sentence_end + 1

        chunk_text = clean_content[start:end].strip()

        if chunk_text:
            chunk = DocumentChunk(
                content=chunk_text,
                chunk_id=f"{document_id}_fix{chunk_index}",
                document_id=document_id,
                chunk_index=chunk_index,
                total_chunks=0,
                chapter=None,
                paragraph=None,
                section_type="fixed",
                rubrik=metadata.get('rubrik'),
                departement=metadata.get('departement'),
                effective_date=metadata.get('effective_date'),
                issued_date=metadata.get('issued_date'),
                repealed=metadata.get('repealed', False),
                expiration_date=metadata.get('expiration_date'),
                char_count=len(chunk_text),
                estimated_tokens=estimate_tokens(chunk_text),
                metadata=metadata.copy()
            )
            chunks.append(chunk)
            chunk_index += 1

        start = end - overlap_chars

    return chunks
