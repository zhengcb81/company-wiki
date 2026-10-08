"""Read-only command/output integrity audit; not a substitute for fact review."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
rows = []
for ledger in sorted(ROOT.rglob('index.jsonl')):
    records = [json.loads(line) for line in ledger.read_text(encoding='utf-8').splitlines() if line]
    starts = {}
    finishes = {}
    issues = []
    for record in records:
        group = starts if record['event'] == 'start' else finishes
        ident = record['id']
        if ident in group:
            issues.append({'id': ident, 'issue': 'duplicate event'})
        group[ident] = record
    for ident, record in finishes.items():
        if ident not in starts:
            issues.append({'id': ident, 'issue': 'missing start'})
        else:
            for key in ('command', 'cwd', 'label'):
                if record[key] != starts[ident][key]:
                    issues.append({'id': ident, 'issue': f'changed {key}'})
        for kind, output in record['outputs'].items():
            path = Path(output['path'])
            try:
                content = path.read_bytes()
                if len(content) != output['byte_size'] or hashlib.sha256(content).hexdigest() != output['sha256']:
                    issues.append({'id': ident, 'issue': f'{kind} content/size mismatch'})
            except OSError as exc:
                issues.append({'id': ident, 'issue': f'{kind} {type(exc).__name__}'})
    unfinished = sorted(set(starts) - set(finishes))
    rows.append({'ledger': str(ledger), 'started': len(starts), 'finished': len(finishes),
                 'failed_commands': sum(record['returncode'] != 0 for record in finishes.values()),
                 'unfinished_ids': unfinished, 'integrity_issues': issues})
report = {'schema_version': '1.0', 'ledgers': rows,
          'integrity_issue_count': sum(len(row['integrity_issues']) for row in rows),
          'unfinished_count': sum(len(row['unfinished_ids']) for row in rows),
          'scope': 'All recorded commands; exits !=0 are retained evidence, not log-integrity failures.'}
(ROOT / 'command_integrity.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'ledgers': len(rows), 'integrity_issues': report['integrity_issue_count'],
                  'unfinished': report['unfinished_count']}, ensure_ascii=False))
