"""Pytest fixtures for the document-normalization lane."""

import pytest

from support.document_normalization_fixtures import tiny_png


@pytest.fixture
def png_bytes() -> bytes:
    return tiny_png()
