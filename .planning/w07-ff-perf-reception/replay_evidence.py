"""Replay accepted synthetic request/response hashes in an isolated temp dir."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--ff-project',type=Path,required=True)
args = parser.parse_args()
sys.path.insert(0,str(args.ff_project/'tools/offline_contract_matrix'))
from oracle import audit
plan = Path(__file__).resolve().parent
summary = json.loads((plan/'acceptance.json').read_text(encoding='utf-8'))
with tempfile.TemporaryDirectory(prefix='root-w07-replay-') as scratch:
    root = Path(scratch)
    with zipfile.ZipFile(plan/'offline-evidence.zip') as z:
        for entry in z.infolist():
            if not (root/entry.filename).resolve().is_relative_to(root.resolve()):
                raise ValueError('archive path escaped isolated replay')
        z.extractall(root)
    attempt = root/summary['final_attempt']
    report = json.loads((attempt/'report.json').read_text(encoding='utf-8'))
    report['evidence_root'] = str(attempt/'artifacts')
    findings = [f.to_dict() for f in audit(report)]
    print(json.dumps({'cases':len(report['cases']),'finding_count':len(findings),'findings':findings[:3]}))
    if findings:
        raise SystemExit(1)
