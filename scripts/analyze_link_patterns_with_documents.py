#!/usr/bin/env python3
"""
Link Pattern Analysis with Document Examples
Analyzes invalid links and provides specific SFS document examples for each pattern type.
"""

import json
import re
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set

def extract_sfs_id(filepath: str) -> str:
    """Extract SFS ID from file path"""
    filename = Path(filepath).stem
    # Remove any suffix like _kap1, _kap2, etc.
    base_name = re.sub(r'_kap\d+$', '', filename)
    return base_name

def analyze_invalid_link(link_text: str, link_target: str, document_content: str) -> str:
    """Analyze an invalid link and categorize it"""
    
    # Check if it's a cross-chapter reference
    if link_target.startswith('#kap') and '.' in link_target:
        # Extract chapter and section from target
        match = re.search(r'#kap(\d+)\.(.+)', link_target)
        if match:
            target_chapter = match.group(1)
            target_section = match.group(2)
            
            # Check if the chapter exists in the document
            chapter_pattern = f'## {target_chapter} kap\\.'
            if re.search(chapter_pattern, document_content):
                # Chapter exists, but section doesn't
                return f"cross_chapter_nonexistent_section"
            else:
                # Whole chapter doesn't exist
                return f"cross_chapter_nonexistent_chapter"
    
    # Check if it's missing chapter context
    if not link_target.startswith('#kap') and re.search(r'^\d+[a-z]?$', link_target.replace('#', '')):
        # Check if document has chapters
        if re.search(r'## \d+ kap\.', document_content):
            return "missing_chapter_context"
    
    # Simple non-existent section
    if link_target.startswith('#') and not link_target.startswith('#kap'):
        return "simple_nonexistent_section"
    
    return "other"

def analyze_document_links(md_file: str) -> List[Tuple[str, str, str]]:
    """Analyze all links in a document and return invalid ones with patterns"""
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return []
    
    # Find all markdown links
    link_pattern = r'\[([^\]]+)\]\(#([^)]+)\)'
    links = re.findall(link_pattern, content)
    
    invalid_links = []
    
    for link_text, link_target in links:
        # Check if target exists in document
        target_id = link_target
        if f'id="{target_id}"' not in content:
            pattern = analyze_invalid_link(link_text, f'#{link_target}', content)
            invalid_links.append((link_text, f'#{link_target}', pattern))
    
    return invalid_links

def main():
    """Main analysis function"""
    
    # Find all markdown files (test with newly regenerated files)
    regen_dir = Path('/Users/martin/Code/sfs-md/sfs-regenerated-output')
    md_files = list(regen_dir.glob('**/*.md'))
    
    # Filter out any non-SFS files if needed
    md_files = [f for f in md_files if f.name.startswith('sfs-') and f.name.endswith('.md')]
    
    print(f"Found {len(md_files)} markdown files")
    
    # Pattern categories with examples
    pattern_examples = defaultdict(list)
    pattern_documents = defaultdict(set)
    
    total_invalid = 0
    documents_processed = 0
    
    for md_file in md_files[:2000]:  # Limit to first 2000 for performance
        sfs_id = extract_sfs_id(str(md_file))
        invalid_links = analyze_document_links(str(md_file))
        
        if invalid_links:
            documents_processed += 1
            
        for link_text, link_target, pattern in invalid_links:
            total_invalid += 1
            pattern_examples[pattern].append({
                'sfs_id': sfs_id,
                'link_text': link_text,
                'link_target': link_target,
                'file': str(md_file)
            })
            pattern_documents[pattern].add(sfs_id)
    
    print(f"\nProcessed {documents_processed} documents with invalid links")
    print(f"Total invalid links found: {total_invalid}")
    
    # Generate detailed report
    report = []
    report.append("# Link Pattern Analysis with Document Examples")
    report.append("")
    report.append(f"**Total documents processed:** {len(md_files)}")
    report.append(f"**Documents with invalid links:** {documents_processed}")
    report.append(f"**Total invalid links:** {total_invalid}")
    report.append("")
    
    # Sort patterns by frequency
    sorted_patterns = sorted(pattern_examples.items(), key=lambda x: len(x[1]), reverse=True)
    
    for pattern, examples in sorted_patterns:
        count = len(examples)
        percentage = (count / total_invalid * 100) if total_invalid > 0 else 0
        doc_count = len(pattern_documents[pattern])
        
        report.append(f"## {pattern.replace('_', ' ').title()}")
        report.append(f"**Count:** {count} links ({percentage:.1f}%)")
        report.append(f"**Documents affected:** {doc_count}")
        report.append("")
        
        # Show first 10 examples with SFS IDs
        report.append("### Examples:")
        for i, example in enumerate(examples[:10]):
            report.append(f"- **{example['sfs_id']}**: `{example['link_text']}` → `{example['link_target']}`")
        
        if len(examples) > 10:
            report.append(f"- ... and {len(examples) - 10} more examples")
        
        report.append("")
        
        # Show affected documents
        report.append("### Affected Documents:")
        doc_list = sorted(list(pattern_documents[pattern]))[:20]
        for doc in doc_list:
            report.append(f"- {doc}")
        
        if len(pattern_documents[pattern]) > 20:
            report.append(f"- ... and {len(pattern_documents[pattern]) - 20} more documents")
        
        report.append("")
        report.append("---")
        report.append("")
    
    # Write report
    report_path = '/Users/martin/Code/sfs-md/reports/link_patterns_with_documents.md'
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print(f"\nReport saved to: {report_path}")
    
    # Print summary
    print("\n=== SUMMARY ===")
    for pattern, examples in sorted_patterns:
        count = len(examples)
        percentage = (count / total_invalid * 100) if total_invalid > 0 else 0
        doc_count = len(pattern_documents[pattern])
        print(f"{pattern}: {count} links ({percentage:.1f}%) in {doc_count} documents")

if __name__ == "__main__":
    main()