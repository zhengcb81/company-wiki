"""DU-BENCH: an independent document-understanding quality benchmark.

Public entry point (INTERFACES.md §5)::

    from tools.document_understanding_benchmark import evaluate
    result = evaluate(observed, gold)

CLI (see README.md)::

    python -m tools.document_understanding_benchmark --mode offline|native \
        --bindings <json> --output <owned-dir>

The package is standalone: it does not import ``company_wiki``. Native mode
observes the existing public parser/selector through a thin injected observer
instead of reimplementing selection.
"""

from __future__ import annotations

from .evaluate import evaluate

__all__ = ["evaluate"]
