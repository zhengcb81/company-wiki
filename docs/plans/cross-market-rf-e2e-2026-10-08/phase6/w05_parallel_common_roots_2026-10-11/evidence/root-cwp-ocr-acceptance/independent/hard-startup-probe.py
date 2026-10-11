"""One independent real spawn deadline probe; no model/provider/raw access."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
tree = Path(sys.argv[1]).resolve()
evidence = Path(__file__).resolve().parent
sys.path.insert(0, str(tree / 'src'))
sys.path.insert(0, str(tree / 'tests/document_normalization'))
from company_wiki._process_tree import pid_is_alive
from company_wiki.document_normalization import NormalizationLimitError
from company_wiki.document_normalization import isolated_ocr as boundary
from test_isolated_ocr import NativeFake, cfg

owned = Path(tempfile.mkdtemp(prefix='owned-hard-startup-', dir=evidence))
assert owned.resolve().parent == evidence
receipt = {'schema':'root-w05-ocr-independent-hard-startup/1',
    'tree':str(tree), 'platform':sys.platform,
    'timeout_seconds':0.05, 'provider_calls':0, 'model_calls':0,
    'initial_owned_root':'absent before mkdtemp', 'owned_root':str(owned)}
processes = []
actual_popen = subprocess.Popen

def record_popen(*args, **kwargs):
    child = actual_popen(*args, **kwargs)
    processes.append(child)
    return child

adapter = None
try:
    config = cfg(owned)
    started = time.monotonic()
    adapter = boundary.IsolatedOCRAdapter(config, deadline=started+0.05,
        scratch_dir=owned, _backend_factory=NativeFake)
    boundary.subprocess.Popen = record_popen
    error = None
    try:
        adapter.validate_environment()
    except NormalizationLimitError as exc:
        error = exc.limit_name
    elapsed = time.monotonic()-started
    receipt.update({'error_limit_name':error,'elapsed_seconds':elapsed,
        'spawned_bootstrap_pids':[p.pid for p in processes],
        'all_bootstraps_reaped':all(p.poll() is not None and not pid_is_alive(p.pid) for p in processes),
        'backend_started':(owned/'backend-init').exists(),
        'remaining_proxy_scratch':[p.name for p in owned.glob('cwp-ocr-*')],
        'adapter_worker_pid':adapter.worker_pid,
        'configured_identity_unchanged':adapter.identity_manifest == config.identity_manifest
            and adapter.fingerprint==config.fingerprint})
    assert error == 'deadline', receipt
    assert processes, 'The real bootstrap must have spawned; expired-before-spawn is not this test'
    assert elapsed < 1.0, receipt
    assert receipt['all_bootstraps_reaped'] and not receipt['remaining_proxy_scratch'], receipt
    assert adapter.worker_pid is None and receipt['configured_identity_unchanged'], receipt
    receipt['status']='PASS'
except AssertionError as exc:
    receipt.update({'status':'FAIL','detail':str(exc)})
except Exception as exc:
    receipt.update({'status':'HARNESS_ERROR','detail':repr(exc)})
finally:
    boundary.subprocess.Popen = actual_popen
    if adapter is not None:
        adapter.close()
    assert owned.resolve().parent == evidence and owned.name.startswith('owned-hard-startup-')
    shutil.rmtree(owned)
    receipt['owned_root_restored'] = not owned.exists()
    paths=('src/company_wiki/document_normalization/isolated_ocr.py',
        'src/company_wiki/source_catalog/narrative_normalization.py',
        'src/company_wiki/document_normalization/ocr_composition.py')
    receipt['source_sha256']={p:hashlib.sha256((tree/p).read_bytes()).hexdigest() for p in paths}
    (evidence/'hard-startup-result.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
sys.exit(0 if receipt['status']=='PASS' else 1)
