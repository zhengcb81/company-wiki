"""Freeze an independent review record without editing product or shared planning."""
import hashlib
import json
from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures-root')
OUT = Path(__file__).resolve().parent
paths = [
    'skills/revenue-forecast-audit/scripts/financial_measure_audit.py',
    'skills/revenue-forecast-audit/references/financial-measure-audit.md',
    'skills/revenue-forecast-audit/SKILL.md',
    'skills/revenue-forecast-audit/references/review-process.md',
    'skills/revenue-forecast-audit/references/review-analyst.md',
    'tests/test_financial_measure_root_regressions.py',
    'tests/test_financial_measure_typed_contract.py',
    'tests/test_financial_measure_report_boundary.py',
]
files = [{'path': p, 'sha256': hashlib.sha256((ROOT / p).read_bytes()).hexdigest(),
          'bytes': len((ROOT / p).read_bytes())} for p in paths]
probes = json.loads((OUT / 'final-counterexamples.json').read_text(encoding='utf-8'))
cli = json.loads((OUT / 'cli-structured-invalid.json').read_text(encoding='utf-8'))
cleanup = json.loads((OUT / 'cleanup.json').read_text(encoding='utf-8'))
issue = {
    'id': 'W06-INDEPENDENT-01', 'priority': 'P2', 'status': 'open_at_review_freeze',
    'file': 'skills/revenue-forecast-audit/scripts/financial_measure_audit.py', 'line': 587,
    'title': 'Invalid top-level report omits source_qualification_verified',
    'cause': '_empty_report does not use the same nonattestation fields as the normal report factory.',
    'impact': 'Malformed-but-valid JSON is diagnosed without crashing and cannot return PASS; its report shape differs from the documented schema and a strict consumer can raise KeyError.',
    'reproductions': ['independent_nonobject_ledger_report_contract',
                      'independent_observations_object_report_contract',
                      'cli-structured-invalid.json'],
    'fix': 'Include source_qualification_verified:false in _empty_report; retain original failure evidence and do one focused schema verification. No additional permission or identity check is needed.',
}
record = {
    'schema_version': 'w06-independent-final-review/1',
    'reviewer': '/root/w05_ocr_acceptance_review', 'author_of_product': False,
    'product_root': str(ROOT), 'frozen_files': files,
    'review_decision': 'ACCEPT_TYPED_MATH_WITH_P2_REPORT_SCHEMA_FIX',
    'engineering_status': 'PASS_WITH_ONE_P2_OUTPUT_CONTRACT_OMISSION',
    'p1_findings': [], 'findings': [issue],
    'independent_checks': {
        'unchanged_original_vectors': 19, 'independent_additional_vectors': 8,
        'expected_arithmetic_statuses_passed': sum(x['passes_expectation'] for x in probes['cases']),
        'unexpected_statuses_or_exceptions': [x['id'] for x in probes['cases'] if not x['passes_expectation']],
        'output_contract_failures': [x['id'] for x in probes['cases'] if not x['required_nonattestation_fields_present']],
        'cli': {'exit_code': cli['exit_code'], 'structured_invalid_report': cli['structured_invalid_report'],
                'nonattestation_field_omission_reproduced': not cli['required_nonattestation_fields_present']},
        'scratch_restored': cleanup['initially_absent'] and cleanup['finally_absent'],
    },
    'static_review': {
        'typed_input_and_output_context': 'Checked entity/definition/kind/currency/scale/time/arity and dependency validity propagation.',
        'period': 'Growth/CAGR preserve output anchor, require ordered comparable periods; temporal sums cannot silently concatenate overlaps/gaps.',
        'roles': 'Future guidance and explicit assumptions are legal; reported future facts and more-factual result promotions remain UNRESOLVED.',
        'unknown_provenance': 'Missing required fact source_ref remains UNRESOLVED. Optional unknown available_by is diagnostic-only; source qualification is never attested.',
        'precision': 'Decimal arithmetic; boolean rounding rejected, positive tolerance bounded by explicit display precision and actual expected magnitude, tiny values have no one-unit epsilon floor.',
        'shape_schema': 'Bad arity/schema/as-of/shape are structured non-PASS reports. The P2 finding affects a nonattestation field only, not overall status.',
        'scope': 'Explicitly scoped cross-entity market share is allowed; no identity reconstruction or permit chain added.',
        'root_skill_wiring': 'SKILL.md, review-process.md and review-analyst.md make the tool supplemental and preserve four independent source/process/model reviews.',
    },
    'author_test_evidence_read_not_independently_repeated': {
        'focused': '76 PASS', 'full_suite': '296 PASS in 75.047s',
        'numeric_unchanged': '7 PASS', 'cli_e2e': 'CN/HK/US synthetic ledgers, mutations, immutable attempts and cleanup',
        'report': '../fix/repair-report.json',
    },
    'scope_limits': [
        'PASS is declared arithmetic and typed-context consistency only. Source truth, source qualification, complete company numerical coverage, buy-side model quality and W04 economic reasonableness are not signed off.',
        'source_ref, FX source, scope_inclusion, definition and display-precision basis are declared strings; reviewers must read actual evidence and validate their meanings.',
        'Optional unavailable available_by does not block the math tool; the four-review workflow remains responsible for actual publication availability and as-of qualification.',
        'The sum operation checks contiguous flow periods, not parallel business segments. Unequal 52/53-week comparability is not inferred.',
        'No live providers, real-document content, LLM or paid resources were called in this independent review.',
    ],
    'provider_calls': 0, 'llm_calls': 0, 'charged_cost_usd': '0',
    'original_intake_failures_preserved': True,
}
boundary = json.loads((OUT / 'report-boundary-verification.json').read_text(encoding='utf-8'))
assert boundary['pass'] and boundary['frozen_product_sha256'] == files[0]['sha256']
source_bytes = (ROOT / paths[0]).read_bytes()
prefix, empty_factory = source_bytes.split(b'def _empty_report(as_of):', 1)
assert empty_factory.count(b', "source_qualification_verified": False') == 1
pre_fix_bytes = prefix + b'def _empty_report(as_of):' + empty_factory.replace(b', "source_qualification_verified": False', b'', 1)
pre_fix_reconstructed_sha = hashlib.sha256(pre_fix_bytes).hexdigest()
assert pre_fix_reconstructed_sha == probes['product_sha256']
record['review_decision'] = 'ACCEPT_WITH_SCOPED_LIMITS'
record['engineering_status'] = 'PASS_INDEPENDENT_FOCUSED_ACCEPTANCE'
record['findings'][0]['status'] = 'CLOSED_AND_INDEPENDENTLY_VERIFIED'
record['findings'][0]['resolution'] = 'ROOT added source_qualification_verified:false to _empty_report; three pure checks and one real CLI check verify the final frozen product. Prior failure evidence is preserved.'
record['independent_checks']['pre_schema_fix_product_sha256'] = probes['product_sha256']
record['independent_checks']['pre_schema_fix_output_contract_failures_preserved'] = record['independent_checks'].pop('output_contract_failures')
record['independent_checks']['final_schema_fix'] = {'pure_core_checks': 3, 'real_cli_checks': 1,
    'pass': boundary['pass'], 'evidence': 'report-boundary-verification.json',
    'scratch_restored': boundary['scratch_finally_absent'],
    'final_delta_only_empty_factory_nonattestation_field': True,
    'reconstructed_pre_fix_sha256': pre_fix_reconstructed_sha}
