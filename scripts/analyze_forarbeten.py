#!/usr/bin/env python3
"""
Analyze processed SFS documents to find regulations with förarbeten (preparatory works).
"""

import os
import re
import yaml
from pathlib import Path


def extract_frontmatter(content):
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith('---'):
        return {}

    try:
        # Find the end of frontmatter
        end_marker = content.find('\n---\n', 3)
        if end_marker == -1:
            return {}

        frontmatter_content = content[3:end_marker]

        # Parse frontmatter manually due to YAML formatting issues
        frontmatter = {}
        lines = frontmatter_content.strip().split('\n')
        current_key = None
        current_value = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if ':' in line and not line.startswith('-'):
                # New key-value pair
                if current_key and current_value:
                    if current_key == 'forarbeten':
                        frontmatter[current_key] = current_value
                    else:
                        frontmatter[current_key] = ' '.join(current_value) if current_value else ''

                parts = line.split(':', 1)
                current_key = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else ''

                if current_key == 'forarbeten':
                    current_value = [value] if value else []
                else:
                    current_value = [value] if value else []
            elif line.startswith('-') and current_key == 'forarbeten':
                # List item for forarbeten
                item = line[1:].strip()
                if item:
                    current_value.append(item)
            elif current_key and current_value:
                # Continuation of previous value
                current_value.append(line)

        # Handle the last key-value pair
        if current_key and current_value:
            if current_key == 'forarbeten':
                frontmatter[current_key] = current_value
            else:
                frontmatter[current_key] = ' '.join(current_value) if current_value else ''

        return frontmatter
    except Exception as e:
        print(f"Error parsing frontmatter: {e}")
        return {}


def analyze_forarbeten_files(output_dir):
    """Analyze all markdown files and find those with förarbeten."""
    regulations_with_forarbeten = []

    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if file.endswith('.md'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                    frontmatter = extract_frontmatter(content)
                    if frontmatter.get('förarbeten'):
                        regulations_with_forarbeten.append({
                            'beteckning': frontmatter.get('beteckning', 'Unknown'),
                            'rubrik': frontmatter.get('rubrik', 'Unknown'),
                            'förarbeten': frontmatter['förarbeten'],
                            'file': filepath
                        })

                except Exception as e:
                    print(f"Error reading {filepath}: {e}")

    return regulations_with_forarbeten


def format_forarbeten_list(regulations, max_count=100):
    """Format the list of regulations with förarbeten."""
    # Sort by beteckning (year:number)
    regulations.sort(key=lambda x: x['beteckning'])

    # Limit to max_count
    if len(regulations) > max_count:
        regulations = regulations[:max_count]

    print(f"Författningar med förarbeten (max {max_count} st):")
    print("=" * 60)

    for i, reg in enumerate(regulations, 1):
        print(f"\n{i}. {reg['beteckning']} - {reg['rubrik']}")
        print(f"   Förarbeten:")

        forarbeten = reg['förarbeten']
        if isinstance(forarbeten, list):
            for fa in forarbeten:
                if isinstance(fa, dict):
                    typ = fa.get('typ', 'Unknown')
                    beteckning = fa.get('beteckning', 'Unknown')
                    titel = fa.get('titel', 'Ingen titel')
                    print(f"     - {typ} {beteckning}: {titel}")
                else:
                    print(f"     - {fa}")
        else:
            print(f"     - {forarbeten}")


def main():
    output_dir = "sfs-output"

    if not os.path.exists(output_dir):
        print(f"Output directory {output_dir} does not exist!")
        return

    print("Analyzing processed SFS documents for förarbeten...")
    regulations = analyze_forarbeten_files(output_dir)

    print(f"\nFound {len(regulations)} regulations with förarbeten")

    if regulations:
        format_forarbeten_list(regulations)
    else:
        print("No regulations with förarbeten found.")


if __name__ == "__main__":
    main()
