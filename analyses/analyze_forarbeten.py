#!/usr/bin/env python3
"""
Script to analyze JSON files in sfs-jsondata directory for 'forarbeten' content.
"""

import json
import os
from collections import defaultdict
import re

def analyze_forarbeten_field(json_data):
    """Extract and analyze the forarbeten field from JSON data."""
    try:
        register = json_data.get('register', {})
        forarbeten = register.get('forarbeten')
        
        if forarbeten is None:
            return None, None
        
        if isinstance(forarbeten, str):
            forarbeten = forarbeten.strip()
            if not forarbeten:
                return None, None
            return forarbeten, len(forarbeten)
        
        return str(forarbeten), len(str(forarbeten)) if forarbeten else None
    
    except (KeyError, TypeError, ValueError) as e:
        print(f"Error analyzing forarbeten field: {e}")
        return None, None

def analyze_forarbeten_content(forarbeten_text):
    """Analyze the content of forarbeten field."""
    if not forarbeten_text:
        return {}
    
    analysis = {}
    
    # Count propositions (Prop.)
    prop_matches = re.findall(r'Prop\.\s*\d+[:/]\d+', forarbeten_text, re.IGNORECASE)
    analysis['propositioner'] = len(prop_matches)
    
    # Count committee reports (Bet., Rskr, etc.)
    bet_matches = re.findall(r'Bet\.\s*\d+[:/]\d+', forarbeten_text, re.IGNORECASE)
    analysis['betankanden'] = len(bet_matches)
    
    # Count riksdag decisions (Rskr)
    rskr_matches = re.findall(r'Rskr\s*\d+[:/]\d+', forarbeten_text, re.IGNORECASE)
    analysis['riksdagsskrivelser'] = len(rskr_matches)
    
    # Count legislative committee reports (LU, AU, etc.)
    lu_matches = re.findall(r'\d+[A-Z]+\s*\d+[:/]\d+', forarbeten_text)
    analysis['utskottsutlatanden'] = len(lu_matches)
    
    # Check for EU references
    eu_matches = re.findall(r'(EG|EU|EEG)', forarbeten_text, re.IGNORECASE)
    analysis['eu_referenser'] = len(eu_matches) > 0
    
    return analysis

