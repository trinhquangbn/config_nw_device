import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture
def sample_device_spec():
    return {
        "name": "R1-TEST",
        "host": "192.0.2.10",
        "username": "admin",
        "password": "secret",
        "device_type": "cisco_ios",
        "group": "core",
        "tags": ["core"],
    }
