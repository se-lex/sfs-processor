#!/usr/bin/env python3
"""
Analyze the context and location of chapter revocation patterns in SFS documents.
"""

import re
import json
from collections import defaultdict, Counter

def analyze_context_patterns():
    """Analyze where chapter revocation patterns appear in documents."""
    
    # Read the comprehensive report
    with open('/Users/martin/Code/sfs-md/comprehensive_report.txt', 'r') as f:
        content = f.read()
    
    # Pattern to match individual entries - more flexible
    entry_pattern = r'Document: ([^\n]+).*?Match: ([^\n]+).*?Full sentence: ([^\n]+).*?Context: (.*?)(?=\n\n.*?Document:|$)'
    
    matches = re.findall(entry_pattern, content, re.DOTALL)
    
    # If that doesn't work, try a different approach
    if len(matches) < 10:
        # Split by document entries
        document_sections = re.split(r'\n\n\d+\. Document:', content)
        matches = []
        
        for section in document_sections:
            if 'kap. har upphävts genom' in section or 'kap. Har upphävts genom' in section:
                # Extract document info
                doc_match = re.search(r'([^\n]+)', section)
                if doc_match:
                    doc_id = doc_match.group(1)
                    
                    # Extract match type
                    match_type_match = re.search(r'Match: ([^\n]+)', section)
                    match_type = match_type_match.group(1) if match_type_match else 'unknown'
                    
                    # Extract full sentence
                    sentence_match = re.search(r'Full sentence: ([^\n]+)', section)
                    full_sentence = sentence_match.group(1) if sentence_match else 'unknown'
                    
                    # Extract context
                    context_match = re.search(r'Context: (.*?)(?=\n\n|$)', section, re.DOTALL)
                    context = context_match.group(1) if context_match else 'unknown'
                    
                    matches.append((doc_id, match_type, full_sentence, context))
    
    print(f"Total matches found: {len(matches)}")
    print("=" * 60)
    
    # Categories for analysis
    categories = {
        'overgangsbestammelser': 0,
        'before_overgangsbestammelser': 0,
        'chapter_transitions': 0,
        'main_body': 0,
        'end_of_document': 0
    }
    
    context_patterns = {
        'has_overgangsbestammelser': 0,
        'has_chapter_header': 0,
        'has_section_number': 0,
        'has_lag_reference': 0,
        'has_forordning_reference': 0,
        'isolated_revocation': 0
    }
    
    detailed_analysis = []
    
    for i, (doc_id, match_type, full_sentence, context) in enumerate(matches):
        # Clean up context
        context = context.strip()
        
        # Analyze context patterns
        analysis = {
            'doc_id': doc_id,
            'match_type': match_type,
            'full_sentence': full_sentence,
            'context': context[:200],  # First 200 chars
            'has_overgangsbestammelser': 'Övergångsbestämmelser' in context,
            'has_chapter_header': bool(re.search(r'\d+\s*kap\.\s*[A-ZÅÄÖ]', context)),
            'has_section_number': bool(re.search(r'\d+\s*§', context)),
            'has_temporal_marker': bool(re.search(r'(träder i kraft|ikraftträdande|upphör|gäller)', context)),
            'position_indicator': 'unknown'
        }
        
        # Determine position in document - check full context
        full_context = context
        
        if 'Övergångsbestämmelser' in full_context:
            analysis['position_indicator'] = 'in_overgangsbestammelser'
            categories['overgangsbestammelser'] += 1
        # Check if appears right before Övergångsbestämmelser section
        elif re.search(r'Övergångsbestämmelser\s*\d{4}:', full_context):
            analysis['position_indicator'] = 'before_overgangsbestammelser'
            categories['before_overgangsbestammelser'] += 1
        # Check if it's between chapters (next thing is chapter header)
        elif re.search(r'kap\.\s*[Hh]ar upphävts[^\\n]*\\n\\n[^\\n]*\\n\\n\d+\s*kap\.\s*[A-ZÅÄÖ]', full_context):
            analysis['position_indicator'] = 'between_chapters'
            categories['chapter_transitions'] += 1
        # Check if it's at the end of document (before transitional provisions)
        elif re.search(r'kap\.\s*[Hh]ar upphävts[^\\n]*\\n\\n[^\\n]*Övergångsbestämmelser', full_context):
            analysis['position_indicator'] = 'end_of_document'
            categories['end_of_document'] += 1
        else:
            analysis['position_indicator'] = 'main_body'
            categories['main_body'] += 1
        
        # Update pattern counts
        for pattern in context_patterns:
            if pattern in analysis and analysis[pattern]:
                context_patterns[pattern] += 1
        
        detailed_analysis.append(analysis)
    
    # Print summary statistics
    print("LOCATION ANALYSIS:")
    print("-" * 30)
    for category, count in categories.items():
        percentage = (count / len(matches)) * 100
        print(f"{category.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
    
    print("\nCONTEXT PATTERNS:")
    print("-" * 30)
    for pattern, count in context_patterns.items():
        percentage = (count / len(matches)) * 100
        print(f"{pattern.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
    
    # Show examples from each category
    print("\nEXAMPLES BY CATEGORY:")
    print("=" * 60)
    
    by_position = defaultdict(list)
    for analysis in detailed_analysis:
        by_position[analysis['position_indicator']].append(analysis)
    
    for position, examples in by_position.items():
        print(f"\n{position.replace('_', ' ').upper()} ({len(examples)} examples):")
        print("-" * 40)
        
        # Show up to 3 examples
        for i, example in enumerate(examples[:3]):
            print(f"Example {i+1}:")
            print(f"  Document: {example['doc_id']}")
            print(f"  Sentence: {example['full_sentence']}")
            print(f"  Context: {example['context']}")
            print()
    
    # Analyze document types
    print("\nDOCUMENT TYPE ANALYSIS:")
    print("-" * 30)
    
    doc_types = Counter()
    for analysis in detailed_analysis:
        if 'lag' in analysis['match_type']:
            doc_types['lag'] += 1
        elif 'förordning' in analysis['match_type']:
            doc_types['förordning'] += 1
        else:
            doc_types['other'] += 1
    
    for doc_type, count in doc_types.items():
        percentage = (count / len(matches)) * 100
        print(f"{doc_type.title()}: {count} ({percentage:.1f}%)")
    
    # Find common structural patterns
    print("\nSTRUCTURAL PATTERNS:")
    print("-" * 30)
    
    header_patterns = defaultdict(int)
    for analysis in detailed_analysis:
        context = analysis['context']
        
        # Look for common headers or section patterns
        headers = re.findall(r'(\d+\s*kap\.\s*[A-ZÅÄÖ][^\\n]*)', context)
        for header in headers:
            header_patterns[header.strip()] += 1
    
    # Show most common header patterns
    print("Most common chapter headers near revocations:")
    for header, count in sorted(header_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {count}x: {header}")
    
    return detailed_analysis

if __name__ == "__main__":
    results = analyze_context_patterns()