"""Preserve the new independent RF P1 and its exact frozen scope; no product writes."""
import hashlib
import json
from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
OUT = Path(__file__).resolve().parent
probes_path = OUT / 'original-and-independent-probes.json'
probes = json.loads(probes_path.read_text(encoding='utf-8'))
original_failure = OUT / 'original-point-stock-annual-fail.json'
if original_failure.exists():
    raise RuntimeError('refuse to overwrite original new-P1 evidence')
original_failure.write_bytes(probes_path.read_bytes())
code_paths = ['scripts/contracts/period_flow.py', 'scripts/contracts/annual_consumption.py',
              'scripts/contracts/document.py', 'scripts/contracts/recognition.py',
              'scripts/forecast/segments.py', 'compatibility/compatibility_manifest.py',
              'compatibility/contract_registry.py']
files = []
for path in code_paths:
    body = (ROOT / path).read_bytes()
    files.append({'path': path, 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)})
case = next(x for x in probes['cases'] if x['case'] == 'independent_point_stock_cannot_be_annual_revenue_alias')
assert case['actual'] == 'accepted' and case['strong_readers'] == 'PASS' and case['fy2026_low'] == 170.0
scratch = OUT / '_probe_scratch'
assert not scratch.exists()
(OUT / 'probe-cleanup.json').write_text(json.dumps({'scratch': str(scratch), 'initially_absent': True,
    'finally_absent': True, 'immutable_registry_cleanup': 'The registry intentionally sets a read-only attribute. Initial rmtree failed; path was verified inside the owned review directory, attribute cleared, and scratch removed with native PowerShell.',
    'provider_calls': 0, 'llm_calls': 0, 'fees_usd': 0}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
record = {
    'schema_version': 'w05-rf-flow-independent-final-review/1',
    'reviewer': '/root/w05_ocr_acceptance_review', 'author_of_product': False,
    'product_root': str(ROOT), 'root_head_declared': probes['root_head_declared'],
    'worker_delivery': probes['original_delivery'], 'frozen_key_files': files,
    'root_inventory_records_checked': len(probes['frozen_files']),
    'freeze_mismatches': [x['path'] for x in probes['frozen_files'] if not x['matches_frozen_inventory']],
    'verdict': 'FAIL_NEW_TYPED_ANCESTRY_P1',
    'findings': [{
        'id': 'W05-RF-INDEPENDENT-01', 'priority': 'P1', 'status': 'OPEN_AT_REVIEW_FREEZE',
        'title': 'An annual alias can launder point stock as recognized annual revenue',
        'cause': 'validate_windowed_composition returns for annual derived facts without period_flow ancestors; validate_annual_consumption trusts the outer annual basis. Typed monetary_balance point ancestry is never checked.',
        'actual': 'validate_document -> run_forecast -> validate_published_forecast -> validate_forecast_output accepts point monetary_balance 20 via annual revenue x0 alias, increases FY2026 low revenue from 150 to 170, and both strong readers PASS.',
        'expected': 'A pure relabeling of a point stock cannot establish recognized annual flow. Reject at the business contract, not due to registry write permissions.',
        'evidence': 'original-point-stock-annual-fail.json cases[5].input',
        'reproducer': 'probes.py stock_as_annual()',
        'control': 'The same stock alias labeled period_flow is correctly rejected with flow-bearing input diagnostic.',
        'repair_scope': 'Use unified typed ancestry for annual/datetime wrappers; do not blanket-reject native legitimate stock quantity times annual price/ARPU, stock-flow bridge models, or annual-only legacy drafts.',
    }],
    'independent_results': [
        {k: v for k, v in c.items() if k != 'input'} for c in probes['cases']
    ],
    'tested_scope': [
        'Original three P1 builders and expectations were replayed unchanged with only LEAF path rebound in memory; all three now receive real composition diagnostics.',
        'Original valid post-control bridge and negative disposal pass the actual run_forecast and strong readers.',
        'A zero-weight FY operand cannot manufacture full-year coverage.',
        'point stock -> period_flow rejects, point stock -> annual incorrectly accepts.',
        'All 29 ROOT frozen inventory byte sizes and SHA values match.',
    ],
    'unmeasured_scope': [
        'No repeat of 356-test daily suite or 52-test compatibility suite.',
        'H1/Q3 concatenation, additional annual-rate extrapolation and pure rate/scalar ancestry controls were not independently run before ROOT requested turn completion after the P1.',
        'Recognition shared-owner ordering and registry root split were read; their authored GREEN evidence was read but not reexecuted in this narrow turn.',
        'No independent CLI subprocess was completed in this turn; run_forecast formal publication and both strong readers were exercised with an explicit isolated registry.',
        'No source truth, actual business perimeter validity, all-company forecast economics or W04 quality verdict.',
    ],
    'environment_failure_preserved': {
        'file': 'first-unconfigured-registry-probes.json',
        'cause': 'First independent harness lacked explicit REVENUE_PUBLICATION_REGISTRY; formal publication attempted default external-tree artifacts and was denied by sandbox. No such failure is counted as a valid business rejection.',
        'resolution': 'Set publication registry to initially absent owned scratch and disable attestation provider for synthetic tests; original expectations untouched.',
    },
    'author_evidence_not_independently_repeated': {
        'daily_gate': '356 passed +36 subtests in 33.20s',
        'portable_compatibility': '52 passed +7 subtests in 3.90s',
        'explicit_real_three_repo_roots': '../fix/final-checkpoints.json',
        'report': '../fix/ROOT-fix-summary.md',
    },
    'scratch_restored': True, 'provider_calls': 0, 'llm_calls': 0, 'fees_usd': 0,
    'product_writes': 0, 'original_documents_touched': 0,
}
(OUT / 'final-review.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
md = '''# W05-RF-FLOW — independent final acceptance, first freeze

## Verdict

**FAIL_NEW_TYPED_ANCESTRY_P1. Do not accept this freeze yet.** The original three P1 counterexamples are fixed, but an independent typed stock alias still passes as annual recognized revenue. ROOT and the author were notified immediately; ROOT has assigned a systematic typed-ancestry repair.

The product root is `C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root`, HEAD declared `1b616622763ece6549676f2a74f596e6c65244af`, pending worker merge `f1a782a478d255b9b4b8f531e7a3961134e257ba`. All 29 ROOT inventory SHA/byte records match. Exact key-file SHA values are in `final-review.json`; period-flow SHA is `31ac27d37180c4a08f801745efe399ffc1281adad89b145f677fa5e94622841e`.

## New P1: point stock can bypass the annual wrapper

`validate_windowed_composition` skips an annual derived parameter with no `period_flow` ancestor; `validate_annual_consumption` accepts its annual label. A `point_in_time`, `monetary_balance` value 20 is passed through `derived_fact formula=x0` with outer `dimension=revenue` and `time_basis=annual`. The ordinary acquisition adjustment consumes it: `validate_document`, `run_forecast` and both strong readers all accept; FY2026 low revenue increases from 150 to **170**. No stock-to-flow model or annual pricing driver supports the conversion.

The exact complete input is preserved as `original-point-stock-annual-fail.json`, case `independent_point_stock_cannot_be_annual_revenue_alias` / `cases[5].input`. The constructor is `probes.py:stock_as_annual`. The corresponding dated wrapper is rejected correctly, proving the hole is the annual no-dated-ancestor trigger, not financial arithmetic.

The repair should validate typed ancestry through all relevant annual wrappers while preserving legitimate native stock quantity × annual price/ARPU and stock-flow model formulas. It must not become a blanket annual-only rejection, company-specific branch, rationale exemption or permission check.

## Independent executed results

The original three P1 builders and reject expectations were reused without edits: partial derived → annual, rationale moving a 2026 window to 2027, and H1 + own Q2 all now receive real composition errors. The original post-control bridge and small negative disposal pass formal forecasting and both readers. The nonzero/zero-weight coverage probe is correctly rejected. The dated stock alias rejects; the annual stock alias incorrectly passes. All eight exact inputs/results are retained.

The first harness omitted an explicit publication registry and encountered sandbox denial of the default external-tree artifacts path. That result remains in `first-unconfigured-registry-probes.json` and is not counted as a correct business rejection. The isolated rerun uses an owned registry, so the P1 truly reaches formal publication and strong readers. The immutable registry's read-only attribute initially prevented ordinary cleanup; the owned absolute scratch was checked, its temporary attribute cleared and the directory removed. `probe-cleanup.json` records absent → absent.

## Scope and remaining checks

Authored 356+36 daily and 52+7 portable compatibility GREEN evidence, recognition validation ordering and the explicit-root registry split were reviewed without rerunning the large suites. Additional H1/Q3, annual-rate extrapolation and rate/scalar controls have not been independently run; ROOT requested this turn stop after P1 evidence. No independent CLI subprocess was completed here. A final follow-up should replay the preserved P1 and selected legitimate typed-pricing controls after the author's freeze.

This is an engineering/temporal semantics verdict. It does not verify real source facts, group/subsidiary business inclusion, the validity of arbitrary scope text or buy-side forecast economic quality. No original, live provider, LLM, installed copy or product code was changed. Cost is zero.
'''
(OUT / 'final-review.md').write_text(md, encoding='utf-8')
entries = []
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name != 'manifest.json':
        body = path.read_bytes()
        entries.append({'path': path.name, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()})
(OUT / 'manifest.json').write_text(json.dumps({'schema_version': 'w05-independent-final-evidence/1', 'files': entries},
    ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'verdict': record['verdict'], 'report': str(OUT / 'final-review.md'),
                  'evidence_files': len(entries), 'scratch_restored': not scratch.exists()}))
