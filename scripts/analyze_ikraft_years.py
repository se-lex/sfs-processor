#!/usr/bin/env python3
import json
import os
from pathlib import Path
from collections import defaultdict

def analyze_ikraft_years(json_dir):
    """Analyze years for cases where ikraftOvergangsbestammelse=true without ikraftDateTime"""
    
    year_counts = defaultdict(int)
    examples_by_year = defaultdict(list)
    
    json_path = Path(json_dir)
    
    for json_file in json_path.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check main document
            if data.get('ikraftOvergangsbestammelse') == True and data.get('ikraftDateTime') is None:
                year = data.get('publiceringsar', 'Unknown')
                year_counts[year] += 1
                examples_by_year[year].append({
                    'file': json_file.name,
                    'beteckning': data.get('beteckning'),
                    'type': 'grundforfattning'
                })
            
            # Check andringsforfattningar
            if 'andringsforfattningar' in data:
                for andring in data['andringsforfattningar']:
                    if andring.get('ikraftOvergangsbestammelse') == True and andring.get('ikraftDateTime') is None:
                        year = andring.get('publiceringsar', 'Unknown')
                        year_counts[year] += 1
                        if len(examples_by_year[year]) < 3:  # Limit examples per year
                            examples_by_year[year].append({
                                'file': json_file.name,
                                'beteckning': andring.get('beteckning'),
                                'type': 'andringsforfattning',
                                'grundforfattning': data.get('beteckning')
                            })
                        
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    return year_counts, examples_by_year

if __name__ == "__main__":
    json_dir = "../sfs-jsondata"
    
    print("Analyzing years for ikraftOvergangsbestammelse=true without ikraftDateTime...")
    year_counts, examples_by_year = analyze_ikraft_years(json_dir)
    
    # Sort years
    sorted_years = sorted(year_counts.items(), key=lambda x: x[0], reverse=True)
    
    print(f"\nTotal cases: {sum(year_counts.values())}")
    print("\nDistribution by year:")
    print("-" * 40)
    
    # Group by decade for better overview
    decade_counts = defaultdict(int)
    for year, count in sorted_years:
        if year != 'Unknown':
            decade = f"{year[:3]}0s"
            decade_counts[decade] += count
        print(f"{year}: {count} cases")
    
    print("\nDistribution by decade:")
    print("-" * 40)
    for decade in sorted(decade_counts.keys(), reverse=True):
        print(f"{decade}: {decade_counts[decade]} cases")
    
    # Show recent examples
    print("\nExamples from recent years:")
    print("-" * 40)
    recent_years = [year for year, _ in sorted_years if year != 'Unknown' and int(year) >= 2015][:5]
    
    for year in recent_years:
        if year in examples_by_year:
            print(f"\n{year}:")
            for ex in examples_by_year[year][:2]:
                print(f"  - {ex['beteckning']} ({ex['type']})")
                if 'grundforfattning' in ex:
                    print(f"    Grundförfattning: {ex['grundforfattning']}")
    
    # Show oldest examples
    print("\nExamples from oldest years:")
    print("-" * 40)
    oldest_years = [year for year, _ in sorted_years if year != 'Unknown'][-5:]
    
    for year in reversed(oldest_years):
        if year in examples_by_year:
            print(f"\n{year}:")
            for ex in examples_by_year[year][:2]:
                print(f"  - {ex['beteckning']} ({ex['type']})")
                if 'grundforfattning' in ex:
                    print(f"    Grundförfattning: {ex['grundforfattning']}")