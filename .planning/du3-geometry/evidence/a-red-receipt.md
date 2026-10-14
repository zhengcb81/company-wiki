"""DU3-GEOMETRY node A: RED receipt (captured before implementation existed).

Command:
  python -B -X utf8 -m pytest tests/unit/document_normalization_layout_snapshots -q

Result (RED, before ``layout_snapshots`` package was written):
  tests/unit/document_normalization_layout_snapshots/test_a_unit_binding.py:14:
    from company_wiki.document_normalization.layout_snapshots import project_layout_snapshot
  E   ModuleNotFoundError: No module named 'company_wiki.document_normalization.layout_snapshots'
  ERROR tests/unit/document_normalization_layout_snapshots/test_a_snapshot_contract.py
  ERROR tests/unit/document_normalization_layout_snapshots/test_a_unit_binding.py
  Interrupted: 2 errors during collection

Both node-A modules (snapshot_contract + unit_binding) fail at import against the
absent module: the required counterexample set is written and RED first, as the
card demands.  GREEN evidence is recorded in the handoff.
"""
