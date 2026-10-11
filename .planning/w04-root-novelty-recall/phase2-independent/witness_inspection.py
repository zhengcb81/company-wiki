"""Inspect ROOT's frozen six-result evidence only; never parse originals again."""
import gzip
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
PLAN=OUT.parent
TREE=Path(r"C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki")
FREEZE=TREE/'.planning/w04-root-novelty-recall/phase2-real-recall/product-freeze.json'
EXPECTED='2db879e8744fe646caa2a44a93d89ef4b89dbbf65f5fffe4549ed4d7d21b69ed'
EVIDENCE=PLAN/'native-novelty-six-quality-v2.json.gz'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def textsha(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))

if (OUT/'witness-inspection.json').exists():raise RuntimeError('Fresh inspection only')
assert sha(FREEZE)==EXPECTED
freeze=read(FREEZE)
products_before={p:sha(TREE/p) for p in freeze['products']}
source_sha=sha(EVIDENCE)
data=json.loads(gzip.decompress(EVIDENCE.read_bytes()))
annual=next(row for row in data['items'] if row['key']=='cn-annual')
spans={row['locator']:row for row in annual['selected_spans']}
groups={row['group_id']:row for row in annual['complete_selected_groups']}
records=[]
for name,claim in data['bound_fact_recall'].items():
    for w in claim['witnesses']:
        members=[spans[loc] for loc in w['locators']]
        ordered=sorted(members,key=lambda row:(row['coordinates']['page_number'],row['coordinates']['paragraph_index']))
        joined=''.join(row['raw_text'] for row in ordered)
        grouped=[row for row in annual['selected_spans'] if 'group:'+row['structured_value'].get('selection_group_id','')==w['group_id']]
        source_ids={row['source_id'] for row in members}
        native_group=groups[w['group_id']]
        ok=(claim['complete'] and len(source_ids)==1 and source_ids=={'urn:company-wiki:source:sha256:'+annual['sha256']}
            and {row['locator'] for row in grouped}==set(w['locators']) and w['span_cost']==len(grouped)
            and w==native_group and joined==w['raw_text'] and textsha(joined)==w['raw_text_sha256'])
        records.append({'name':name,'pass':bool(ok),'group_id':w['group_id'],'locators':w['locators'],
            'span_cost':w['span_cost'],'raw_text_sha256':w['raw_text_sha256'],'raw_text':joined,
            'boundary': {'lpcvd_shipments':'Specific LPCVD shipments exceed three hundred reactors; repeat orders refer only to some new equipment, not LPCVD exclusively.',
                'tungsten_validation_and_repeat_orders':'CVD/HAR/ALD tungsten series shares completed customer validation and repeat production orders.',
                'prismo_pd5_new_facts':'PD5 supports up to four chambers and switching six/eight inches, with completed line validation and repeat orders.',
                'supplier_lead_time_constraint':'Multi-supplier mitigation; lead-time effect is conditional on continuing upstream capacity constraints.'}[name]})
assert len(records)==4 and all(row['pass'] for row in records)
declarations=[{'key':row['key'],'raw_sha_unchanged':row['sha256']==row['raw_sha_after'],
    'legacy_matches_frozen':row['legacy_matches_frozen'],'selected':row['selected_count'],'cap':row['selection_limit'],
    'omitted_partition':row['omitted_count']==row['candidate_count']-row['selected_count']} for row in data['items']]
assert len(declarations)==6 and all(row['raw_sha_unchanged'] and row['legacy_matches_frozen'] and row['selected']<=row['cap']
    and row['omitted_partition'] for row in declarations)
assert sha(EVIDENCE)==source_sha and sha(FREEZE)==EXPECTED and products_before=={p:sha(TREE/p) for p in freeze['products']}
inspection={'schema_version':'w04-independent-root-witness-inspection/1','status':'PASS_EVIDENCE_BINDING_ONLY',
    'evidence_path':str(EVIDENCE),'evidence_sha256':source_sha,'product_freeze_sha256':EXPECTED,
    'root_status':data['status'],'four_witnesses':records,'six_report_declarations':declarations,
    'scope':'Read compressed ROOT result only; original PDF/TXT/HTML bytes, parser and selector not rerun. Four witnesses matched complete selected source groups in native coordinate order and text SHA.',
    'provider_network_LLM_calls':0,'fees_usd':0,'root_evidence_and_products_unchanged':True,
    'limitations':['Independent raw-document rehash/full-six replay not performed; ROOT supplied frozen execution evidence.',
                   'Summary quality, logical entailment of generated summaries and downstream RF remain not_evaluated.']}
(OUT/'witness-inspection.json').write_text(json.dumps(inspection,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report=read(OUT/'report.json')
report['witness_inspection']='witness-inspection.json'
report['witness_inspection_status']=inspection['status']
report['witness_checks_passed']=4
report['root_real_six_status']=data['status']
report['scope']='17 pure engineering checks plus read-only inspection of four whole-group witnesses in frozen ROOT six-result evidence; no 375/six-original rerun'
report['residual'][0]='ROOT fixed six-result report is PASS and four selected witnesses were independently evidence-bound; generated summaries and RF still not evaluated.'
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md=(OUT/'report.md').read_text(encoding='utf-8')
md=md.replace('ROOT must independently replay fixed real six-original native checkpoints and full ordered0.7.1 package hashes.',
    'ROOT has completed the unchanged fixed six-original replay with PASS; this reviewer inspected its saved evidence without rerunning originals.')
md+='''
## Read-only ROOT witness reception

ROOT's four complete annual source groups were independently matched to all their selected spans in native page/paragraph order, one source SHA and one group each; concatenated raw text and SHA match. These are original page41 LPCVD-specific >three hundred shipments, page44 CVD/HAR/ALD tungsten-series completed validation/repeat-production orders, page56 PRISMO PD5 up-to-four chambers/six-or-eight-inch switching/completed validation/repeat orders, and page62 multi-supplier mitigation with conditional lead-time effects. No cross-group substring, thin-film total substitution, LPCVD-specific repeat-order invention or plan-as-completion is accepted.

Saved ROOT six-result declarations retain all six raw-before/after SHA, legacy fingerprints, caps and omitted counts; originals were not reopened or reprocessed by this reviewer. The compressed result and seven frozen products remained unchanged. See `witness-inspection.json` for exact group locators, text SHA and scope. Summary and research remain not evaluated. Old FAIL attempt evidence remains preserved.
'''
(OUT/'report.md').write_text(md,encoding='utf-8')
manifest={'schema_version':'w04-phase2-independent-engineering-freeze/1','state':'FINAL_STOP','verdict':report['verdict'],
    'files':[{'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='manifest.json']}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'engineering':report['verdict'],'engineering_checks':17,'witness_binding_checks':4,
    'ROOT_six_status':data['status'],'manifest_sha256':sha(OUT/'manifest.json')},ensure_ascii=False))
