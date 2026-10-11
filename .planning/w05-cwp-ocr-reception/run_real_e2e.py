"""ROOT real replay, isolated scratch and bounded child; zero network/cost."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import time

PROJECT = Path(__file__).resolve().parents[2]
TREE = PROJECT.parent / '_harness_worktrees/w05/cwp-ocr-root'
EVIDENCE = PROJECT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-cwp-ocr-acceptance'
SCRATCH = Path(__file__).resolve().parent / 'real-scratch'
SCRIPT = TREE / 'docs/handoffs/w05-cwp-ocr/scripts/e2e_slide7_recovery.py'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def child():
    scope = runpy.run_path(str(SCRIPT), run_name='root_ocr_receipt')
    g = scope['main'].__globals__
    # Redirect evidence destinations only; real source/config/assertions unchanged.
    g['HERE'] = str(SCRATCH)
    g['OUT'] = str(SCRATCH/'result.json')
    try:
        g['main']()
    except BaseException as exc:
        g['state']['status'] = 'FAILED'
        g['state']['error'] = f'{type(exc).__name__}: {exc}'
        g['persist']()
        raise

def parent():
    assert not SCRATCH.exists(), 'scratch baseline must be absent'
    inputs = json.loads((TREE/'docs/handoffs/w05-cwp-ocr/input/inputs.json').read_text(encoding='utf-8'))
    tracked = [inputs['raw_windows_extended_path'], inputs['replay_config_read_only'], str(TREE/'config/local_ocr.json'), str(PROJECT/'config.yaml'), str(PROJECT/'config/source_catalog.yaml')]
    before = {p:digest(p) for p in tracked}
    receipt = {'status':'RUNNING','scratch_before':'absent','input_before':before,'project_network_calls':0,'project_provider_calls':0,'project_llm_calls':0,'cost_usd':0,'hard_limit_per_phase_seconds':90,'outer_hard_limit_seconds':195}
    SCRATCH.mkdir()
    started = time.monotonic()
    try:
        with (EVIDENCE/'root-real-e2e.log').open('wb') as log:
            proc = subprocess.Popen([sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),'--child'],cwd=TREE,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
            try:
                receipt['exit_code'] = proc.wait(timeout=195)
            except subprocess.TimeoutExpired:
                subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=log,stderr=log,check=False,timeout=15)
                proc.wait(timeout=15)
                receipt.update(status='HARD_TIMEOUT',exit_code=124)
        if (SCRATCH/'result.json').exists():
            result = json.loads((SCRATCH/'result.json').read_text(encoding='utf-8'))
            (EVIDENCE/'root-real-e2e-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            receipt['result_status'] = result['status']
            assert result['status']=='COMPLETED'
            assert result['baseline_match']['text_box_confidence_exact']
            assert result['baseline_match']['lines_compared']==22
            assert len(result['slide7']['recovered_lines'])==2
            assert result['replay']['exact_match']
        else:
            raise AssertionError('no result JSON')
        assert receipt['exit_code']==0
        receipt['status']='PASS'
    except BaseException as exc:
        receipt.update(status='FAIL',error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        receipt['elapsed_seconds']=round(time.monotonic()-started,3)
        receipt['input_after']={p:digest(p) for p in tracked}
        receipt['raw_config_unchanged']=receipt['input_after']==before
        receipt['scratch_peak_retained_bytes']=sum(p.stat().st_size for p in SCRATCH.rglob('*') if p.is_file())
        assert SCRATCH.resolve().parent==Path(__file__).resolve().parent and SCRATCH.name=='real-scratch'
        shutil.rmtree(SCRATCH)
        receipt['scratch_after']='absent' if not SCRATCH.exists() else 'present'
        (EVIDENCE/'root-real-e2e-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(receipt['status'],receipt['elapsed_seconds'],'seconds; scratch',receipt['scratch_after'])
        assert receipt['raw_config_unchanged'] and receipt['scratch_after']=='absent'

if __name__=='__main__':
    child() if '--child' in sys.argv else parent()
