"""Commit only ROOT-owned finished reception records and three W07 packets."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
assert not subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT).strip(), 'Preserve pre-existing staging'
paths = ['.gitattributes', '.planning/w07-parallel-packages',
         '.planning/w04-root-novelty-recall/phase2-independent', '.planning/w04-selector-integration',
         '.planning/w06-cross-period-acquisition/cutoff-implementation',
         '.planning/w06-cross-period-acquisition/cutoff-independent/retest',
         '.planning/w06-cross-period-acquisition/matrix-deadline-diagnosis.md',
         '.planning/w06-cross-period-acquisition/run_final_matrix.py',
         'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w07_parallel_quality_2026-10-11',
         'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/ROOT-reception-status.md',
         'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-ff-matrix-acceptance/recall-checkpoint-publication.json',
         'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-ff-matrix-acceptance/root-matrix-final-usage-v2']
for base in ['docs/plans/narrative-evidence-pilot-2026-09-26', 'docs/plans/cross-market-rf-e2e-2026-10-08',
             'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/main_auto_official_json',
             'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11']:
    paths += [base + '/' + name for name in ('task_plan.md','findings.md','progress.md')]
subprocess.run(['git','add','--pathspec-from-file=-','--pathspec-file-nul'],cwd=ROOT,
               input=b''.join(p.encode('utf-8')+b'\0' for p in paths),check=True)
subprocess.run(['git','diff','--cached','--check'],cwd=ROOT,check=True)
subprocess.run(['git','commit','-m','docs: prepare three isolated W07 lanes and record reception checkpoints'],cwd=ROOT,check=True)
print(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),flush=True)
subprocess.run(['git','push','origin','master'],cwd=ROOT,check=True)
print('ROOT checkpoint pushed normally',flush=True)
