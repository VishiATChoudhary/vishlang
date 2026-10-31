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


def unwrap(user: str) -> str:
    """What a real model sees as the text to rewrite: strip the neutralise_user() wrapper."""
    if "<<<\n" in user and "\n>>>" in user:
        return user.split("<<<\n", 1)[1].rsplit("\n>>>", 1)[0]
    return user
