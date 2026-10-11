"""Freeze this authority repair independently; historical freeze/report/ZIP stay unchanged."""
from pathlib import Path
import collections
import hashlib
import json
import re

FF=Path(r'C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

old=HERE.parent
assert sha(old/'freeze-manifest.json')=='e098e5bca867a33802d8fcf6945af7370bb092aec13a4397be475244c43e1246'
assert sha(old/'offline-evidence.zip')=='dd8fc402a337ef02b3db456a760162f59129c9e7ae5667c62d281294d903bea3'
original=HERE.parent.parent/'independent-final/original-41-report-copy.json'
assert sha(original)=='aa2ab10add76f89e6e259fa0a05c8ad961f562f46b3fd21a1e94c1b2a3acc72f'
reaudit=json.loads((HERE/'frozen-matrix-re-audit.json').read_text(encoding='utf-8'))
plan_note='''
## Case authority repair reception — 2026-10-11

- Independent final review found TOOL_BLOCKER_CASE_CONTRACT_AUTHORITY_P1: report.required_cases / case.expected / hashed request could redefine intended work. Old engineering freeze remains historical; this repair has its own freeze under fix/case-authority/.
- Fixed executable immutable CaseSpec/RunSpec is now shared by registry/dispatch, launch input checks, report declaration and oracle. It owns every required ID, company/market/kind, exact FY/period/as-of/intent/companion/limits, fixture scenario/date/content and credential-presence vector, expected assertions and declared execution scope. Caller-modified required lists cannot remove work; unknown/duplicate/extra cases cannot replace missing cases.
- Fixed assertions re-evaluate actual response meaning rather than trusting PASS/summary booleans. Bound request/response/fixture SHA checks remain; caller changes to expected/scope no longer change which rules execute. Missing new fixture evidence is diagnosed, not filled in retrospectively.
- TDD: original three authority counterexamples 3 FAIL, then GREEN; an additional shared assertion proof flips each of 21 old real FAIL labels to PASS, all 21 RED then GREEN. Mandatory-case property tests cover every one of 41 removals and 41 duplicate/extra replacements; valid full-registry and named single-case positive controls, every original request vector, runner shared object registry and pre-launch drift checks are included. Concentrated package: 195 PASS / 4.42 seconds, Ruff clean.
- Old actual 41-case result stays 19 PASS / 21 FAIL / 1 PARTIAL. Re-audit retains all original response/status bytes and reports 22 required cases not passed + original three intended-stage diagnostics + 40 missing new fixture receipts. Original 19 PASS cases have no new business-assertion error. This repair does not resolve missing source-fact assertions or certify producer completion. No new full matrix/producer/provider/network/model run.
- Old manifest SHA e098e5bca867a33802d8fcf6945af7370bb092aec13a4397be475244c43e1246, original 41 report SHA aa2ab10add76f89e6e259fa0a05c8ad961f562f46b3fd21a1e94c1b2a3acc72f and ZIP SHA dd8fc402a337ef02b3db456a760162f59129c9e7ae5667c62d281294d903bea3 remain unchanged. No producer/scripts/config/CI writes, no commit/install/push, no permissions or manual signoffs added.

### Next Step
ROOT independently verifies the case-authority freeze and three retained counterexamples. ROOT owns producer/source-fact diagnosis and reruns the unchanged 41-case real matrix after prerequisite remediation; author is frozen STOP.
'''
for name in ('task_plan.md','findings.md','progress.md'):
    p=FF/'.planning/w06-ff-matrix'/name
    text=p.read_text(encoding='utf-8')
    if '## Case authority repair reception' not in text:
        if name=='task_plan.md':
            text=re.sub(r'## Current Phase\n.*?(?=\n## Next Step)','## Current Phase\nCase authority engineering repair complete and frozen; ROOT independent reception next. Product integration remains partial.\n',text,flags=re.S)
            text=re.sub(r'## Next Step\n.*?(?=\n## Phases)','## Next Step\nROOT reviews the independent case-authority freeze, then diagnoses producer source-fact setup before unchanged real matrix rerun.\n',text,flags=re.S)
        p.write_text(text+plan_note,encoding='utf-8')

p=FF/'tools/offline_contract_matrix/README.md';text=p.read_text(encoding='utf-8')
text=text.replace('tests/test_w06_contract_matrix.py tests/test_w06_matrix_runtime.py`','tests/test_w06_contract_matrix.py tests/test_w06_matrix_runtime.py tests/test_w06_case_authority.py`')
if '## Fixed case authority' not in text:
    text+='''
## Fixed case authority (ROOT repair, 2026-10-11)

`case_specs.py` is the only executable definition of mandatory cases, full input requests, provider fixture scenarios, expected assertions and declared scope. `cli_main._case_registry()` binds its exact CaseSpec objects; Context verifies each request/fixture vector before starting FF; oracle independently uses the same definitions. `report.required_cases`, expected flags, scenarios and result labels are observations, never authority. Missing/unknown/duplicate cases, changing market/company/period/as-of/intent/mode/companion/limits, clearing an expectation or relabeling an incompatible response PASS cannot certify acceptance.

`oracle.audit_case(spec, case)` is a component check. `oracle.audit(report)` additionally checks the complete fixed coverage and bound request/response/fixture bytes, source proofs and measured isolation. A single case/component positive control never certifies a complete product matrix. Historical reports without newly required fixture receipts remain historical/partial; do not manufacture them. No new human permission, authorization document or identity database is involved.

Focused tool checks: 195 PASS (~5 seconds) and Ruff clean. The original actual product matrix remains 19 PASS / 21 FAIL / 1 PARTIAL. See `docs/handoffs/w06-ff-matrix/case-authority/handoff.md` for independent reception. Construction helper scripts in canonical evidence are historical one-shot edit records, not replay entry points; run the three test files above, then the unchanged real matrix only after ROOT producer fixes.
'''
    p.write_text(text,encoding='utf-8')

handoff=FF/'docs/handoffs/w06-ff-matrix/case-authority'
handoff.mkdir(parents=True,exist_ok=True)
md='''# W06 CaseSpec authority repair — ROOT handoff

**Author FROZEN_STOP. Engineering tests GREEN, product integration remains PARTIAL_PRODUCT_FAILURES.**

The independent blocker was common: a report could redefine omitted cases, remove a mandatory assertion, or change the intended request vector while updating its hash. Fixed immutable `CaseSpec`/`RunSpec` now owns registry, full request/fixture vector, expected assertions and execution scope; runner and oracle consume it. No extra license, identity store, manual review or signoff was added.

## TDD / concentrated verification

- Retained exact three independent authority inputs → formal 3 FAIL (red.log).
- Fixed response meaning proof: each of 21 real FAIL labels changed to PASS → 21 FAIL before implementation (assertion-red.log).
- Full package: 195 PASS / 4.42 seconds (green-final.log), Ruff clean. Includes all 41 missing-case properties, all 41 duplicate/extra replacements, complete registry and named single-case positives, all 41 original full request vectors, dimensions/companion budgets, fixture/date/credential drift, shared runner registry and rejection before process launch.
- No full 41-case CLI/provider/network/model rerun. Test component fixtures do not claim newly completed product execution.

## Original evidence and remaining work

Original 41 actual statuses remain 19 PASS / 21 FAIL / 1 PARTIAL. New read-only audit reports 22 required cases not passed, original three unmet-stage checks, and 40 missing newly-required fixture receipts. No new business assertion errors occur on original 19 PASS cases. Historical missing receipts must stay missing; no retroactive manufacture. These 40 gaps are newly required test observability only, not production authorization, provider permission or acquisition prerequisites.

Old freeze/report/ZIP hashes and original independent FAIL are preserved. Actual steady source-fact assertion absence and primary2025 missing remain ROOT diagnosis; ET not-started is not proof of an ET defect. ROOT reruns unchanged real matrix after producer prerequisites are resolved.

## Read / replay interfaces

Canonical independent evidence: '''+str(HERE)+'''

1. Read report.json/manifest.json, exact-inputs.json and frozen-matrix-re-audit.json.
2. Run from this FF root: `python -B -m pytest -q tests/test_w06_contract_matrix.py tests/test_w06_matrix_runtime.py tests/test_w06_case_authority.py --basetemp <fresh-short-owned-path>`.
3. Run `python -B -m ruff check tools/offline_contract_matrix tests/test_w06_contract_matrix.py tests/test_w06_matrix_runtime.py tests/test_w06_case_authority.py`.
4. Independent reviewer replays original three counterexamples; use fresh owned paths for modified request bytes. Never overwrite originals or old ZIP.
5. ROOT alone commits/merges/installs/pushes. This author stops after freeze.

Construction helper scripts are archived one-shot implementation records and not re-executable acceptance commands. Scope is test tooling only; no scripts/config/CI/Dayu/IQS changes.
'''
details={'schema_version':'w06-case-authority-handoff/1','author_state':'FROZEN_STOP','engineering':'GREEN','product':'PARTIAL_PRODUCT_FAILURES','tests':{'passed':195,'seconds':4.42,'authority_red_failed':3,'assertion_red_failed':21,'ruff':'passed'},'original_result_counts':reaudit['case_counts_unchanged'],'re_audit':str(HERE/'frozen-matrix-re-audit.json'),'canonical_evidence':str(HERE),'old_manifest_sha256':sha(old/'freeze-manifest.json'),'original_report_sha256':sha(original),'old_bundle_sha256':sha(old/'offline-evidence.zip'),'producer_calls_new':0,'commit_install_push':False,'next_owner':'ROOT'}
(HERE/'report.md').write_text(md,encoding='utf-8')
(HERE/'report.json').write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf-8')
(handoff/'handoff.md').write_text(md,encoding='utf-8')
(handoff/'handoff.json').write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf-8')
files=list((FF/'tools/offline_contract_matrix').glob('*.py'))+[FF/'tools/offline_contract_matrix/README.md']+[FF/'tests'/n for n in ('test_w06_contract_matrix.py','test_w06_matrix_runtime.py','test_w06_case_authority.py')]+[FF/'.planning/w06-ff-matrix'/n for n in ('task_plan.md','findings.md','progress.md')]+[p for p in (FF/'tests/fixtures/w06_contract_matrix/authority').rglob('*') if p.is_file()]+[handoff/'handoff.md',handoff/'handoff.json']
manifest={'schema_version':'w06-case-authority-freeze/1','state':'FROZEN_STOP','files':[{'path':p.relative_to(FF).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)],'evidence':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='manifest.json'],'old_manifest_sha256':sha(old/'freeze-manifest.json'),'old_bundle_sha256':sha(old/'offline-evidence.zip'),'original_report_sha256':sha(original)}
blob=json.dumps(manifest,ensure_ascii=False,indent=2)
(HERE/'manifest.json').write_text(blob,encoding='utf-8')
(handoff/'manifest.json').write_text(blob,encoding='utf-8')
print(json.dumps({'freeze_sha256':sha(HERE/'manifest.json'),'source_files':len(files),'fixture_bytes':sum(p.stat().st_size for p in (FF/'tests/fixtures/w06_contract_matrix/authority').rglob('*') if p.is_file()),'old_evidence_unchanged':True},ensure_ascii=True))
