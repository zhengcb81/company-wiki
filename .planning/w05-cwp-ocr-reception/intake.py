"""Read-only receipt verification; no originals copied or modified."""
import hashlib
import json
from pathlib import Path

project = Path(__file__).resolve().parents[2]
leaf = project.parent / '_harness_worktrees/w05/cwp-ocr'
delivery = leaf / 'docs/handoffs/w05-cwp-ocr'
evidence = project / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-cwp-ocr-acceptance'
evidence.mkdir(parents=True, exist_ok=True)
handoff = json.loads((delivery/'handoff.json').read_text(encoding='utf-8'))
manifest = json.loads((delivery/'manifest.json').read_text(encoding='utf-8'))
results = []
for record in manifest['files'] + handoff['changed_files'] + handoff['input_evidence']:
    p = leaf / record['path']
    raw = p.read_bytes()
    results.append({'path':record['path'], 'sha256':hashlib.sha256(raw).hexdigest(), 'bytes':len(raw), 'match':hashlib.sha256(raw).hexdigest()==record['sha256'] and ('bytes' not in record or len(raw)==record['bytes'])})
config = {}
for name in ('config.yaml','config/source_catalog.yaml'):
    config[name] = hashlib.sha256((project/name).read_bytes()).hexdigest()
out = {'status':'PASS' if all(r['match'] for r in results) else 'FAIL', 'files':results, 'production_config_before':config, 'delivery_head':'6fe9a82a6a96fe024774791e2018c882a098d512','project_provider_calls':0,'project_llm_calls':0,'project_cost_usd':0}
(evidence/'intake.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(out['status'],len(results),'entries',config)
raise SystemExit(out['status']!='PASS')
