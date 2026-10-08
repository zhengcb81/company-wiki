exec((__import__('pathlib').Path(__file__).parent/'inspect_all.py').read_text(encoding='utf-8').split('art=[]')[0])
groups={}
for c in D['evidence_claims']:
 key=(c['source_id'],c['locator'],c['excerpt'])
 groups.setdefault(key,[]).append(c)
for i,((sid,loc,ex),cs) in enumerate(groups.items()):
 print('\nGROUP',i,sid,loc)
 print('CLAIMS',[(c['claim_id'],c['target_type'],c['target_id'],c['support_type'],c.get('extracted_value')) for c in cs])
 print(ex)
print('HISTORY',json.dumps(D['historical_revenue'],ensure_ascii=False,indent=2))
for k in ['research_coverage','management_communication_coverage','management_targets','growth_driver_tree']:
 (HERE/(k+'.json')).write_text(json.dumps(D[k],ensure_ascii=False,indent=2),encoding='utf-8')
for f in ['roadshow_public_questions.json','roadshow_precollect_questions_page1.json']:
 q=json.loads((OUT/f).read_text(encoding='utf-8')); print('FORMAT',f,type(q).__name__,list(q)[:12] if isinstance(q,dict) else len(q)); print(json.dumps(q,ensure_ascii=False)[:2500])
