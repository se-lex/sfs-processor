#!/usr/bin/env python3
"""
Analyze HTML file sizes and identify optimization opportunities.
"""
import os
import re
from pathlib import Path
from collections import defaultdict


def analyze_html_file(filepath):
    """Analyze a single HTML file and return size breakdown."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    total_size = len(content.encode('utf-8'))
    
    # Extract different sections
    head_match = re.search(r'<head>(.*?)</head>', content, re.DOTALL)
    head_size = len(head_match.group(0).encode('utf-8')) if head_match else 0
    
    metadata_match = re.search(r'<div class="metadata">.*?</div>', content, re.DOTALL)
    metadata_size = len(metadata_match.group(0).encode('utf-8')) if metadata_match else 0
    
    # Count whitespace
    whitespace_only = re.findall(r'\n\s+', content)
    whitespace_size = sum(len(ws.encode('utf-8')) for ws in whitespace_only)
    
    # Count scripts
    scripts = re.findall(r'<script[^>]*>.*?</script>', content, re.DOTALL)
    script_size = sum(len(s.encode('utf-8')) for s in scripts)
    
    # Count inline attributes
    attributes = re.findall(r'\s(property|datatype|prefix|resource)="[^"]*"', content)
    attribute_size = sum(len(a.encode('utf-8')) for a in attributes)
    
    return {
        'filepath': filepath,
        'total_size': total_size,
        'head_size': head_size,
        'metadata_size': metadata_size,
        'whitespace_size': whitespace_size,
        'script_size': script_size,
        'attribute_size': attribute_size,
        'content_size': total_size - head_size - metadata_size - whitespace_size
    }


def analyze_directory(directory):
    """Analyze all HTML files in directory."""
    results = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                results.append(analyze_html_file(filepath))
    
    return results


def print_analysis(results):
    """Print analysis results."""
    print("\n" + "="*80)
    print("HTML FILE SIZE ANALYSIS")
    print("="*80)
    
    total_bytes = sum(r['total_size'] for r in results)
    total_head = sum(r['head_size'] for r in results)
    total_metadata = sum(r['metadata_size'] for r in results)
    total_whitespace = sum(r['whitespace_size'] for r in results)
    total_script = sum(r['script_size'] for r in results)
    total_attribute = sum(r['attribute_size'] for r in results)
    
    print(f"\nTotal files analyzed: {len(results)}")
    print(f"Total size: {total_bytes:,} bytes ({total_bytes/1024:.1f} KB)")
    print(f"Average file size: {total_bytes/len(results):,.0f} bytes ({total_bytes/len(results)/1024:.1f} KB)")
    
    print("\n" + "-"*80)
    print("SIZE BREAKDOWN ACROSS ALL FILES:")
    print("-"*80)
    print(f"Head section:      {total_head:8,} bytes ({total_head/total_bytes*100:5.1f}%)")
    print(f"Metadata section:  {total_metadata:8,} bytes ({total_metadata/total_bytes*100:5.1f}%)")
    print(f"Scripts:           {total_script:8,} bytes ({total_script/total_bytes*100:5.1f}%)")
    print(f"Attributes:        {total_attribute:8,} bytes ({total_attribute/total_bytes*100:5.1f}%)")
    print(f"Whitespace:        {total_whitespace:8,} bytes ({total_whitespace/total_bytes*100:5.1f}%)")
    
    print("\n" + "-"*80)
    print("INDIVIDUAL FILE SIZES:")
    print("-"*80)
    for r in sorted(results, key=lambda x: x['total_size'], reverse=True):
        filename = Path(r['filepath']).name
        parent_dir = '/'.join(Path(r['filepath']).parts[-3:-1])
        print(f"{parent_dir:20s} {r['total_size']:8,} bytes ({r['total_size']/1024:6.1f} KB)")
    
    print("\n" + "="*80)
    print("OPTIMIZATION OPPORTUNITIES:")
    print("="*80)
    print(f"1. Whitespace removal:     ~{total_whitespace:,} bytes ({total_whitespace/total_bytes*100:.1f}%)")
    print(f"2. Script optimization:    ~{total_script:,} bytes ({total_script/total_bytes*100:.1f}%)")
    print(f"3. Metadata optimization:  ~{total_metadata:,} bytes ({total_metadata/total_bytes*100:.1f}%)")
    print(f"4. Attribute optimization: ~{total_attribute:,} bytes ({total_attribute/total_bytes*100:.1f}%)")
    
    potential_savings = total_whitespace * 0.8 + total_script * 0.2 + total_metadata * 0.15
    print(f"\nEstimated potential savings: {potential_savings:,.0f} bytes ({potential_savings/total_bytes*100:.1f}%)")
    print("="*80 + "\n")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python analyze_sizes.py <directory>")
        sys.exit(1)
    
    directory = sys.argv[1]
    results = analyze_directory(directory)
    print_analysis(results)
