"""Shared pytest fixtures for the P3 identity-audit lane.

Every fixture is synthetic and lives under ``tmp_path``; the production config,
production catalog and real originals are never opened.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fixtures import sidecar_catalog
from fixtures.sidecar_catalog import Fixture


@pytest.fixture
def build(tmp_path: Path):
    """Build (and always close) synthetic sidecar catalogs under tmp_path."""

    built: list[Fixture] = []
    counter = {"n": 0}

    def _build(**kwargs) -> Fixture:
        counter["n"] += 1
        root = tmp_path / f"fixture-{counter['n']}"
        fixture = sidecar_catalog.build_fixture(root, **kwargs)
        built.append(fixture)
        return fixture

    try:
        yield _build
    finally:
        for fixture in built:
            fixture.close()


@pytest.fixture
def plain(build) -> Fixture:
    """One indexed ``text/plain`` source with a real unit-marked original."""
    return build()


@pytest.fixture
def captured(build) -> Fixture:
    """Same source, plus the capture provenance that proves availability."""
    return build(capture=True)


@pytest.fixture
def unmarked(build) -> Fixture:
    """A ``text/plain`` source whose original carries no unit token at all."""
    return build(body=sidecar_catalog.PLAIN_BODY)
