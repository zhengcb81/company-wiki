"""The retained-observation diagnostic must not overwrite author evidence."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def test_standalone_report_uses_package_imports_and_owned_output(tmp_path):
    root=Path(__file__).resolve().parents[3]
    original=root/'docs/plans/du4-table-2026-10-15/results/real-packet-bindings-report.json'
    digest=hashlib.sha256(original.read_bytes()).digest()
    output=tmp_path/'actual.json'
    completed=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('report_real_packet.py')),
                              '--output',str(output)],cwd=root,
                             env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},
                             capture_output=True,timeout=20)
    assert completed.returncode==0,completed.stderr.decode(errors='replace')
    assert json.loads(output.read_text(encoding='utf8'))['totals']=={'bound':34,'ambiguous':7,'unavailable':0}
    assert hashlib.sha256(original.read_bytes()).digest()==digest
