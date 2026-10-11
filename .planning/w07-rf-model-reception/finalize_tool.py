from pathlib import Path
import json

root = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-rf-model-reception')
p = root/'tools/model_generalization_matrix/cases.py'
s = p.read_text(encoding='utf-8')
assert '"annual": {"2026": 144.0, "2027": 172.8}' in s
s = s.replace('"annual": {"2026": 144.0, "2027": 172.8}', '"annual": {"2026": (100.0 + 50.0) * 1.1, "2027": (100.0 + 50.0) * 1.1 ** 2}')
p.write_text(s, encoding='utf-8')
p = root/'tools/tests/test_root_w07_model_boundaries.py'
p.write_text(p.read_text(encoding='utf-8')+'''
def test_full_declared_matrix_matches_hand_oracles(runtime):
    engine = NativeEngine(runtime)
    results = [run_case(spec, engine) for spec in C.CASES]
    assert all(r.status in {"PASS", "REJECT_OK"} for r in results), [
        (r.case_id, r.status, r.assertions, r.diagnostics)
        for r in results if r.status not in {"PASS", "REJECT_OK"}
    ]
''', encoding='utf-8')

readme = root/'tools/model_generalization_matrix/README.md'
s = readme.read_text(encoding='utf-8').replace('A wrong engine result is therefore always caught.', 'Wrong values for declared assertions are detected; undeclared boundaries remain unverified.')
s = s.replace('dated control + cross-FY partial windows', 'dated calendar H1 evidence flow').replace('management target + gross/net/cannibalization', 'annual/run-rate management target').replace('shared shock + joint scenarios', 'shared timing shock and sum cap').replace(' + future actual |', ' |')
s += '''
## ROOT reception scope and remaining coverage

Execution `status=COMPLETE` means all **declared** vectors, requested CLI checks,
readonly hashes and scratch restoration passed. It does not certify the whole
construction card. `combination_coverage.status=PARTIAL` explicitly lists:

- CNY/HKD label and same-currency scaling vectors beyond current USD scale test.
- Acquisition/control, non-calendar cross-FY and missing-quarter ancestry.
- Correlated joint volume/price scenarios beyond a timing delay and sum cap.
- Cumulative target, net presentation and cannibalization.
- Future actual/WAPE null through final draft output beyond observed-range null.

Those are remaining ROOT planning items, not `NOT_SUPPORTED` claims about the
native engine. No fake API or copied forecast engine substitutes for them.

Each case now retains only its own actual native request/result and exceptions.
The 16 inputs are synthetic and bounded; this payload retention must not be
copied into real-company processing. Output must be a new directory, prior
evidence is never overwritten. Newly created scratch parents are removed and
existing sentinel contents remain. Infrastructure errors cannot be contract
rejections. Missing unknown fields, empty assertions/case sets, incomplete
vectors, CLI failure, readonly drift and cleanup failure cannot give success.

ROOT focused tests: `python -B -m pytest -q tools/tests/test_w07_model_generalization.py tools/tests/test_root_w07_model_boundaries.py`.
The complete matrix remains a manual milestone; no new per-commit/CI gate.
'''
readme.write_text(s, encoding='utf-8')

# Keep only a small diagnostic from the first ROOT E2E: no duplicate native payloads.
plan = Path(__file__).resolve().parent
old = plan/'native-e2e'
raw = json.loads((old/'model-generalization-matrix.json').read_text(encoding='utf-8'))
minimal = {k: raw[k] for k in ['status', 'counts', 'cleanup', 'cli_evidence', 'residuals']}
minimal['failed_cases'] = [{k: c[k] for k in ['case_id', 'expected', 'observed', 'assertions']} for c in raw['cases'] if c['status'] == 'FAIL']
minimal['cause'] = 'ROOT initially used wrong fixture constants (144/172.8). Native fixture is (100+50)*1.1^n. Corrected from fixture input arithmetic, not observed output. Full-matrix regression added.'
(plan/'first-e2e-diagnostic.json').write_text(json.dumps(minimal, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert old.resolve().parent == plan.resolve()
for name in ['model-generalization-matrix.json', 'model-generalization-matrix.md']:
    (old/name).unlink()
old.rmdir()
print('Independent input arithmetic fixed; matrix regression and accurate coverage docs added.')