def main():
    directory_path = "/Users/martin/Code/sfs-jsondata"
    
    if not os.path.exists(directory_path):
        print(f"Error: Directory {directory_path} does not exist.")
        print("Please make sure the path is correct.")
        return
    
    total_files = 0
    files_with_forarbeten = 0
    forarbeten_content_stats = defaultdict(int)
    forarbeten_examples = []
    content_analysis = defaultdict(int)
    
    print(f"Analyzing JSON files in {directory_path}...")
    print("-" * 50)
    
    # Walk through all subdirectories
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                total_files += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    forarbeten_text, text_length = analyze_forarbeten_field(data)
                    
                    if forarbeten_text is not None:
                        files_with_forarbeten += 1
                        
                        # Store examples (first 10)
                        if len(forarbeten_examples) < 10:
                            relative_path = os.path.relpath(file_path, directory_path)
                            forarbeten_examples.append({
                                'file': relative_path,
                                'content': forarbeten_text[:200] + "..." if len(forarbeten_text) > 200 else forarbeten_text
                            })
                        
                        # Analyze content
                        analysis = analyze_forarbeten_content(forarbeten_text)
                        for key, value in analysis.items():
                            if isinstance(value, bool):
                                if value:
                                    content_analysis[key] += 1
                            else:
                                content_analysis[f"total_{key}"] += value
                                if value > 0:
                                    content_analysis[f"files_with_{key}"] += 1
                        
                        # Track length distribution
                        if text_length:
                            if text_length < 50:
                                forarbeten_content_stats['kort (< 50 tecken)'] += 1
                            elif text_length < 200:
                                forarbeten_content_stats['medel (50-200 tecken)'] += 1
                            else:
                                forarbeten_content_stats['lång (> 200 tecken)'] += 1
                
                except (json.JSONDecodeError, KeyError, FileNotFoundError, UnicodeDecodeError) as e:
                    print(f"Error processing {file_path}: {e}")
                
                # Progress indicator
                if total_files % 1000 == 0:
                    print(f"Processed {total_files} files...")
    
    # Calculate percentage
    percentage = (files_with_forarbeten / total_files * 100) if total_files > 0 else 0
    
    print(f"\n{'='*60}")
    print("RESULTAT - Analys av 'forarbeten' fält")
    print(f"{'='*60}")
    print(f"Totalt antal JSON-filer: {total_files:,}")
    print(f"Filer med forarbeten-innehåll: {files_with_forarbeten:,}")
    print(f"Procentsats: {percentage:.2f}%")
    
    if files_with_forarbeten > 0:
        print(f"\n{'='*40}")
        print("FÖRDELNING AV INNEHÅLLSLÄNGD")
        print(f"{'='*40}")
        for category, count in forarbeten_content_stats.items():
            percent = (count / files_with_forarbeten * 100)
            print(f"{category}: {count:,} ({percent:.1f}%)")
        
        print(f"\n{'='*40}")
        print("INNEHÅLLSANALYS")
        print(f"{'='*40}")
        print(f"Filer med propositioner: {content_analysis.get('files_with_propositioner', 0):,}")
        print(f"Totalt antal propositioner: {content_analysis.get('total_propositioner', 0):,}")
        print(f"Filer med betänkanden: {content_analysis.get('files_with_betankanden', 0):,}")
        print(f"Filer med riksdagsskrivelser: {content_analysis.get('files_with_riksdagsskrivelser', 0):,}")
        print(f"Filer med utskottsutlåtanden: {content_analysis.get('files_with_utskottsutlatanden', 0):,}")
        print(f"Filer med EU-referenser: {content_analysis.get('eu_referenser', 0):,}")
        
        print(f"\n{'='*40}")
        print("EXEMPEL PÅ FORARBETEN-INNEHÅLL")
        print(f"{'='*40}")
        for i, example in enumerate(forarbeten_examples, 1):
            print(f"{i}. {example['file']}")
            print(f"   Innehåll: {example['content']}")
            print()
    
    print(f"\n{'='*60}")
    print("REFLEKTION ÖVER INNEHÅLLET")
    print(f"{'='*60}")
    
    if percentage < 10:
        print("📊 LÅGT TÄCKNING: Mycket få filer har forarbeten-information.")
        print("   Detta kan indikera att:")
        print("   - Många författningar saknar dokumenterade förarbeten")
        print("   - Data kan vara ofullständig för äldre författningar")
        print("   - Vissa typer av författningar (förordningar) har sällan förarbeten")
    elif percentage < 30:
        print("📊 MÅTTLIG TÄCKNING: En mindre del av filerna har forarbeten-information.")
        print("   Detta är normalt eftersom:")
        print("   - Inte alla författningar har explicita förarbeten")
        print("   - Förordningar har ofta färre förarbeten än lagar")
    elif percentage < 60:
        print("📊 GOD TÄCKNING: En betydande del av filerna har forarbeten-information.")
        print("   Detta indikerar god dokumentation av lagstiftningsprocessen.")
    else:
        print("📊 MYCKET GOD TÄCKNING: Majoriteten av filerna har forarbeten-information.")
        print("   Detta visar på omfattande dokumentation av förarbeten.")
    
    if files_with_forarbeten > 0:
        prop_coverage = content_analysis.get('files_with_propositioner', 0) / files_with_forarbeten * 100
        print(f"\n📋 PROPOSITIONER: {prop_coverage:.1f}% av filerna med förarbeten innehåller propositioner")
        print("   Propositioner är den vanligaste typen av förarbete för lagar.")
        
        if content_analysis.get('eu_referenser', 0) > 0:
            eu_coverage = content_analysis.get('eu_referenser', 0) / files_with_forarbeten * 100
            print(f"\n🇪🇺 EU-REFERENSER: {eu_coverage:.1f}% av filerna med förarbeten har EU-koppling")
            print("   Detta visar på EU:s påverkan på svensk lagstiftning.")

if __name__ == "__main__":
    main()
