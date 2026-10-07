"""G3-SOURCE-FACTS read-only proposal helpers.

This package never writes to the production catalog, never edits originals and
exposes no apply / delete / update surface: it only turns observed evidence
into JSON/Markdown proposals for the MAIN lane to review.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "g3-source-facts/1"
