"""Make a small explicit engineering fixture with existing native RF APIs."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
RF = ROOT.parent / '_harness_worktrees/w07/rf-model-quality'
OUT = Path(__file__).parent / 'native-input'
assert not OUT.exists(), 'Preserve previous fixture attempt'
sys.path[:0] = [str(RF / 'scripts'), str(RF / 'tests')]
from test_research_evidence_roles import calibrated_document
from revenue_core import run_forecast
from research_support_diagnostics import build_support_diagnostics

OUT.mkdir()
data = calibrated_document()
raw = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
sha = hashlib.sha256(raw).hexdigest()
values = {'native-input.json': data,
          'native-draft.json': run_forecast(data, mode='draft'),
          'native-support.json': build_support_diagnostics(data, input_sha256=sha)}
for name, value in values.items():
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
manifest = {'schema': 'w07-native-engineering-fixture/1', 'synthetic': True,
            'source_truth_verified': False, 'economic_reasonableness': 'not_evaluated',
            'rf_base': '30ddae8ed2a457c418e63b182e7d8c9230fbf3ff',
            'generation': 'calibrated_document; run_forecast(mode=draft); build_support_diagnostics',
            'files': [{'path': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                       'bytes': p.stat().st_size} for p in sorted(OUT.glob('*.json'))]}
(OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'files': len(manifest['files']), 'bytes': sum(r['bytes'] for r in manifest['files']),
                  'native_mode': 'draft', 'source_truth_verified': False}))
