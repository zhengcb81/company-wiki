"""One causal connective observation for policy and source-quote consumers.

The connective establishes grammar only. Each consumer still owns the meaning
of its arguments; a financial or accounting cause is not an operating proof.
"""
from __future__ import annotations

import re


CAUSAL_LINK = re.compile(
    r"\b(?:driven by|due to|reflecting|because)\b|主要由|主要原因(?:是|为)|"
    r"由于|因为|受(?P<embedded_cause>.{0,12})带动|得益于", re.I)
