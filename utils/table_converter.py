#!/usr/bin/env python3
"""
Utility for converting table-like structures to Markdown tables.

This module detects and converts text tables that use tabs or multiple spaces
for column separation into proper Markdown table syntax.

Supports:
- Tab-separated tables
- Space-separated tables with consistent alignment
- Tables with or without headers
- Multi-line content within cells (basic support)
"""

import re
from typing import List, Tuple, Optional
from pathlib import Path


def detect_table_structure(lines: List[str]) -> Optional[Tuple[int, int, str]]:
    """
    Detect if a sequence of lines forms a table structure.
    
    Args:
        lines: List of lines to analyze
        
    Returns:
        Tuple of (start_index, end_index, separator_type) if table found, None otherwise.
        separator_type is either 'tab' or 'space'
    """
    if len(lines) < 2:
        return None
    
    # Skip YAML front matter and markdown elements
    def is_table_candidate(line: str) -> bool:
        line_stripped = line.strip()
        # Skip empty lines, YAML, markdown headers, etc.
        if not line_stripped or line_stripped.startswith('---') or line_stripped.startswith('#'):
            return False
        # Skip lines that start with markdown list markers
        if line_stripped.startswith(('- ', '* ', '+ ')):
            return False
        return True
    
    # Check for tab-separated tables
    tab_lines = []
    for i, line in enumerate(lines):
        if is_table_candidate(line) and '\t' in line:
            parts = line.split('\t')
            # Must have at least 2 non-empty parts
            non_empty_parts = [p.strip() for p in parts if p.strip()]
            if len(non_empty_parts) >= 2:
                tab_lines.append(i)
    
    # If we have consecutive tab-separated lines, it's likely a table
    if len(tab_lines) >= 2:
        consecutive_groups = []
        current_group = [tab_lines[0]]
        
        for i in range(1, len(tab_lines)):
            if tab_lines[i] - tab_lines[i-1] <= 2:  # Allow 1 empty line between rows
                current_group.append(tab_lines[i])
            else:
                if len(current_group) >= 2:
                    consecutive_groups.append(current_group)
                current_group = [tab_lines[i]]
        
        if len(current_group) >= 2:
            consecutive_groups.append(current_group)
        
        # Return the largest group
        if consecutive_groups:
            largest_group = max(consecutive_groups, key=len)
            return (largest_group[0], largest_group[-1], 'tab')
    
    # Check for space-separated tables (4+ consecutive spaces to be more conservative)
    space_pattern = re.compile(r'\s{4,}')
    space_lines = []
    
    for i, line in enumerate(lines):
        if is_table_candidate(line) and space_pattern.search(line):
            parts = space_pattern.split(line)
            # Must have at least 2 non-empty parts
            non_empty_parts = [p.strip() for p in parts if p.strip()]
            if len(non_empty_parts) >= 2:
                space_lines.append(i)
    
    # Similar logic for space-separated tables
    if len(space_lines) >= 2:
        consecutive_groups = []
        current_group = [space_lines[0]]
        
        for i in range(1, len(space_lines)):
            if space_lines[i] - space_lines[i-1] <= 2:
                current_group.append(space_lines[i])
            else:
                if len(current_group) >= 2:
                    consecutive_groups.append(current_group)
                current_group = [space_lines[i]]
        
        if len(current_group) >= 2:
            consecutive_groups.append(current_group)
        
        if consecutive_groups:
            largest_group = max(consecutive_groups, key=len)
            return (largest_group[0], largest_group[-1], 'space')
    
    return None


def parse_table_row(line: str, separator_type: str) -> List[str]:
    """
    Parse a single table row into columns.
    
    Args:
        line: The line to parse
        separator_type: Either 'tab' or 'space'
        
    Returns:
        List of column values
    """
    if separator_type == 'tab':
        return [col.strip() for col in line.split('\t')]
    else:  # space
        # Split on 3+ consecutive spaces
        columns = re.split(r'\s{3,}', line)
        return [col.strip() for col in columns if col.strip()]


def normalize_table_rows(rows: List[List[str]]) -> List[List[str]]:
    """
    Normalize table rows to have the same number of columns and remove empty columns.
    
    Args:
        rows: List of rows, where each row is a list of columns
        
    Returns:
        Normalized rows with consistent column count and empty columns removed
    """
    if not rows:
        return rows
    
    # Find the maximum number of columns
    max_cols = max(len(row) for row in rows)
    
    # Pad rows with empty strings first
    padded_rows = []
    for row in rows:
        padded_row = row.copy()
        while len(padded_row) < max_cols:
            padded_row.append('')
        padded_rows.append(padded_row)
    
    # Identify columns that are entirely empty
    empty_columns = set()
    for col_idx in range(max_cols):
        if all(not row[col_idx].strip() for row in padded_rows):
            empty_columns.add(col_idx)
    
    # Remove empty columns
    if empty_columns:
        normalized_rows = []
        for row in padded_rows:
            filtered_row = [col for i, col in enumerate(row) if i not in empty_columns]
            normalized_rows.append(filtered_row)
        return normalized_rows
    
    return padded_rows


