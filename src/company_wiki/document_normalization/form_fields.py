"""Literal inline form controls, shared by native heading inference owners."""
from __future__ import annotations

import re

_INLINE_APPLICABILITY = re.compile(r"[□☐☑√✓✔]\s*[适適]用\s*[□☐☑√✓✔]\s*不[适適]用")


def has_inline_form_response(text: str) -> bool:
    """A source response is not heading evidence just because it is numbered."""
    return _INLINE_APPLICABILITY.search(text) is not None
