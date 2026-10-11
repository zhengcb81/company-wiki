"""Remove only this ROOT-created runtime copy and two retained test attempts."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

PLAN = Path(__file__).resolve().parent
FF = Path('C:/Users/郑曾波/Projects/filing-fetch')
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-ff-perf-reception')
summary = json.loads((PLAN/'acceptance.json').read_text(encoding='utf-8'))
archive = PLAN/'offline-evidence.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == summary['archive_sha256']
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    attempts = {Path(n).parts[0] for n in z.namelist()}
assert len(attempts)==2 and summary['final_attempt'] in attempts
assert subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip() == '64b4d294a1e61e595e330b4a7d4075c289f9fdc3'
status = subprocess.check_output(['git','-C',str(ROOT),'status','--short'],text=True).strip()
assert status == '?? .planning/w07-ff-matrix-efficiency/input/'
copied = ROOT/'.planning/w07-ff-matrix-efficiency/input'
assert copied.resolve().is_relative_to(ROOT.resolve()) and not copied.is_symlink()
shutil.rmtree(copied)
subprocess.run(['git','-C',str(FF),'worktree','remove',str(ROOT)],check=True)
reports = Path.home()/'AppData/Local/Temp/w7ff-root-reports'
assert reports.resolve().is_relative_to((Path.home()/'AppData/Local/Temp').resolve())
assert {p.name for p in reports.iterdir()} == attempts
for attempt in attempts:
    target = reports/attempt
    assert target.resolve().is_relative_to(reports.resolve()) and not target.is_symlink()
    shutil.rmtree(target)
reports.rmdir()
assert not (reports.parent/'w7ff-root-scratch').exists()
# A failed sandbox-temp replay created this exact empty owned directory.
failed = Path.home()/'AppData/Local/Packages/sandbox.{4c21efa0-ba16-4fec-a813-bb1a7e6b5ff7}/AC/Temp/root-w07-replay-u7e6aeji'
if failed.exists():
    assert not list(failed.iterdir())
    failed.rmdir()
result = {'root_worktree_removed':not ROOT.exists(),'owned_test_reports_removed':not reports.exists(),
          'owned_scratch_restored_absent':True,'compressed_evidence_preserved':True,
          'worker_inputs_and_branches_preserved':True}
(PLAN/'cleanup.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
