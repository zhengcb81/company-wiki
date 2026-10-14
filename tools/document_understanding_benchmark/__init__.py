"""DU-BENCH: an independent document-understanding quality benchmark.

Public entry points (INTERFACES.md §5)::

    from tools.document_understanding_benchmark import evaluate
    result = evaluate(observed, gold)

    from tools.document_understanding_benchmark import observe_final_material
    observed = observe_final_material(material, originals, sample_id=..., execution=...)

    from tools.document_understanding_benchmark import compare_runs
    comparison = compare_runs(baseline, candidate, frozen_suite=...)

CLI (see README.md)::

    python -m tools.document_understanding_benchmark --mode offline|native \
        --bindings <json> --output <owned-dir>

The package is standalone: it does not import ``company_wiki``. Native mode
observes the existing public parser/selector through a thin injected observer
instead of reimplementing selection.
"""

from __future__ import annotations

from .comparison import compare_runs
from .evaluate import evaluate
from .final_material import observe_final_material

__all__ = ["compare_runs", "evaluate", "observe_final_material"]
