#!/usr/bin/env python3
"""
Test script for law name linking functionality.
"""

from formatters.apply_links import apply_law_name_links
import os

def test_linking():
    """Test the linking functionality with examples from the report."""
    
    test_cases = [
        '3 kap. 3 § dataskyddslagen',
        '8 kap. 7 § regeringsformen', 
        '2 kap. 25 § skollagen',
        '29 kap. 14 § och offentlighets- och sekretesslagen',
        '15 kap. 2 § sekretesslagen'
    ]

    print('Testar länkfunktionalitet efter fix:')
    print('=' * 60)
    print()

    for test_case in test_cases:
        result = apply_law_name_links(test_case)
        if result != test_case:
            print(f'✅ LÄNKAD: {test_case}')
            print(f'   Resultat: {result}')
        else:
            print(f'❌ EJ LÄNKAD: {test_case}')
        print()

if __name__ == "__main__":
    test_linking()