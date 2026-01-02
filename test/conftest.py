"""
Shared pytest fixtures and configuration for sfs-processor tests.
"""
import pytest
from pathlib import Path


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def test_data_dir(project_root):
    """Return the test data directory."""
    return project_root / "test" / "data"


@pytest.fixture
def sample_temporal_title():
    """Sample temporal title with date markers for testing."""
    return """/Rubriken upphör att gälla U:2025-07-15/
Förordning (2023:30) om statsbidrag till regioner för åtgärder för att höja driftsäkerheten på hälso- och sjukvårdens fastigheter
/Rubriken träder i kraft I:2025-07-15/
Förordning om statsbidrag till regioner för åtgärder för att höja driftsäkerheten på fastigheter för hälso- och sjukvård"""


@pytest.fixture
def sample_sfs_document():
    """Sample SFS document data for testing."""
    return {
        'beteckning': '2023:30',
        'rubrik': """/Rubriken upphör att gälla U:2025-07-15/
Förordning (2023:30) om statsbidrag till regioner för åtgärder för att höja driftsäkerheten på hälso- och sjukvårdens fastigheter
/Rubriken träder i kraft I:2025-07-15/
Förordning om statsbidrag till regioner för åtgärder för att höja driftsäkerheten på fastigheter för hälso- och sjukvård""",
        'fulltext': {
            'innehall': 'Test innehåll här...'
        }
    }


@pytest.fixture
def mock_riksdagen_responses(requests_mock):
    """
    Mock common Riksdagen API responses.
    Can be customized per test by accessing the requests_mock fixture.
    """
    # Mock successful proposition (prop 2024/25:1 -> HB031)
    requests_mock.get(
        'https://data.riksdagen.se/dokument/HB031.json',
        json={
            'dokumentstatus': {
                'dokument': {
                    'dokumentnamn': 'Prop. 2024/25:1',
                    'titel': 'Budgetpropositionen för 2025',
                    'rm': '2024/25',
                    'beteckning': '1',
                    'typ': 'prop',
                    'dokument_url_html': 'https://data.riksdagen.se/dokument/HB031.html'
                }
            }
        }
    )

    # Mock successful proposition (prop 2023/24:144 -> HA03144)
    requests_mock.get(
        'https://data.riksdagen.se/dokument/HA03144.json',
        json={
            'dokumentstatus': {
                'dokument': {
                    'dokumentnamn': 'Prop. 2023/24:144',
                    'titel': 'Test proposition',
                    'rm': '2023/24',
                    'beteckning': '144',
                    'typ': 'prop',
                    'dokument_url_html': 'https://data.riksdagen.se/dokument/HA03144.html'
                }
            }
        }
    )

    # Mock successful bet (committee report) (bet 2023/24:JuU3 -> HA01JuU3)
    requests_mock.get(
        'https://data.riksdagen.se/dokument/HA01JuU3.json',
        json={
            'dokumentstatus': {
                'dokument': {
                    'dokumentnamn': 'Bet. 2023/24:JuU3',
                    'titel': 'Justitieutskottets betänkande',
                    'rm': '2023/24',
                    'beteckning': 'JuU3',
                    'typ': 'bet',
                    'dokument_url_html': 'https://data.riksdagen.se/dokument/HA01JuU3.html'
                }
            }
        }
    )

    # Mock riksdagsskrivelse (rskr 2023/24:9 -> HA049)
    requests_mock.get(
        'https://data.riksdagen.se/dokument/HA049.json',
        json={
            'dokumentstatus': {
                'dokument': {
                    'dokumentnamn': 'Rskr. 2023/24:9',
                    'titel': 'Riksdagens skrivelse',
                    'rm': '2023/24',
                    'beteckning': '9',
                    'typ': 'rskr',
                    'dokument_url_html': 'https://data.riksdagen.se/dokument/HA049.html'
                }
            }
        }
    )

    return requests_mock


@pytest.fixture
def mock_riksdagen_404(requests_mock):
    """Mock a 404 response from Riksdagen API."""
    requests_mock.get(
        'https://data.riksdagen.se/dokument/G60340.json',
        status_code=404
    )
    return requests_mock
