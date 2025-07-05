"""
Test configuration for pytest.
"""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Skapa en temporär katalog för tester."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_sfs_data():
    """Exempel på SFS-data för tester."""
    return {
        "beteckning": "2025:123",
        "rubrik": "Testlag",
        "organisation": {"namn": "Regeringskansliet"},
        "fulltext": {
            "text": "Test innehåll",
            "utfardadDateTime": "2025-01-01T00:00:00",
        },
        "ikraftDateTime": "2025-06-01T00:00:00",
    }
