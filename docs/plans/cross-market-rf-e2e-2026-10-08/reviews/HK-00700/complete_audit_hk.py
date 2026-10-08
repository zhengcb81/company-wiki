import json, sys, hashlib, sqlite3, math, datetime as dt, re
from pathlib import Path
HERE=Path(__file__).resolve().parent
EX=HERE.parents[1]/'executions/HK-00700';ROOT=EX.parents[4]
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=load(EX/'manifest.json');OUT=Path(m['output_root']);i=load(OUT/'input.json');f=load(OUT/'forecast.json')
def save(n,v):(HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
if sys.argv[1]=='producer':
 c=sqlite3.connect('file:'+(ROOT/'.source_catalog/catalog.sqlite3').as_posix()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON')
 tables=[q[0] for q in c.execute("select name from sqlite_master where type='table'")]
 identifiers=[q['source_id'] for q in m['sources'][:2]]
 identifiers+=['urn:company-wiki:document:sha256:'+q.split(':')[-1] for q in identifiers]
 result={}
 for table in tables:
  if not re.fullmatch(r'[A-Za-z0-9_]+',table):continue
  cols=[q[1] for q in c.execute('pragma table_info('+table+')')]
  key=next((k for k in ['document_id','source_id'] if k in cols),None)
  if key:
   rows=[dict(q) for q in c.execute('select * from '+table+' where '+key+' in (?,?,?,?)',identifiers)]
   if rows:result[table]=rows
 c.close()
 artifact_checks=[]
 for q in result.get('artifacts',[]):
  path=Path(q['path']);artifact_checks.append(dict(artifact_id=q['artifact_id'],role=q['artifact_role'],status=q['status'],path=str(path),exists=path.is_file(),registered_sha256=q['content_sha256'],current_sha256=sha(path) if path.is_file() else None,current_bytes=path.stat().st_size if path.is_file() else None,metadata=json.loads(q['metadata_json'])))
 save('independent_current_producer_rows.json',dict(database=str(ROOT/'.source_catalog/catalog.sqlite3'),read_mode='ro/query_only',accessed_at=dt.datetime.now(dt.timezone.utc).isoformat(),rows=result,artifact_checks=artifact_checks))
 print(json.dumps(dict(tables={k:len(v) for k,v in result.items()},rows=result),ensure_ascii=False))
elif sys.argv[1]=='manual-output':
 p={q['parameter_id']:q for q in i['parameters']};calc=load(HERE/'independent_calculations.json')['manual_arithmetic']
 close=lambda a,b:math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-6)
 for q in calc['company_values']:
  r=f['consolidated_forecast'][q['scenario']];y=str(q['year'])
  assert close(r['annual_growth'][y],q['growth'])
  assert close(r['segment_subtotal'][y],q['revenue']) and close(r['adjustment_total'][y],0)
  assert close(r['annual_revenue'][y],sum(b['annual_revenue'][y] for b in r['segment_bridge']))
  assert r['adjustment_bridge']==[]
 for q in calc['paths']:
  rec=f['consolidated_forecast'][q['scenario']]
  bridge=next(b for b in rec['segment_bridge'] if b['name']==q['segment'])
  assert all(close(bridge['annual_revenue'][y],v) for y,v in q['path'].items())
  contribution=next(b for b in rec['incremental_contribution']['segments'] if b['name']==q['segment'])
  assert close(contribution['terminal_incremental_revenue'],q['path']['2028']-q['base'])
 drivers=f['growth_driver_analysis'];assert drivers['unattributed_company_adjustments']==0
 actual={q['driver_id']:q for q in drivers['drivers']}
 for q in calc['driver_allocation']:
  assert close(actual[q['driver_id']]['estimated_base_terminal_increment'],q['increment'])
  assert close(actual[q['driver_id']]['share_of_positive_driver_increment'],q['increment']/sum(d['increment'] for d in calc['driver_allocation']))
  assert close(sum(x['terminal_incremental_revenue'] for x in actual[q['driver_id']]['terminal_increment_by_segment']),q['increment'])
 assert [q['driver_id'] for q in drivers['top_drivers']]==[q['driver_id'] for q in calc['driver_allocation']]
 assert all(q['rank']==n+1 for n,q in enumerate(drivers['top_drivers']))
 assert drivers['reconciliation']['difference']==0
 assert not i.get('revenue_constraints') and not f['constraint_audit']
 assert f['probability_weighted_forecast'] is None
 report=dict(company_annual_growth_all9='PASS',all45_segment_company_bridge_cells='PASS',all15_incremental_contribution_rows='PASS',all5_driver_values_weights_shares_ranking='PASS',no_constraints_adjustments_or_probability_weighting='PASS',original_forecast_sha256=sha(OUT/'forecast.json'),registry_after_MAIN_fix=load(HERE/'independent_registry_audit-after-main-fix.json'),runtime_at_review={k:sha(Path(m['skill_root'])/k) for k in m['runtime_file_sha256']},runtime_manifest_drift=[dict(file=k,emitting_sha256=v,current_sha256=sha(Path(m['skill_root'])/k)) for k,v in m['runtime_file_sha256'].items() if sha(Path(m['skill_root'])/k)!=v])
 save('independent_complete_output_checks.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['runtime_at_review','registry_after_MAIN_fix']},ensure_ascii=False))
elif sys.argv[1]=='target-search':
 terms=['guidance','target','expect','outlook','aim','will','plan','beyond','later this year','目標','預期','展望','計劃','將']
 rows=[]
 for name in ['annual_2025','interim_2026_official','results_2q2026','corporate_overview_20260916']:
  pages=load(HERE/(name+'_review_pages.json'))
  for q in pages:
   hits=[t for t in terms if t.casefold() in q['text'].casefold()]
   if hits:rows.append(dict(document=name,page=q['page'],terms=hits,text=q['text']))
 save('independent_management_statement_search.json',dict(search_terms=terms,records=rows,meaning='Search locates contexts; no-result keyword search does not prove internet-wide absence. Relevant original contexts reviewed separately.'))
 print(json.dumps(dict(pages_with_matches=len(rows),candidate_contexts=[dict(document=q['document'],page=q['page'],terms=q['terms']) for q in rows]),ensure_ascii=False))
