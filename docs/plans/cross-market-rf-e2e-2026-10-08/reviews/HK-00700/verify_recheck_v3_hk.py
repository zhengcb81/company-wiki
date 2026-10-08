"""Final read-only artifact/report identity checks for sealed v3 recheck."""
import hashlib,json,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=load(HERE/'recheck_v3.json');m=load(HERE.parents[1]/'executions/HK-00700/manifest_v3.json');i=load(Path(m['output_root'])/'input.json')
assert r['verdict']=='FAIL' and r['subverdicts']['full_product_E2E']=='PARTIAL'
assert len(r['facts'])==378
assert {q['claim_or_parameter_id'] for q in r['facts'] if q['record_type']=='claim'}=={q['claim_id'] for q in i['evidence_claims']}
assert {q['claim_or_parameter_id'] for q in r['facts'] if q['record_type']=='parameter'}=={q['parameter_id'] for q in i['parameters']}
assert len(r['closed_findings'])==6 and len(r['remaining_findings'])==7
assert r['findings'][0]['id']=='HK-V3-R01' and r['findings'][0]['status']=='OPEN'
assert next(q for q in r['checks'] if q['id']=='V3-C07')['status']=='FAIL'
assert all(q['status'] in {'PASS','FAIL','BLOCKED','NOT_APPLICABLE'} for q in r['checks'])
for artifact in m['primary_artifacts']+[m['registry'],m['old_manifest']]:
    p=Path(artifact['absolute_path']);assert sha(p)==artifact['sha256'] and p.stat().st_size==artifact['bytes']
for q in r['artifact_integrity']['old133_checks']:
    p=Path(q['path']);assert sha(p)==q['expected'] and p.stat().st_size==q['expected_bytes']
for name,expected in r['artifact_integrity']['initial_review_sha256'].items():assert sha(HERE/name)==expected
for q in r['checks']+r['findings']:
    for reference in q.get('paths',[])+q.get('evidence',[]):assert Path(reference.split('#',1)[0]).exists(),reference
pairs=collections.defaultdict(list)
for line in (HERE/'commands/index.jsonl').read_text(encoding='utf-8').splitlines():
    q=json.loads(line)
    if 'hk-v3' in q['label'].lower():pairs[q['id']].append(q)
for key,rows in pairs.items():
    if len(rows)==1:
        assert rows[0]['label']=='hk-v3-final-recheck-integrity' and rows[0]['event']=='start'
        continue
    assert len(rows)==2 and [q['event'] for q in rows]==['start','finish']
    for q in rows[-1]['outputs'].values():assert sha(q['path'])==q['sha256'] and Path(q['path']).stat().st_size==q['byte_size']
summary=dict(serialization='PASS',initial_review_unchanged=True,old133_unchanged=True,v3_four_artifacts_registry_unchanged=True,checks=len(r['checks']),facts=len(r['facts']),closed_findings=r['closed_findings'],remaining_findings=[q['id'] for q in r['remaining_findings']],verdict=r['verdict'],model_quality_acceptance=r['subverdicts']['model_quality_acceptance'],full_product_E2E=r['subverdicts']['full_product_E2E'],sha256={'recheck_v3.md':sha(HERE/'recheck_v3.md'),'recheck_v3.json':sha(HERE/'recheck_v3.json')})
(HERE/'recheck_v3_integrity.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
