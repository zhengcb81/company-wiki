"""Read-only additional observations against ROOT candidate; temporary inputs."""
from pathlib import Path
import importlib.util
import json
import tempfile

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w08-root/audit')
spec = importlib.util.spec_from_file_location('postfix_package', ROOT/'tests/test_w08_review_evidence.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def probe(name, mutate):
    with tempfile.TemporaryDirectory(prefix='w08-postfix-', dir=Path(__file__).parent) as temp:
        builder = module.PackageBuilder(temp)
        run = builder.build()
        # Builder's originally declared capture output must really exist.
        for role in ('storage','fetch','process','analyst'):
            output = run/'roles'/role/'commands'/f'{role}-capture'/'stdout.txt'
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text('synthetic child output\n', encoding='utf8')
        mutate(builder,run)
        result = builder.reconcile(run)
        return {'case':name,'identity':result['identity'], 'storage_report':result['role_reports']['storage'],
                'storage_events':result['events']['storage'], 'unchecked':result['unchecked'],
                'numeric':result['numeric_reconciliation'], 'quality_status':result['quality_status']}

def events(run, mutation):
    p=run/'roles/storage/events.jsonl'
    values=[json.loads(line) for line in p.read_text(encoding='utf8').splitlines()]
    mutation(values)
    p.write_text(''.join(json.dumps(v)+'\n' for v in values), encoding='utf8')

def unknown_report(b,r):
    (r/'reports/attempt-1/storage.json').write_text('{}', encoding='utf8')

def numeric_date(b,r):
    (r/'execution/date.txt').write_text('Published 2026-10-13\n',encoding='utf8')
    b.payload['numeric_coverage']['verified'][0]['recompute'].update(artifact='execution/date.txt',locator='line 1')

rows=[probe('baseline',lambda b,r:None),
      probe('unknown_actual_report_fields',unknown_report),
      probe('legacy_events_without_run_id',lambda b,r:events(r,lambda vs:[v.pop('run_id') for v in vs])),
      probe('old_explicit_attempt_events',lambda b,r:events(r,lambda vs:[v['data'].update(review_attempt='old-attempt') for v in vs])),
      probe('date_line_is_not_recompute',numeric_date),
      probe('capture_id_pair_fixed',lambda b,r:events(r,lambda vs:vs[1]['data'].update(capture_id='other'))),
      probe('stale_run_event_fixed',lambda b,r:events(r,lambda vs:[v.update(run_id='old-run') for v in vs]))]
out=Path(__file__).with_name('postfix-observations.json')
out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
for row in rows:
    print(json.dumps({'case':row['case'],'binding':row['storage_report']['binding_status'],
        'matched':row['storage_events']['matched_calls'],'unchecked':row['unchecked'],
        'numeric':row['numeric']['recompute_rows_observed'],'quality':row['quality_status']},ensure_ascii=False))
