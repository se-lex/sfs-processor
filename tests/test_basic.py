"""
Test för SFS processor funktionalitet.
"""

import json
from pathlib import Path


def test_sample_sfs_data_structure(sample_sfs_data):
    """Test att exempel SFS-data har rätt struktur."""
    assert "beteckning" in sample_sfs_data
    assert "rubrik" in sample_sfs_data
    assert sample_sfs_data["beteckning"] == "2025:123"


def test_temp_directory_creation(temp_dir):
    """Test att temporära kataloger skapas korrekt."""
    assert temp_dir.exists()
    assert temp_dir.is_dir()
    
    # Skapa en testfil
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")
    
    assert test_file.exists()
    assert test_file.read_text() == "test content"


def test_json_processing_example(sample_sfs_data, temp_dir):
    """Test av JSON-bearbetning med exempel data."""
    # Spara som JSON
    json_file = temp_dir / "test_sfs.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(sample_sfs_data, f, ensure_ascii=False, indent=2)
    
    # Läs tillbaka
    with open(json_file, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
    
    assert loaded_data == sample_sfs_data
    assert loaded_data["beteckning"] == "2025:123"
