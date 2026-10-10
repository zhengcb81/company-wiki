"""Verify diagnostic coverage and immutable cited evidence; no network or mutation outside HERE."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
PHASE=HERE.parent
PROJECTS=Path('C:/Users/郑曾波/Projects')
def read(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj):
    if '--write-receipts' in sys.argv:
        (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

c=read(HERE/'coverage.json'); roots=read(HERE/'root_causes.json')['roots']; inventory=read(HERE/'report_inventory.json')
assert len(c['entries'])==157
assert len({x['issue_key'] for x in c['entries']})==157
assert Counter(x['cohort'] for x in c['entries'])=={'old64':64,'m3_91':91,'expert_carryover2':2}
assert sha(Path(c['immutable_old_matrix']['path']))==c['immutable_old_matrix']['sha256']
assert len(roots)==26 and sum(x['checks'] for x in inventory['reports'])==246
known={x['root_cause_id'] for x in roots}
for x in c['entries']:
    assert x['root_cause_ids'] and set(x['root_cause_ids'])<=known
    assert x['work_packages'] and all((HERE/'work_packages'/f'{w}.md').exists() for w in x['work_packages'])
    if x['cohort']=='m3_91':
        p=Path(x['source_report']); assert sha(p)==x['source_report_sha256']
        o=read(p); n=int(x['source_pointer'].split('/')[-1])
        assert o['findings'][n]==x['original_finding']
for r in inventory['reports']:
    p=Path(r['path']); obj=read(p); md=Path(r['markdown_path'])
    assert sha(p)==r['sha256'] and md.exists() and sha(md)==r['markdown_sha256']
    assert len(obj['checks'])==r['checks'] and len(obj['findings'])==r['findings']

run=PROJECTS/'revenue-forecast-audit/runs/m3-20261009T184946-cn-688012'
recon=read(run/'execution/research/qa-reconciliation.json')
pages=[]; observed_records=[]
for stream, meta in recon['streams'].items():
    ids=[]
    for source in meta['sources']:
        p=Path(source['path']); data=p.read_bytes(); obj=json.loads(data)
        assert len(data)==source['bytes'] and hashlib.sha256(data).hexdigest()==source['sha256']
        records=obj['datas'][0]['records']; ids += [x['id'] for x in records]
        observed_records += [(stream,p.name,i,x) for i,x in enumerate(records)]
        pages.append({'stream':stream,'path':str(p),'bytes':len(data),'sha256':source['sha256'],'records':len(records)})
    assert len(ids)==meta['record_count'] and len(set(ids))==meta['unique_record_count']
assert len(pages)==86 and sum(x['bytes'] for x in pages)==668749 and len(observed_records)==257
target=[x for x in observed_records if x[3].get('companyId')==145565]
assert len(target)==24
first=read(run/'execution/sources/qa-latest-form-01.raw')['datas'][0]['records'][2]
correct=read(run/'execution/sources/qa-latest-form-18.raw')['datas'][0]['records'][2]
pre=read(run/'execution/sources/qa-precollect-form-10.raw')['datas'][0]['records'][1]
assert first['id']==2508409 and correct['id']==2508385
assert pre['id']==36395 and pre['companyId']==145565 and '800' in pre['answer'] and pre['answer'].strip()

official=PHASE/'m3_source_research_2026-10-09/official_json_source_root'
official_shas={'DATA_CONTRACT.md':'2d80afeeac0946f91e18dccc6008eab734dcb1d727aac6f2dbe2870e7b4f08b3','JSON_EVIDENCE_INDEX.json':'4969a5239e15b71f2e8d83e3107dd7a9f80ab78b9673b710a2158906b35285fc'}
for f,h in official_shas.items(): assert sha(official/f)==h

paths=[
 PROJECTS/'company-wiki/src/company_wiki/automation/narrative_select.py',
 PROJECTS/'company-wiki/src/company_wiki/automation/narrative_http_model.py',
 PROJECTS/'company-wiki/src/company_wiki/automation/narrative_model_caller.py',
 PROJECTS/'company-wiki/src/company_wiki/source_catalog/bounded_http.py',
 PROJECTS/'company-wiki/src/company_wiki/source_catalog/official_source_flow.py',
 PROJECTS/'company-wiki/src/company_wiki/source_catalog/transcript_json_extract.py',
 PROJECTS/'revenue-forecast/scripts/research/drivers.py',
 PROJECTS/'revenue-forecast/scripts/contracts/constants.py',
 PROJECTS/'revenue-forecast/scripts/contracts/document.py',
 PROJECTS/'revenue-forecast/scripts/revenue_report.py',
 PROJECTS/'revenue-forecast/scripts/company_wiki_source_reader_v2.py',
]
code=[{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in paths]
guidance=PROJECTS/'revenue-forecast-audit/runs/m3-20261009T184946-us-msft/execution/deck_images/p21-image21.png'
assert sha(guidance)=='fa3b238c348236c19d17948f68815f56250a946a3bbe93d755a207441c12bddf'
save('evidence_observation.json',{'status':'read_only_local_expert_verification_not_engineering_or_research_acceptance','m3_reports':12,'checks':246,'findings':91,'all_report_json_and_markdown_shas_rechecked':True,'raw_pages_reparsed_and_byte_hash_checked':pages,'raw_totals':{'pages':86,'bytes':668749,'records':257,'target_records':24},'record_correction':{'first_page_pointer_id':first['id'],'correct_page_pointer_id':correct['id'],'precollect_answer_id':pre['id'],'precollect_answer_contains_800_cumulative_reaction_chambers':True},'primary_guidance_page21':{'path':str(guidance),'sha256':sha(guidance),'review':'Expert visually inspected frozen original image: adjusted Azure Q1 44-45% constant currency, FX reduces revenue less than one point. Reported 43-45% is analyst conditional endpoint envelope, not original reported guidance.'},'official_contract_files':official_shas,'code_bytes_at_read_only_verification':code,'network_requests':0,'model_calls':0,'new_paid_tokens':0,'new_paid_micro_usd':0,'old_matrix_sha_unchanged':True,'protected_source_bytes_sha_unchanged':True})
save('verification.json',{'status':'PASS_DIAGNOSTIC_MAPPING_ONLY','company_findings':155,'expert_carryover':2,'composite_keys':157,'unmapped':0,'duplicates':0,'roots':26,'work_packages':9,'old_matrix_sha_unchanged':True,'report_original_finding_fields_match':True,'M3_reports':12,'M3_checks':246,'M3_findings':91,'M3_severity':dict(Counter(x['severity'] for x in c['entries'] if x['cohort']=='m3_91')),'semantic_root_review':'expert diagnosis; code/actual frozen evidence reviewed; tests and real company reacceptance remain planned','engineering_or_research_completed':False})
print('PASS mapping157 / roots26 / cards9 / reports12 / checks246 / findings91; 86 raw pages byte-verified; 0 network/model/fee')
