"""Freeze ROOT acceptance after the independent review; original reports remain."""
import hashlib
import json
from pathlib import Path

TREE = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures-root')
OUT = TREE / 'docs/handoffs/w06-audit-measures'
PRODUCT = TREE / 'skills/revenue-forecast-audit/scripts/financial_measure_audit.py'
SHA = 'b48e20bb9ecf88c1cb86821978c668cb83e963989dc4b1ca099b5d5bbad48020'
assert hashlib.sha256(PRODUCT.read_bytes()).hexdigest() == SHA
report = {
    'schema_version':'w06-root-measures-acceptance/1', 'status':'PASS_WITH_SCOPE',
    'worker_head':'6a50d7ed1b4cf389589c7ca62b4ab161b5dc0ad1',
    'integration_base':'321d4c165575e81add3b4aa1ee9ba0a047ca6082',
    'product_physical_sha256':SHA,
    'verification':{'full_suite_before_one_field_delta':296,
        'final_financial_suite':77, 'original_numeric':7,
        'independent_original_vectors':19, 'independent_extra_vectors':8,
        'independent_final_boundary_checks':4,
        'skill_structure':'PASS_UTF8', 'offline_cli_e2e':'PASS',
        'scratch_restored':True, 'original_failures_preserved':True},
    'providers':0, 'llm_calls':0, 'new_cost_usd':0,
    'source_truth_verified':False, 'economic_reasonableness':'not_evaluated',
    'main_merge_and_installation':'ROOT subsequent publication step',
}
(OUT/'root-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'root-acceptance.md').write_text('''# ROOT acceptance — W06 financial measures

PASS within the declared typed-math scope. Original worker commits and all failing probes remain.
ROOT integrated current main321d (W05 causal closure), repaired five shared semantic/boundary causes,
and wired the tool into the process/analyst skill references without adding a permission or release gate.

296 tests passed at the main engineering node; the independent review replayed the original 19 vectors
and eight additional probes. Its P2 empty-report field omission was corrected through a six-failure
regression; final financial77 passed and the non-author review verified three pure + one real CLI checks.
The final delta only adds source_qualification_verified:false to that factory, proven by reverse SHA.
No repeated full suite was required for that output-only change. Skill structure validated in UTF-8.

Current sum checks temporal concatenation, not automatic segment consolidation. Source availability,
opaque economic labels, source truth, complete company coverage and buy-side model quality remain
explicit scope limits. Four independent reviewers still perform their own source and model checks.
All test roots restored; no provider/LLM/raw-document operations or incremental fees.

The acceptance JSON binds the frozen physical bytes and test counts. ROOT publishes the merge and
only five named skill files plus manifest per installed copy; unrelated config/output stays intact.
The central evidence/independent reports reside in company-wiki phase6/w06_parallel_verification_2026-10-11/
evidence/root-audit-measures-acceptance/. Audit has no remote; no remote push is claimed.
''',encoding='utf-8')
print('ROOT acceptance files frozen')
