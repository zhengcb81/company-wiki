# Host guard JSON pointer context handoff

## Scope and root cause

The guard flattened runtime string literals before classifying their role. The
actual source-coordinate values `record_pointer` and `field_pointer` therefore
looked like host paths when their JSON pointers started with a recognized root.

Only `scripts/host_assumption_guard.py` and its existing responsibility tests in
`tests/contract/test_fc1307_host_assumption_gate.py` changed. Source is stable and
ready for the root's normal commit. No commit was performed here.

## Classification

`_is_json_pointer_data_literal(node, parents)` accepts RFC 6901 literal syntax
(empty or slash-prefixed, with only `~0`/`~1` escapes) under exactly the dictionary
data keys `record_pointer` and `field_pointer`. Literal Add operands may reach
that dictionary value; any call, container or other AST parent stops exemption.
This covers the real field-pointer prefix concatenated with `str(index)`.

This is finite syntax classification, not runtime dataflow or pointer validation.
F-string expressions are not newly exempted. Real `Path(...)` and `open(...)`
arguments, arbitrary pointer/path keys, invalid tilde escapes, Windows paths,
standalone host literals, and unguarded capability calls stay detected. Existing
prefixes, baseline identities, fail-closed parse/read behavior and capability
skip detection did not change; no marker, license or gate was added.

## TDD and verification

- RED: 5 failed / 10 passed. The four legitimate coordinate cases were reported
  as host paths; the combined pointer + real Path + capability case exposed the
  extra false positive. Raw RED log is retained without alteration.
- GREEN: 42 passed / 1 deselected in 1.16 seconds. The deselected case scans the
  entire repository, owned by the root's combined normal hook run. All other
  existing guard responsibility tests ran, covering path roots, capability
  checks, exact baseline identity, malformed files and baseline diagnostics.
- Ruff: exit 0 for both owned files.
- Actual motivating `tests/unit/test_official_json_model_subject.py`: read-only
  `scan_file` returns no violations after classification.
- Baseline: `git diff HEAD --name-only -- tests/contract/host_assumption_baseline.json`
  is empty. No baseline or archived evidence bytes were edited.
- Zero provider/model calls. Owned TEMP and pytest's relocated TEMP were removed.

## Evidence

`host-pointer-red.log/json`, `host-pointer-green.log/json`,
`host-pointer-ruff.log`, and `host-pointer-handoff.json` reside in this new evidence
directory. No full suite or external vendor calls were made.
