"""Strong formal checks plus independent arithmetic and complete original excerpt match."""
from pathlib import Path
import datetime,hashlib,json,math,os,re,sys
ROOT=Path(__file__).resolve().parent
OLD=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/CN-688012');OUT=OLD/'v3'
SKILL=Path('C:/Users/郑曾波/.agents/skills/revenue-forecast')
sys.path.insert(0,str(SKILL/'scripts'))
from revenue_report import validate_published_forecast,render_markdown
from revenue_backtest import validate_snapshot
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sh(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def eq(a,b):assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-8),(a,b)
def norm(x):return re.sub(r'\s+','',x)
d=read(OUT/'input.json');r=read(OUT/'forecast.json');old=read(OLD/'forecast.json')
validate_published_forecast(r,d)
assert (OUT/'forecast.md').read_bytes()==render_markdown(r).encode('utf-8')
snap=read(OUT/'snapshot.json');validate_snapshot(snap);assert snap['input_document']==d
economic={k:v for k,v in r.items() if k not in {'publication_receipt','result_sha256'}}
assert {k:v for k,v in snap['forecast_result'].items() if k not in {'publication_receipt','result_sha256'}}==economic
ps={p['parameter_id']:p for p in d['parameters']};ss={s['name']:s for s in r['segments']};arithmetic=[]
for sc in ['low','base','high']:
    previous=r['base_revenue']
    for y in [2026,2027,2028]:
        e=ps[f'equipment_units_{sc}_{y}']['value']*ps[f'equipment_unit_revenue_{sc}_{y}']['value']
        residual=ps[f'aftermarket_revenue_{sc}_{y}']['value'];cmp=ps[f'cmp_revenue_{sc}_{y}']['value']
        for name,v in [('Equipment',e),('NonEquipmentResidual',residual),('CMP',cmp)]:eq(v,ss[name]['scenarios'][sc]['recognized_revenue'][str(y)])
        total=e+residual+cmp;path=r['consolidated_forecast'][sc]
        eq(total,path['annual_revenue'][str(y)]);eq(total,old['consolidated_forecast'][sc]['annual_revenue'][str(y)])
        eq(total/previous-1,path['annual_growth'][str(y)]);previous=total
        arithmetic.append(dict(scenario=sc,year=y,independent_sum=total,engine_total=path['annual_revenue'][str(y)],numeric_assumptions_identical_v2=True,status='PASS'))
    eq((previous/r['base_revenue'])**(1/3)-1,path['cagr']);eq(previous-r['base_revenue'],path['incremental_revenue'])
for y in [2026,2027,2028]:
    vals=[r['consolidated_forecast'][sc]['annual_revenue'][str(y)] for sc in ['low','base','high']];assert vals==sorted(vals)
assert all(r['consolidated_forecast'][sc]['annual_revenue']['2026']>6691.28732767 for sc in ['low','base','high'])
assert ps['cmp_base']['kind']=='analyst_assumption';eq(ps['equipment_base']['value']+ps['aftermarket_base']['value']+ps['cmp_base']['value'],r['base_revenue'])
assert r['publication_receipt']['attestation_status']=='unattested'
registry=Path(os.environ['REVENUE_PUBLICATION_REGISTRY']);assert registry==OUT/'publications.jsonl' and registry.exists()
sources={s['source_id']:s for s in d['sources']}
texts={d['sources'][0]['source_id']:'\n'.join(p['text'] for p in read(OLD/'annual2025_pages.json')),d['sources'][1]['source_id']:'\n'.join(p['text'] for p in read(OLD/'half2026_pages.json')),'semi_wfe_20260714':(OLD/'semi_web_open_snapshot.json').read_text(encoding='utf-8'),'amec_sse_results_qa_20260910':json.dumps(read(OLD/'roadshow_public_questions.json'),ensure_ascii=False)}
for receipt in read(ROOT/'announcements_v3_receipts.json'):
    texts['amec_cninfo_'+receipt['announcement_id']]='\n'.join(p['text'] for p in read(receipt['pages_path']))
checks=[]
for c in d['evidence_claims']:
    source=sources[c['source_id']]
    assert c['content_sha256']==source['capture']['snapshot_sha256']
    assert c['capture_receipt_sha256']==source['capture']['receipt_sha256']
    assert hashlib.sha256(c['excerpt'].strip().encode('utf-8')).hexdigest()==c['excerpt_sha256']
    # JSON official Q&A escapes newlines; compare exact answer payload separately.
    if c['source_id']=='amec_sse_results_qa_20260910':
        payload=read(OLD/'roadshow_public_questions.json');body='\n'.join(str(x) for q in payload['datas'][0]['records'] for x in q.values())
    else:body=texts[c['source_id']]
    assert norm(c['excerpt']) in norm(body),(c['claim_id'],'original exact-normalized excerpt missing')
    checks.append(dict(claim_id=c['claim_id'],source_id=c['source_id'],locator=c['locator'],status='PASS original normalized-whitespace exact substring',excerpt_sha256=c['excerpt_sha256']))
protected=[]
for p in read(ROOT/'v3_protected_v2.json')['protected']:
    assert sh(p['path'])==p['sha256'] and Path(p['path']).stat().st_size==p['bytes'],p['path']
    protected.append(dict(p,unchanged=True))
receipt=dict(schema_version='1.0',timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS deterministic execution checks; independent reviewer pending',strong_input_required_validation=True,render_byte_identical=True,snapshot_validated=True,snapshot_input_exact=True,arithmetic=arithmetic,all_claim_original_match=checks,claims_count=len(checks),old_v2_artifacts_protected=protected,publication_registry=str(registry),attestation_status='unattested',gaps={'CWPWorker':'BLOCKED/not_run','IR_original_DOCX':'BLOCKED/not_obtained','equity_incentive_target_numeric_schedule':'not_obtained; company mentions existence; no numeric fabrication','residual_quantitative_calibration':'unknown','phaseII_local_sales_target':'ambiguous period/mismatch/unmodeled'})
(ROOT/'formal_verification_v3.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':receipt['status'],'claims_original_checked':len(checks),'arithmetic_rows':len(arithmetic),'v2_protected_unchanged':True},ensure_ascii=False))
