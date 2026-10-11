from __future__ import annotations
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
EVIDENCE = Path(__file__).resolve().parent
FROZEN = ROOT / 'docs/handoffs/w05-rf-flow/e2e/frozen'
path = ROOT / 'scripts/generate_input_template.py'
body = path.read_text(encoding='utf-8')
old = '''                "year only through explicit derived sums, with a rationale when "
                "windows overlap or a pre-control gap stays out of scope."'''
new = '''                "year only through actual input windows and their derived lineage. "
                "Rationale may explain independent scopes, a residual subtraction or "
                "a real pre-control perimeter gap; it never moves known dates or "
                "adds the same economic flow twice. Stock/rate alone is not revenue."'''
assert old in body
path.write_text(body.replace(old, new), encoding='utf-8')
manifest_path = FROZEN / 'manifest.json'
shutil.copyfile(manifest_path, EVIDENCE / 'frozen-manifest-before-template-doc-fix.json')
scratch = EVIDENCE / 'template-doc-scratch'
assert not scratch.exists()
scratch.mkdir()
env = os.environ.copy()
env['PYTHONDONTWRITEBYTECODE'] = '1'
env['PYTHONUTF8'] = '1'
arguments = [sys.executable, '-B', 'scripts/generate_input_template.py', '--name', 'FixtureCo Template (synthetic)',
             '--base-year', '2025', '--forecast-years', '2026', '2027', '--segments', 'Segment A',
             '--schema', '3.10', '--currency', 'CNY', '--output', str(scratch / 'template-3.10.json')]