def convert_to_markdown_table(lines: List[str], start_idx: int, end_idx: int, separator_type: str) -> List[str]:
    """
    Convert detected table structure to Markdown table format.
    
    Args:
        lines: Original lines
        start_idx: Start index of table
        end_idx: End index of table
        separator_type: Either 'tab' or 'space'
        
    Returns:
        List of lines with Markdown table
    """
    table_lines = lines[start_idx:end_idx + 1]
    
    # Parse rows
    rows = []
    for line in table_lines:
        if line.strip():  # Skip empty lines
            row = parse_table_row(line, separator_type)
            if row:  # Only add non-empty rows
                rows.append(row)
    
    if len(rows) < 2:
        return lines[start_idx:end_idx + 1]  # Return original if not enough data
    
    # Normalize column count
    rows = normalize_table_rows(rows)
    
    if not rows:
        return lines[start_idx:end_idx + 1]
    
    num_cols = len(rows[0])
    
    # Build Markdown table
    markdown_lines = []
    
    # Add header row (first row)
    header = '| ' + ' | '.join(rows[0]) + ' |'
    markdown_lines.append(header)
    
    # Add separator row
    separator = '|' + '|'.join([' --- ' for _ in range(num_cols)]) + '|'
    markdown_lines.append(separator)
    
    # Add data rows
    for row in rows[1:]:
        data_row = '| ' + ' | '.join(row) + ' |'
        markdown_lines.append(data_row)
    
    return markdown_lines


def convert_tables_in_markdown(markdown_content: str, verbose: bool = False) -> str:
    """Convert table-like structures in markdown content to proper Markdown tables.
    
    Args:
        markdown_content: The markdown content to process
        verbose: Whether to print verbose output about conversions
        
    Returns:
        str: The markdown content with tables converted
    """
    lines = markdown_content.split('\n')
    result_lines = []
    i = 0
    tables_converted = 0
    
    while i < len(lines):
        # Look ahead for table structures (check next 10 lines or until end)
        end_check = min(i + 10, len(lines))
        check_lines = lines[i:end_check]
        
        table_info = detect_table_structure(check_lines)
        
        if table_info:
            start_rel, end_rel, sep_type = table_info
            start_abs = i + start_rel
            end_abs = i + end_rel
            
            # Add lines before table
            result_lines.extend(lines[i:start_abs])
            
            # Convert table
            table_markdown = convert_to_markdown_table(lines, start_abs, end_abs, sep_type)
            result_lines.extend(table_markdown)
            
            if verbose:
                print(f"Converted table at lines {start_abs + 1}-{end_abs + 1} (separator: {sep_type})")
            tables_converted += 1
            
            # Move past the table
            i = end_abs + 1
        else:
            # No table found, add current line and move on
            result_lines.append(lines[i])
            i += 1
    
    if verbose and tables_converted > 0:
        print(f"Total tables converted: {tables_converted}")
    
    return '\n'.join(result_lines)


def process_file_tables(file_path: str, output_path: str = None) -> bool:
    """
    Process a file to convert table-like structures to Markdown tables.
    
    Args:
        file_path: Path to input file
        output_path: Path to output file (if None, overwrites input file)
        
    Returns:
        True if any tables were converted, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except (IOError, UnicodeDecodeError) as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    # Remove trailing newlines for processing
    lines = [line.rstrip('\n\r') for line in lines]
    
    modified = False
    result_lines = []
    i = 0
    
    while i < len(lines):
        # Look ahead for table structures (check next 10 lines or until end)
        end_check = min(i + 10, len(lines))
        check_lines = lines[i:end_check]
        
        table_info = detect_table_structure(check_lines)
        
        if table_info:
            start_rel, end_rel, sep_type = table_info
            start_abs = i + start_rel
            end_abs = i + end_rel
            
            # Add lines before table
            result_lines.extend(lines[i:start_abs])
            
            # Convert table
            table_markdown = convert_to_markdown_table(lines, start_abs, end_abs, sep_type)
            result_lines.extend(table_markdown)
            
            print(f"Converted table at lines {start_abs + 1}-{end_abs + 1} (separator: {sep_type})")
            modified = True
            
            # Move past the table
            i = end_abs + 1
        else:
            # No table found, add current line and move on
            result_lines.append(lines[i])
            i += 1
    
    if modified:
        # Write output
        output_file = output_path if output_path else file_path
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for line in result_lines:
                    f.write(line + '\n')
            print(f"Successfully processed {file_path}")
            return True
        except IOError as e:
            print(f"Error writing to {output_file}: {e}")
            return False
    
    return False


def process_directory_tables(input_dir: str, pattern: str = "*.md") -> None:
    """
    Process all files in a directory to convert tables.
    
    Args:
        input_dir: Directory to process
        pattern: File pattern to match (default: "*.md")
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"Error: Directory {input_dir} does not exist.")
        return
    
    if not input_path.is_dir():
        print(f"Error: {input_dir} is not a directory.")
        return
    
    # Find matching files
    files = list(input_path.rglob(pattern))
    
    if not files:
        print(f"No files matching pattern '{pattern}' found in {input_dir}")
        return
    
    print(f"Found {len(files)} files to process")
    
    converted_count = 0
    processed_count = 0
    
    for file_path in files:
        print(f"\nProcessing {file_path.name}...")
        processed_count += 1
        
        if process_file_tables(str(file_path)):
            converted_count += 1
    
    print(f"\nSummary:")
    print(f"Processed {processed_count} files")
    print(f"Files with converted tables: {converted_count}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python utils/table_converter.py <file_or_directory>")
        print("Examples:")
        print("  python utils/table_converter.py ../sfs-export/2016/sfs-2016-1019.md")
        print("  python utils/table_converter.py ../sfs-export/")
        sys.exit(1)
    
    target = sys.argv[1]
    target_path = Path(target)
    
    if target_path.is_file():
        print(f"Processing single file: {target}")
        process_file_tables(target)
    elif target_path.is_dir():
        print(f"Processing directory: {target}")
        process_directory_tables(target)
    else:
        print(f"Error: {target} is not a valid file or directory")
        sys.exit(1)