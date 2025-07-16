"""File utility functions for SFS document processing."""

from pathlib import Path
from typing import List


def filter_json_files(json_files: List[Path], filter_criteria: str) -> List[Path]:
    """
    Filter JSON files based on filename containing year or ID patterns.

    Args:
        json_files: List of JSON file paths
        filter_criteria: Filter string containing years (YYYY) or IDs (YYYY:NNN)
                        Can be comma-separated for multiple criteria

    Returns:
        List[Path]: Filtered list of JSON files
    """
    if not filter_criteria:
        return json_files

    # Parse filter criteria - split by comma and strip whitespace
    criteria = [c.strip() for c in filter_criteria.split(',') if c.strip()]

    filtered_files = []

    for json_file in json_files:
        filename = json_file.stem  # Get filename without extension

        # Check if filename matches any of the criteria
        for criterion in criteria:
            # Check for exact beteckning match (YYYY:NNN format)
            if ':' in criterion and criterion.replace(':', '-') in filename:
                filtered_files.append(json_file)
                break
            # Check for year match (YYYY format)
            elif ':' not in criterion and f"{criterion}-" in filename:
                filtered_files.append(json_file)
                break
            # Check for partial filename match (e.g., "sfs-2024-925" matches "sfs-2024-925.json")
            elif criterion in filename:
                filtered_files.append(json_file)
                break

    return filtered_files


def read_file_content(file_path: Path) -> str:
    """
    Read file content with proper error handling.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        str: File content, or empty string if reading failed
        
    Raises:
        IOError: If file cannot be read
        UnicodeDecodeError: If file encoding is invalid
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except (IOError, UnicodeDecodeError) as e:
        raise IOError(f"Fel vid läsning av {file_path}: {e}")


def save_to_disk(file_path: Path, content: str) -> None:
    """Save content to disk with proper error handling.

    Args:
        file_path: Path where to save the file
        content: Content to write to the file
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Skrev till disk: {file_path}")
    except IOError as e:
        print(f"Fel vid skrivning av {file_path}: {e}")
