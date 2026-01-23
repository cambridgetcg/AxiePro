"""
Unit test fixtures.

Unit tests should be fast and have no external dependencies.
All I/O should be mocked.
"""

import pytest


# Mark all tests in this directory as unit tests
def pytest_collection_modifyitems(items):
    """Automatically mark all tests in unit/ as unit tests."""
    for item in items:
        if "/unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)


@pytest.fixture
def sample_gene_string():
    """Sample 256-bit gene string for Beast Axie."""
    return "0x0000000000000001000308a042080004200100a04208000c200100a0420c0010"


@pytest.fixture
def sample_axie_data():
    """Sample Axie data for unit tests."""
    return {
        "id": "12345",
        "class": "Beast",
        "breedCount": 0,
        "genes": "0x0000000000000001000308a042080004200100a04208000c200100a0420c0010",
        "stats": {
            "hp": 43,
            "speed": 35,
            "skill": 31,
            "morale": 43,
        },
        "parts": [
            {"id": "back-ronin", "name": "Ronin", "class": "Beast", "type": "back"},
            {"id": "ears-zen", "name": "Zen", "class": "Beast", "type": "ears"},
            {"id": "eyes-chubby", "name": "Chubby", "class": "Beast", "type": "eyes"},
            {"id": "horn-imp", "name": "Imp", "class": "Beast", "type": "horn"},
            {"id": "mouth-nut-cracker", "name": "Nut Cracker", "class": "Beast", "type": "mouth"},
            {"id": "tail-nut-cracker", "name": "Nut Cracker", "class": "Beast", "type": "tail"},
        ],
    }