try:
    result = subprocess.run(arguments, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', timeout=15, check=True)
    target = FROZEN / 'template-3.10.json'
    shutil.copyfile(scratch / target.name, target)
    data = json.loads(target.read_text(encoding='utf-8'))
    assert 'never moves known dates' in data['_comment'] and 'same economic flow twice' in data['_comment']
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for item in manifest['artifacts']:
        if item['path'].endswith('/template-3.10.json'):
            item['bytes'] = target.stat().st_size
            item['sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest['total_bytes'] = sum(item['bytes'] for item in manifest['artifacts'])
    manifest['template_doc_followup'] = 'metadata-only correction after final engineering node; native generator PASS, original manifest preserved in ROOT fix evidence'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
finally:
    assert scratch.resolve().parent == EVIDENCE.resolve() and scratch.name == 'template-doc-scratch'
    shutil.rmtree(scratch)
(EVIDENCE / 'template-doc-checkpoint.json').write_text(json.dumps({
    'command': arguments, 'exit_code': result.returncode, 'stdout': result.stdout,
    'scratch_initial_exists': False, 'scratch_final_exists': scratch.exists(),
    'frozen_template_sha256': hashlib.sha256((FROZEN / 'template-3.10.json').read_bytes()).hexdigest(),
    'scope': 'generated author guidance only; business engine/test assertions unchanged',
    'provider_calls': 0, 'llm_calls': 0, 'fees_usd': 0}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

report = '''# ROOT reception hardening — W05-RF-FLOW

## Status and provenance

Original delivery is `7b22bca8d6aa87f643780100832daec2836ed558` +
`f1a782a478d255b9b4b8f531e7a3961134e257ba`, based on
`1b616622763ece6549676f2a74f596e6c65244af`. The original handoff, manifest and
logs remain a historical worker receipt. This document and `e2e/frozen/manifest.json`
describe ROOT fixes; old handoff file hashes do not certify modified files.
ROOT performs final independent acceptance, merge/commit/push and installation.

## Common roots fixed

1. A derived annual alias previously hid a partial dated flow. The common temporal
   composition rule now applies to dated derived flows **and** annual wrappers
   with dated ancestry, across actual nonzero formula inputs.
2. Any rationale previously bypassed containment and overlap. Explanation now
   describes a real scope gap/independent business scope/residual subtraction;
   it cannot move a 2026 input into 2027 or add H1 and its own Q2.
3. Dated aliases preserve original leaf identity and semantic definition, so
   renaming an output/intermediate definition does not launder double counting.
   Unused/zero-weight operands do not manufacture year coverage. A point stock or
   rate alone cannot establish a recognized flow.
4. The old mixed-recognition lagged-activity input reached a dependency walker
   before shape validation and raised KeyError. One shared recognition validator
   now checks supplied metadata before DAG indexing; no carry-in defaults are
   fabricated. Legacy omitted-recognition draft structural validation is unchanged;
   actual forecast execution still requires a recognition contract.
5. The C1 sealed 1,291,902.08 CNY is retained as 1.29190208 CNY million in an
   entirely CNY synthetic surrounding fixture. No USD relabeling or assumed FX.
6. Compatibility unit tests no longer infer physical sibling repositories. Pure
   manifest/hash validation is separate from explicit read-only Git/document
   integration; nine tiny temporary Git commits test actual descendant/regression.

## Interfaces and responsibility

- `validate_period_flow_fields(..., schema_version="3.9")` keeps its old call shape
  and strict 3/6/12-month 3.9 semantics; only 3.10 admits arbitrary inclusive dates.
- `validate_windowed_composition` keeps the original public signature. Its formula
  lineage follows additive/subtractive sums and scalar/rate/price factors. Products
  of two flow amounts, division by a flow and non-unit-preserving powers are not
  temporal compositions; use the existing explicit assumption/native model fields.
- Original source economic identity/definition/perimeter is the authored evidence
  layer's responsibility. Hashes/string definitions cannot prove real subsidiary
  membership or detect a self-consistent rewrite of all reported facts. Independent
  economic/source audit remains necessary; no review receipt/permission is added.
- `contracts.recognition.validate_recognition_metadata` owns recognition shape;
  `forecast.segments` reexports the old entry for compatibility.
- `compatibility_manifest.validate_manifest(data)` is a pure registry/manifest
  check. Real integration explicitly calls `validate_repository_ancestry(data,
  repo_dirs)` after structural validation. `contract_registry.validate_canonical_documents`
  receives explicit repository roots. Neither unit tests nor production infer the
  current user's Projects directory.

## Engineering acceptance performed

- Formal ROOT RED: 3 real temporal exploits + preexisting mixed KeyError failed;
  the unrelated zero-weight guard already rejected and is not claimed as RED.
- Separate stock RED: a point monetary balance relabeled as revenue was accepted
  before the common typed precondition; original negative assertion retained.
- First final node exposed 2 legacy draft regressions; FAIL logs retained and the
  validator responsibility corrected. Tests were not loosened.
- Final existing `tools/pre_push_gate.py`: ruff PASS, public mypy 11 files PASS,
  **356 tests + 36 subtests PASS**, pytest 33.20s / full entry 38.043s.
- Portable compatibility plus 3.9 field/engine semantics: **52 tests + 7 subtests
  PASS**, pytest 3.90s. Counts overlap some daily tests; do not sum as unique tests.
- Native 3.10 template, two validation/forecast/Markdown chains, immutable snapshot,
  native strong readers, rehashed window/currency tamper rejection and full forecast
  JSON determinism PASS. Actual cross-repo ancestry and canonical docs checked with
  explicit read-only roots. No provider/LLM calls, no fees.
- Generated author guidance was clarified after the engine node; one bounded native
  template regeneration checked its wording. Business code/assertions unchanged.

The existing SMOKE_TESTS list includes the three dated contribution suites, ROOT
temporal lineage and old mixed recognition tests. No new gate script or per-commit
wide suite was created. These proofs are **offline engineering**, not real-company
economic quality or paid-provider acceptance.

## Frozen replay and test isolation

Eight small JSON/Markdown artifacts live under `e2e/frozen/`, not ignored global
`artifacts/`. Verify each byte SHA/size against its manifest. C1 preserves only the
sealed amount/unit/dates; its surrounding facts, sources and forecasts are synthetic.
C2 is a synthetic 06-30 fiscal-year partition `7+10+3=20` and a ten-day observation.
No binary raw original was copied.

To replay with this engine, create your own temporary directory and set
`REVENUE_PUBLICATION_REGISTRY` to a file in it. Run the native forecast CLI on each
frozen input, with JSON/Markdown outputs in that temporary directory. Compare full
forecast JSON with the frozen result, then use `e2e/read_and_tamper.py` on the new
output (`window`, and C1 `currency`). For C1 snapshot use native
`revenue_backtest.py create ... --version w05-root-cny-v1 --output <tmp snapshot>`
and `validate_snapshot`. Do not overwrite frozen files, production registries or
raw/config/install files. Restore only your owned test directory afterward.
The generated template is a FIXME skeleton, not a runnable real-company forecast.

ROOT external evidence includes exact command logs, checkpoints, failed rounds,
scratch initial/final state and the final file SHA inventory. The owned E2E scratch
and template documentation scratch started absent and ended absent. The ROOT
worktree is intentionally retained for independent review until ROOT commits it.
'''
(ROOT / 'docs/handoffs/w05-rf-flow/ROOT-reception.md').write_text(report, encoding='utf-8')
print('Wrote ROOT receipt and clarified regenerated template; no commit or installation')
