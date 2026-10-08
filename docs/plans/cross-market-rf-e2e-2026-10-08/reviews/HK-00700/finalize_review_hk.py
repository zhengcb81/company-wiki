"""Check reviewer serialization and final artifact identity without changing execution."""
from pathlib import Path
import collections, hashlib, json

HERE = Path(__file__).resolve().parent
load = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
review = load(HERE / 'review.json')
manifest = load(HERE.parents[1] / 'executions/HK-00700/manifest.json')
input_doc = load(Path(manifest['output_root']) / 'input.json')
required = {'schema_version', 'reviewer_agent_id', 'company', 'reviewed_at', 'reviewed_runtime', 'executed_agent_id', 'verdict', 'checks', 'facts', 'independent_calculations', 'missing_steps', 'findings', 'artifact_integrity', 'limits', 'command_index'}
assert required <= set(review)
assert review['verdict'] == 'FAIL'
assert len(review['checks']) == 33
assert len({q['id'] for q in review['checks']}) == 33
assert {q['status'] for q in review['checks']} <= {'PASS', 'FAIL', 'NOT_APPLICABLE', 'BLOCKED'}
claim_rows = [q for q in review['facts'] if q['record_type'] == 'claim']
param_rows = [q for q in review['facts'] if q['record_type'] == 'parameter']
assert {q['claim_or_parameter_id'] for q in claim_rows} == {q['claim_id'] for q in input_doc['evidence_claims']}
assert {q['claim_or_parameter_id'] for q in param_rows} == {q['parameter_id'] for q in input_doc['parameters']}
assert len(claim_rows) == 69 and len(param_rows) == 51
assert len(review['facts']) == 145
for history in input_doc['historical_revenue']:
    matching = [q for q in claim_rows if q['claim_or_parameter_id'] in history['claim_ids']]
    assert len(matching) == 1 and matching[0]['independent_value'] == history['value']
    assert matching[0]['status'] == 'PASS'
assert len(review['findings']) == 13
assert sum(q['status'] == 'open' for q in review['findings']) == 12
assert review['findings'][-1]['status'] == 'resolved_by_MAIN_independently_reverified'
missing_references = []
for item in review['checks'] + review['findings']:
    for reference in item.get('evidence', []) + item.get('paths', []):
        base = reference.split('#', 1)[0]
        if not Path(base).exists():
            missing_references.append(reference)
assert not missing_references, missing_references
emitted = []
for record in review['artifact_integrity']['emitting_artifacts']:
    path = Path(record['path'])
    actual = digest(path)
    assert actual == record['expected'] and path.stat().st_size == record['expected_bytes'], str(path)
    emitted.append({'path': str(path), 'sha256': actual, 'byte_size': path.stat().st_size})
protected = []
protection = load(HERE / 'protected_review_inputs.json')
before = protection['before']['protected']
runtime_paths = {q['path'] for q in protection['current'] if q['runtime_file']}
for record in before:
    path = Path(record['path'])
    if record['path'] in runtime_paths:
        continue
    actual = digest(path)
    assert actual == record['sha256'] and path.stat().st_size == record['bytes'], str(path)
    protected.append({'path': str(path), 'sha256': actual})
assert len(protected) == 41
events = [json.loads(line) for line in (HERE / 'commands/index.jsonl').read_text(encoding='utf-8').splitlines()]
by_id = collections.defaultdict(list)
for event in events:
    by_id[event['id']].append(event)
completed = []
active = []
for key, pair in by_id.items():
    if len(pair) == 1:
        assert pair[0]['event'] == 'start' and pair[0]['label'] == 'finalize-independent-hk-review'
        active.append(key)
        continue
    assert len(pair) == 2 and [q['event'] for q in pair] == ['start', 'finish']
    for info in pair[-1]['outputs'].values():
        path = Path(info['path'])
        assert digest(path) == info['sha256'] and path.stat().st_size == info['byte_size']
    completed.append({'id': key, 'returncode': pair[-1]['returncode']})
result = dict(serialization_status='PASS', checks=len(review['checks']), facts=len(review['facts']), findings=len(review['findings']), open_findings=12, protected_raw_config=len(protected), emitting_artifacts=len(emitted), completed_review_command_pairs=len(completed), active_finalization_command=active, emitted=emitted, protected=protected, commands=completed, report_sha256={'review.md': digest(HERE / 'review.md'), 'review.json': digest(HERE / 'review.json')})
(HERE / 'final_review_integrity.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({q: result[q] for q in ['serialization_status', 'checks', 'facts', 'findings', 'open_findings', 'protected_raw_config', 'emitting_artifacts', 'completed_review_command_pairs', 'report_sha256']}, ensure_ascii=False))
