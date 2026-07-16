"""Test fixtures that remain reliable on restricted Windows workspaces."""

from pathlib import Path
from uuid import uuid4

import pytest


@pytest.fixture
def tmp_path(request):
    """Create test directories without pytest's Windows-only 0o700 ACL issue."""
    root = Path.cwd() / "scratch" / "pytest-managed"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{request.node.name}-{uuid4().hex}"
    path.mkdir()
    return path
