"""W18-CWP-HOLDOUT replay tooling (thin orchestration over DU-BENCH).

This package freezes a three-market source manifest and source-side gold,
replays an explicit frozen producer commit against it, and records honest
per-target observations. It adds no second gold, scoring, recovery or cleanup
framework: those come from ``tools.document_understanding_benchmark``.
"""