record['author_test_evidence_read_not_independently_repeated']['root_report_boundary'] = 'One test with seven subcases; original six schema omissions RED and normal control PASS, final all financial 77 PASS; ROOT did not repeat 296.'
record['author_test_evidence_read_not_independently_repeated']['root_report_boundary_logs'] = ['../fix/report-boundary-red.log', '../fix/report-boundary-green.log']
(OUT / 'final-review.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
text = '''# W06-AUDIT-MEASURES — independent ROOT acceptance review

## Conclusion

**Accept the declared typed-math repair, with one P2 report-schema correction before final packaging.** No P1 defect was found in this review. Source truth, source qualification, company-wide coverage and forecast research quality are outside this verdict.

Reviewed product SHA: `294af2a66f30334cd332b5e8e7210adb4d8793bf38959f2d902ee8db1474d808`. The exact seven product/test/wiring hashes are in `final-review.json`.

## Evidence

- The original 19 intake vectors were replayed without changing their ledgers or expected statuses: all 19 now satisfy the frozen expectations; no exception occurred.
- Eight additional probes check legal cross-entity market share, missing factual source, future assumptions, invalid source shape, boolean rounding, unavailable-at-as-of evidence and top-level invalid shapes: all eight have the expected arithmetic status.
- A real CLI invocation using malformed-but-valid JSON returns exit 2 and writes an immutable `INVALID` report; it does not crash the batch. Its owned scratch directory was absent before and after the invocation.
- Two pure-core invalid-shape outputs and that CLI report reproduce the P2 omission below. These original reports are retained in `final-counterexamples.json` and `cli-structured-invalid.json`.
- Author evidence was read: 76 focused / 296 complete tests passed, unchanged numeric tests and synthetic CN/HK/US CLI/E2E checks passed. This review did not repeat the complete suite.

## P2 — inconsistent nonattestation field on invalid top-level inputs

`financial_measure_audit.py:587` uses `_empty_report` without `source_qualification_verified:false`, while normal reports and the documented contract include it. Inputs `[]` and `{observations:{}, relations:[]}` remain correctly `INVALID`, but their report shape differs and a strict downstream consumer could fail with `KeyError`. Add the same field to the empty-report factory and verify these two cases once. This correction does not introduce a permission, identity check or review gate.

## Architecture and semantics reviewed

Input and result entity/definition/kind/currency/scale/time compatibility, invalid dependencies, fixed arity, comparable periods, actual versus future roles, schema and as-of handling were checked. Decimal comparisons reject unbounded tolerances and coerced boolean precision. Legal cross-entity market share works with explicit scope. Unknown required factual provenance remains `UNRESOLVED`; optional unknown publication availability is a diagnostic, with source qualification always unverified.

ROOT's three wiring files (`SKILL.md`, `review-process.md`, `review-analyst.md`) explicitly keep the numeric tool supplementary to the four independent reviews. A tool `PASS` does not satisfy source reading, company-wide exhaustive coverage or the analyst's causal model and reasonableness assessment.

## Practical limits

Declared source IDs, scope, definitions, FX sources and display-precision descriptions are not verified against actual source bytes by this pure tool. Parallel segment sums and unequal 52/53-week comparability are not silently inferred. No provider, LLM, production document or paid resource was touched. This report signs no W04 economic quality or real-company research result.
'''
text = text.replace('**Accept the declared typed-math repair, with one P2 report-schema correction before final packaging.**',
                    '**Accept the repaired typed-math tool within its declared scope.** The one P2 report-schema omission found during this review has been fixed and independently verified.')
text = text.replace('`294af2a66f30334cd332b5e8e7210adb4d8793bf38959f2d902ee8db1474d808`. The exact seven product/test/wiring hashes',
                    '`' + files[0]['sha256'] + '`. The exact eight product/test/wiring hashes')
text = text.replace('## P2 — inconsistent nonattestation field on invalid top-level inputs',
                    '## Closed P2 — inconsistent nonattestation field on invalid top-level inputs')
text = text.replace('Add the same field to the empty-report factory and verify these two cases once. This correction does not introduce a permission, identity check or review gate.',
    'ROOT added the missing field to the empty-report factory. Independent final verification checks the two invalid pure-core shapes, a normal control, and an actual CLI invalid-shape report against the new SHA: all four PASS. ROOT retains its RED log and 77-test financial GREEN log; this review did not repeat the earlier 19/8 vectors or complete suite after the one-field change. The original reports remain unchanged. This correction introduces no permission, identity check or review gate.')
text += '\n## Final freeze verification\n\n`report-boundary-verification.json` records the final SHA, three pure checks and one CLI check; all PASS with scratch absent again. Earlier 19/8 results were run at SHA `294af2a66f30334cd332b5e8e7210adb4d8793bf38959f2d902ee8db1474d808`; the final delta adds only the previously omitted boolean field. `review-before-schema-fix.md/json` preserve the independent original finding.\n'
(OUT / 'final-review.md').write_text(text, encoding='utf-8')
entries = []
for p in sorted(OUT.iterdir()):
    if p.is_file() and p.name != 'manifest.json':
        data = p.read_bytes()
        entries.append({'path': p.name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
(OUT / 'manifest.json').write_text(json.dumps({'schema_version': 'w06-independent-evidence-manifest/1', 'files': entries},
                                            ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'review': str(OUT / 'final-review.md'), 'status': record['review_decision'], 'evidence_files': len(entries)}))
