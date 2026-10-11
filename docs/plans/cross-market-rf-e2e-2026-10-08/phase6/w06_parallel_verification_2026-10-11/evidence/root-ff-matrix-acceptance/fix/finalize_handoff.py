"""ROOT-authorized lane-only PWF/handoff updates and small synthetic evidence package."""
import collections
import hashlib
import json
from pathlib import Path
import re
import zipfile

FF=Path(r'C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
CWP=Path(r'C:/Users/郑曾波/Projects/company-wiki')
HERE=Path(__file__).resolve().parent
ATTEMPT=CWP/'.tmp/w06-matrix-evidence/attempt-1bb98380f75347e7b792e5966c11867e'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

report=json.loads((ATTEMPT/'report.json').read_text(encoding='utf-8'))
repro=json.loads((HERE/'cross-period-repro.json').read_text(encoding='utf-8'))
counts=dict(collections.Counter(c['result'] for c in report['cases']))
note='''
## ROOT final engineering freeze — 2026-10-11

**State: harness engineering GREEN; integration PARTIAL_PRODUCT_FAILURES. Author frozen.**

- Formal original business RED: oracle 7 FAIL / 13 PASS; runtime 3 FAIL / 1 PASS. Generic cross-market fixture SHA collision additionally proved RED (1 FAIL), then fixture identities and bodies made unique by market/security/kind/year/period.
- Concentrated final tests: 34 PASS / 2.95 seconds; Ruff passed. These do not claim product flow COMPLETE.
- Actual final offline node: 41 required cases, 19 PASS / 21 FAIL / 1 PARTIAL, 132.5406 seconds under absolute 180-second batch and 30-second case caps. Zero real provider/paid/model/network requests; translation attempts 0. Thirteen accepted source refs were independently opened with current SourceVersionReader and actual byte SHA, each 1 physical original. Existing parent entries and empty-dir/absent shape preserved; own scratch removed; retained output is explicit evidence.
- Nine warm2024 financial documents were created by real public CWP ensure/import. Local2024 hits all pass. New2025/2026 requests returned not_found without supplier fetch. The chain-A and most ET cases never reached ET because primary2025 filing preparation failed; they are failed/partial, not skipped or relabeled expected failures. Three oracle findings diagnose unmet intended checks, not three proved ET implementation defects.
- Important diagnostic: actual get_verified_assertion(reader='steady') for both US/CN acquired2024 sources returns null; actual source_fact_patch/evidence therefore absent. Real acquisition/import and a complete acquisition metadata record are NOT proof of a verified source-fact assertion. ROOT must decide whether test setup needs an additional real public preparation stage, or the producer has a registration/reconciliation defect. No handcrafted SQL assertions or source_fact_patch were introduced.
- Original attempt-1 HOME failure and earlier supplier same-SHA collision are retained but NOT production defect evidence. Earlier fully populated scanned-sidecar rejection expectation was mistaken; preserved receipt remains, final extra control is explicitly incomplete metadata (missing period/publication). No company-specific workaround or producer code modification.
- Canonical fix evidence: company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-ff-matrix-acceptance/fix/. See root_report.md, cross-period-repro.json, offline-evidence.zip and freeze-manifest.json. Original worker handoff/intake unchanged.

### Next Step
ROOT non-author reception of frozen tool source/tests, followed by ROOT diagnosis of actual imported source assertions and new-period acquisition. Preserve all matrix vectors, use actual public setup if needed, rerun one major offline node after resolution. Only ROOT commits/merges/installs/pushes.
'''
for name in ('task_plan.md','findings.md','progress.md'):
 p=FF/'.planning/w06-ff-matrix'/name
 text=p.read_text(encoding='utf-8')
 if '## ROOT final engineering freeze' not in text:
  if name=='task_plan.md':
   text=re.sub(r'## Current Phase\n.*?(?=\n## Next Step)', '## Current Phase\nROOT reception: engineering complete and frozen; integration partial pending ROOT diagnosis.\n',text,flags=re.S)
   text=re.sub(r'## Next Step\n.*?(?=\n## Phases)', '## Next Step\nROOT independently reviews the frozen source/tests and diagnoses the missing verified source-fact assertions; no author producer edits.\n',text,flags=re.S)
  p.write_text(text+note,encoding='utf-8')

readme=FF/'tools/offline_contract_matrix/README.md'
text=readme.read_text(encoding='utf-8')
text=text.replace('批次目标 ≤180s','批次绝对截止 ≤180s').replace('tests/test_w06_contract_matrix.py`','tests/test_w06_contract_matrix.py tests/test_w06_matrix_runtime.py`')
text=text.replace('| 案例 | 文档类型 | 声明层 | 观测层 | 结果 |','| 案例 | 文档类型 | 声明层 | 预期观测层 | 预期检查 |')
if '## ROOT reception status' not in text:
 text+='''
## ROOT reception status (2026-10-11)

The table above describes intended coverage, not observed PASS. The fixed required registry contains 41 cases. Exit 0 requires every case PASS, complete bound request/response/receipt/fresh-byte evidence, measured budgets, and restored owned scratch. FAIL/PARTIAL/NOT_RUN or any oracle finding returns nonzero.

Each run creates fresh UUID scratch and output children. Only that scratch child and newly-created empty scratch ancestors are removed. Old files, sentinels, output reports, and initially-existing empty directories are preserved. Retained output is evidence and is not scratch. Process deadlines are absolute across seed/binding/cases/proofs; owned child trees are terminated/reaped when exhausted. Child startup has an explicit platform-variable allowlist, synthetic HOME/config/fake key and socket/translation guards before product imports. No real configuration/key bytes are read or hashed; only stat metadata is observed.

Final engineering checks: 34 PASS and Ruff clean. Integration result: 19 PASS / 21 FAIL / 1 PARTIAL in 132.54 s. Nine real-writer warm2024 sources succeed; 2025/2026 acquisition and primary-filing preconditions remain unresolved. Actual verified source-fact assertions are absent in the minimal repro, so these results alone do not establish the producer root cause. ROOT owns investigation. See docs/handoffs/w06-ff-matrix/root_handoff.md. Do not downgrade expectations, skip cases, hand-create assertions, or call the result COMPLETE.

Fixture responses exercise actual FF/CWP/ET runtime when its prerequisites resolve. They do not prove configured StockInfoDLSimple/Dayu supplier reachability. Configured A-share downloader is StockInfoDLSimple/v2-clean-rewrite; Dayu remains external and receives no code writes. Unknown producer usage remains null; observed fixture calls are separate and never substituted for real-cost data.
'''
readme.write_text(text,encoding='utf-8')

bundle=HERE/'offline-evidence.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted((CWP/'.tmp/w06-matrix-evidence').rglob('*')):
  if p.is_file(): z.write(p,'matrix/'+p.relative_to(CWP/'.tmp/w06-matrix-evidence').as_posix())
 for p in sorted(Path(repro['output']).rglob('*')):
  if p.is_file(): z.write(p,'repro/'+p.relative_to(Path(repro['output']).parent).as_posix())

details={
 'schema_version':'w06-root-handoff/1','delivery_status':'PARTIAL_PRODUCT_FAILURES',
 'engineering_tests':{'passed':34,'seconds':2.95,'red_oracle_failed':7,'red_runtime_failed':3,'fixture_collision_red_failed':1,'ruff':'passed'},
 'matrix_counts':counts,'matrix_seconds':report['scope']['batch_elapsed_seconds'],
 'actual_report':str(ATTEMPT/'report.json'),'actual_report_sha256':sha(ATTEMPT/'report.json'),
 'canonical_evidence':str(HERE),'bundle':str(bundle),'bundle_sha256':sha(bundle),'bundle_bytes':bundle.stat().st_size,
 'producer_bindings':report['dependencies'],'source_proof_count':len(report['source_proofs']['proofs']),
 'restore':report['restore'],'scope':report['scope'],'cost':report['cost'],
 'matrix_failures':[{'case_id':c['id'],'result':c['result'],'request_ref':c['request_ref'],'response_ref':c['response_ref'],'diagnostics':c['diagnostics']} for c in report['cases'] if c['result']!='PASS'],
 'oracle_diagnostics':report['oracle'],'oracle_attribution':'failed intended ET checks due primary2025 precondition; not proof of three ET defects',
 'cross_period_repro':str(HERE/'cross-period-repro.json'),'actual_verified_facts':repro['verified_facts']['path'],
 'source_fact_findings':[{'source_id':x['source_id'],'document_id':x['document_id'],'actual_verified_assertion':x['actual_verified_assertion'],'actual_evidence_payload':x['actual_evidence_payload']} for x in repro['verified_facts']['records']],
 'limitations':['Acquisition writer imported bytes/metadata; actual steady verified fact assertion null. ROOT must diagnose whether real public preparation setup or producer registration/reconciliation is missing.','ET stages blocked in final matrix by missing primary2025; no ET-specific defect proven.','Supplier responses are fixtures; actual configured StockInfoDLSimple/Dayu network invocation is unverified.','Original HOME failure and fixture SHA collision retained, not production proof.'],
 'next_owner':'ROOT','author_state':'FROZEN_STOP','commit_install_push':False}
handoff=FF/'docs/handoffs/w06-ff-matrix'
md='''# W06-FF-MATRIX ROOT reception handoff

Status: **PARTIAL_PRODUCT_FAILURES**. Harness source/tests are frozen; ROOT owns independent acceptance and any producer work.

- Engineering: 34 tests pass (2.95 s); Ruff clean. Original formal RED retained.
- Actual required matrix: 41 cases, 19 PASS / 21 FAIL / 1 PARTIAL, 132.54 s. Exit nonzero; not COMPLETE.
- Nine warm2024 same-period local controls pass; all nine requested2026 acquisition cases fail without supplier fetch. US2025 initial acquisition also misses, preventing most ET scenarios from reaching ET.
- Minimal actual CWP-writer reproduction finds acquisition records but **null steady verified source-fact assertion and patch** for US/CN2024. Thus the missing-period results are evidence needing ROOT diagnosis, not yet a proved reconciliation algorithm defect. Do not manufacture fact assertions or alter expectations.
- Thirteen accepted originals fresh-open with matching byte SHA and one physical file. Zero paid/network/model/translation operations. Stat-only production baseline unchanged. Scratch restored; explicit retained output evidence remains.
- Historical intake/worker handoff and every earlier failing node are preserved. Original attempt-1 HOME failure and cross-market fixture same-SHA collision are not producer proof.

## Evidence / interfaces

Read root_handoff.json for exact request/response paths, actual producer HEAD/module SHA, failure case registry, assertions and canonical evidence paths. The small offline-evidence.zip contains all synthetic reports/artifacts from four ROOT attempts plus the independent minimal reproduction; no original lake copies or live credentials. ZIP records preserve original evidence_root paths; inspect artifacts directly or unpack to a separate directory and rewrite paths only in a review copy.

Canonical evidence: '''+str(HERE)+'''

## Next large node

ROOT independently runs focused tests and audits freeze hashes; investigates actual verified fact registration/setup using cross-period-repro.json; then applies any producer correction in ROOT-owned scope and reruns the unchanged required matrix. Do not call test tooling PASS an overall product acceptance. No installation, commit or push performed by this author.
'''
(handoff/'root_handoff.json').write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf-8')
(handoff/'root_handoff.md').write_text(md,encoding='utf-8')
(HERE/'root_report.md').write_text(md,encoding='utf-8')
(HERE/'root_handoff.json').write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf-8')
selected=[p for p in (FF/'tools/offline_contract_matrix').glob('*.py')]+[readme]+[FF/'tests/test_w06_contract_matrix.py',FF/'tests/test_w06_matrix_runtime.py']+[FF/'.planning/w06-ff-matrix'/n for n in ('task_plan.md','findings.md','progress.md')]+[handoff/'root_handoff.json',handoff/'root_handoff.md']
manifest={'schema_version':'w06-root-freeze/1','state':'FROZEN_STOP','files':[{'path':p.relative_to(FF).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(selected)],'evidence':{'offline_bundle_sha256':sha(bundle),'report_sha256':sha(ATTEMPT/'report.json'),'repro_sha256':sha(HERE/'cross-period-repro.json')}}
(HERE/'freeze-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(handoff/'root_freeze_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'bundle_bytes':bundle.stat().st_size,'counts':counts,'freeze_manifest':str(HERE/'freeze-manifest.json'),'freeze_sha256':sha(HERE/'freeze-manifest.json'),'files':len(selected)},ensure_ascii=True))
