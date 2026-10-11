"""Normal OCR merge commit and local main integration, after frozen acceptance."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TREE = ROOT.parent / '_harness_worktrees/w05/cwp-ocr-root'
EVIDENCE = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-cwp-ocr-acceptance'
review = json.loads((EVIDENCE/'independent-preallocation/report.json').read_text(encoding='utf-8'))
real = json.loads((EVIDENCE/'preallocation-real-e2e/root-real-e2e-receipt.json').read_text(encoding='utf-8'))
assert review['status'] == 'PASS_WITH_SCOPE' and real['status'] == 'PASS'
assert real['raw_config_unchanged'] and real['scratch_after'] == 'absent'
for name, digest in review['product_sha256'].items():
    assert hashlib.sha256((TREE/name).read_bytes()).hexdigest() == digest, name
files = [str(p.relative_to(TREE)).replace('\\', '/') for p in [
    *(TREE/'src/company_wiki/document_normalization'/name for name in
      ('isolated_ocr.py','local_ocr.py','ocr_composition.py','ocr_region_recovery.py')),
    TREE/'src/company_wiki/source_catalog/narrative_normalization.py',
    *(TREE/'tests/document_normalization'/name for name in
      ('test_isolated_ocr.py','test_local_ocr_adapter.py','test_ocr_region_composition.py','test_ocr_region_recovery.py')),
    TREE/'tools/pre_push_gate.py', TREE/'tests/unit/test_ci_push_selection.py']]
report = {'schema_version':'root-w05-ocr-acceptance/1','status':'PASS_WITH_SCOPE',
    'worker_head':'6fe9a82a6a96fe024774791e2018c882a098d512',
    'product_sha256':{name:hashlib.sha256((TREE/name).read_bytes()).hexdigest() for name in files},
    'native_suite_before_preallocation':22,'preallocation_focused':54,
    'independent_preallocation':34,'shared_fast_smoke':148,
    'real_two_phase_seconds':real['elapsed_seconds'],'raw_config_unchanged':True,
    'scratch_restored':True,'fees_usd':0,
    'scope':'Windows source/resource contract; POSIX static only; no peak RSS or research-quality certification',
    'original_failures_preserved':True,
    'main_integration_and_remote_ci':'publication step follows this frozen acceptance'}
OUT = TREE/'docs/handoffs/w05-cwp-ocr'
assert not (OUT/'ROOT-acceptance.json').exists()
(OUT/'ROOT-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'ROOT-acceptance.md').write_text('''# ROOT acceptance — Windows local OCR

Accepted within the frozen source/resource scope. Worker commits are preserved through normal merge.
Shared budget now reserves exact planned geometry before image allocation and native inference;
partial dropped regions, stack mapping and non-square rotations retain honest recovery status.
One native subprocess owns its engine and absolute deadline, including startup and preflight.
The redundant blocking-stdin thread was removed after proving a Windows UCRT/NumPy import deadlock;
OS job/independent guardian ownership remains, without vendor/model/config changes.

Final 54 focused and 34 independent preallocation checks pass. The unchanged native boundary's
22 checks passed before this final geometry-only delta. The real SourceVersionReader → OCR →
fresh locator replay passes in 83.006s total (phases37.706/44.104, original85/90s limits).
Two definitions recover,22 previous text/box/confidence records and locators are exact.
Original source/config bytes and isolated scratch baseline remain unchanged; no network or fees.

Six small regression nodes are registered in the existing CI/local smoke (148pass/24.45s),
without adding another gate or real-model test to routine pushes. All original FAILs remain
in company-wiki phase6/w05_parallel_common_roots_2026-10-11/evidence/root-cwp-ocr-acceptance/.
184 is an earlier pre-import-fix baseline, not the final test count. POSIX is static only,
peak RSS and complete OCR recall were not measured, and investment quality is not certified.
The ROOT JSON binds exact physical source/test bytes; Git normalization may change CRLF on main.
''',encoding='utf-8')
def run(cwd, *args):
    return subprocess.run(args,cwd=cwd,check=True)
assert subprocess.check_output(['git','rev-parse','MERGE_HEAD'],cwd=TREE,text=True).strip() == report['worker_head']
run(TREE,'git','add','--','tools/pre_push_gate.py','tests/unit/test_ci_push_selection.py',
    'docs/handoffs/w05-cwp-ocr/ROOT-acceptance.md','docs/handoffs/w05-cwp-ocr/ROOT-acceptance.json')
run(TREE,'git','commit','-m','fix(ocr): bound native execution and reserve source ROI before allocation')
head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=TREE,text=True).strip()
run(ROOT,'git','merge','--no-ff','--no-edit',head)
main = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
target=EVIDENCE/'local-main-integration.json'
assert not target.exists()
target.write_text(json.dumps({'integration_commit':head,'main_head':main,
    'normal_hooks':True,'remote_push_pending':True},indent=2)+'\n',encoding='utf-8')
print('OCR normal main integration',main,'remote push pending')
