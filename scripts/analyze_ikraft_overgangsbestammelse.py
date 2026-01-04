#!/usr/bin/env python3
import json
import os
from pathlib import Path


def analyze_ikraft_overgangsbestammelse(json_dir):
    """Analyze JSON files to check ikraftOvergangsbestammelse patterns"""

    stats = {
        'total_files': 0,
        'files_with_ikraft_true': 0,
        'cases_ikraft_true_no_datetime': 0,
        'cases_ikraft_true_with_datetime': 0,
        'examples_no_datetime': [],
        'examples_with_datetime': []
    }

    json_path = Path(json_dir)

    for json_file in json_path.glob('*.json'):
        stats['total_files'] += 1

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check main document
            if data.get('ikraftOvergangsbestammelse'):
                stats['files_with_ikraft_true'] += 1

                if data.get('ikraftDateTime') is None:
                    stats['cases_ikraft_true_no_datetime'] += 1
                    if len(stats['examples_no_datetime']) < 5:
                        stats['examples_no_datetime'].append({
                            'file': json_file.name,
                            'beteckning': data.get('beteckning'),
                            'ikraftOvergangsbestammelse': data.get('ikraftOvergangsbestammelse'),
                            'ikraftDateTime': data.get('ikraftDateTime'),
                            'ikraftDenDagenRegeringenBestammer': data.get('ikraftDenDagenRegeringenBestammer')
                        })
                else:
                    stats['cases_ikraft_true_with_datetime'] += 1
                    if len(stats['examples_with_datetime']) < 5:
                        stats['examples_with_datetime'].append({
                            'file': json_file.name,
                            'beteckning': data.get('beteckning'),
                            'ikraftOvergangsbestammelse': data.get('ikraftOvergangsbestammelse'),
                            'ikraftDateTime': data.get('ikraftDateTime'),
                            'ikraftDenDagenRegeringenBestammer': data.get('ikraftDenDagenRegeringenBestammer')
                        })

            # Check andringsforfattningar
            if 'andringsforfattningar' in data:
                for andring in data['andringsforfattningar']:
                    if andring.get('ikraftOvergangsbestammelse'):
                        if andring.get('ikraftDateTime') is None:
                            stats['cases_ikraft_true_no_datetime'] += 1
                            if len(stats['examples_no_datetime']) < 10:
                                stats['examples_no_datetime'].append({
                                    'file': json_file.name,
                                    'beteckning': andring.get('beteckning'),
                                    'ikraftOvergangsbestammelse': andring.get('ikraftOvergangsbestammelse'),
                                    'ikraftDateTime': andring.get('ikraftDateTime'),
                                    'ikraftDenDagenRegeringenBestammer': andring.get('ikraftDenDagenRegeringenBestammer'),
                                    'type': 'andringsforfattning'
                                })
                        else:
                            stats['cases_ikraft_true_with_datetime'] += 1
                            if len(stats['examples_with_datetime']) < 10:
                                stats['examples_with_datetime'].append({
                                    'file': json_file.name,
                                    'beteckning': andring.get('beteckning'),
                                    'ikraftOvergangsbestammelse': andring.get('ikraftOvergangsbestammelse'),
                                    'ikraftDateTime': andring.get('ikraftDateTime'),
                                    'ikraftDenDagenRegeringenBestammer': andring.get('ikraftDenDagenRegeringenBestammer'),
                                    'type': 'andringsforfattning'
                                })

        except Exception as e:
            print(f"Error processing {json_file}: {e}")

    return stats


if __name__ == "__main__":
    json_dir = "../sfs-jsondata"

    print("Analyzing ikraftOvergangsbestammelse patterns...")
    stats = analyze_ikraft_overgangsbestammelse(json_dir)

    print(f"\nTotal JSON files analyzed: {stats['total_files']}")
    print(
        f"Files with ikraftOvergangsbestammelse=true in main doc: {stats['files_with_ikraft_true']}")
    print(f"\nCases where ikraftOvergangsbestammelse=true:")
    print(f"  - WITHOUT ikraftDateTime: {stats['cases_ikraft_true_no_datetime']}")
    print(f"  - WITH ikraftDateTime: {stats['cases_ikraft_true_with_datetime']}")

    print(f"\nExamples where ikraftOvergangsbestammelse=true WITHOUT ikraftDateTime:")
    for example in stats['examples_no_datetime']:
        print(f"\n  File: {example['file']}")
        print(f"  Beteckning: {example['beteckning']}")
        print(f"  ikraftOvergangsbestammelse: {example['ikraftOvergangsbestammelse']}")
        print(f"  ikraftDateTime: {example['ikraftDateTime']}")
        print(
            f"  ikraftDenDagenRegeringenBestammer: {example['ikraftDenDagenRegeringenBestammer']}")
        if 'type' in example:
            print(f"  Type: {example['type']}")

    print(f"\nExamples where ikraftOvergangsbestammelse=true WITH ikraftDateTime:")
    for example in stats['examples_with_datetime']:
        print(f"\n  File: {example['file']}")
        print(f"  Beteckning: {example['beteckning']}")
        print(f"  ikraftOvergangsbestammelse: {example['ikraftOvergangsbestammelse']}")
        print(f"  ikraftDateTime: {example['ikraftDateTime']}")
        print(
            f"  ikraftDenDagenRegeringenBestammer: {example['ikraftDenDagenRegeringenBestammer']}")
        if 'type' in example:
            print(f"  Type: {example['type']}")
