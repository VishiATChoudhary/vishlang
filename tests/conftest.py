import os
from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures"


def pytest_collection_modifyitems(config, items):
    if os.environ.get("VISHLANG_SLOW") == "1":
        return
    skip = pytest.mark.skip(reason="set VISHLANG_SLOW=1 to run tests that load the real model")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)
