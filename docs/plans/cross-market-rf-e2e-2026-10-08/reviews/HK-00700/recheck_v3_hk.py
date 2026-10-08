"""Independent v3 dependency-closure audit. Writes reviewer outputs only."""
import collections, datetime as dt, hashlib, json, re, sqlite3, sys, os, subprocess, math
from pathlib import Path
sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
EX = HERE.parents[1] / 'executions/HK-00700'
load = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
save = lambda n, v: (HERE / n).write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding='utf-8')
m = load(EX / 'manifest_v3.json'); OUT = Path(m['output_root'])
old_m = load(EX / 'manifest.json'); old_out = Path(old_m['output_root'])
i = load(OUT / 'input.json'); old_i = load(old_out / 'input.json')
if sys.argv[1] == 'ledger':
    repair = load(EX / 'repair_v3.json'); steps = load(EX / 'skill_step_matrix_v3.json'); declared_facts = load(EX / 'fact_checks_v3.json')
    immutable = load(EX / 'after_v3_integrity.json')['checks']
    protected = []
    for record in immutable:
        p = Path(record['path']); actual = sha(p)
        protected.append(dict(path=str(p), expected=record['sha256'], current=actual, byte_size=p.stat().st_size, expected_bytes=record['bytes'], valid=actual == record['sha256'] and p.stat().st_size == record['bytes']))
    assert len(protected) == 133 and all(q['valid'] for q in protected)
    artifacts = [dict(path=q['absolute_path'], expected=q['sha256'], current=sha(q['absolute_path']), expected_bytes=q['bytes'], current_bytes=Path(q['absolute_path']).stat().st_size) for q in m['primary_artifacts'] + [m['registry'], m['old_manifest']]]
    assert all(q['expected'] == q['current'] and q['expected_bytes'] == q['current_bytes'] for q in artifacts)
    runtimes = load(EX / 'v3_runtime_inventory.json')
    pairs = collections.defaultdict(list)
    for line in Path(m['command_index']).read_text(encoding='utf-8').splitlines():
        q = json.loads(line)
        if 'v3' in q.get('label', '').lower(): pairs[q['id']].append(q)
    commands = []
    for key, pair in pairs.items():
        assert len(pair) == 2 and [q['event'] for q in pair] == ['start', 'finish'], key
        end = pair[-1]; files = []
        for kind, info in end['outputs'].items():
            p = Path(info['path']); actual = sha(p)
            assert actual == info['sha256'] and p.stat().st_size == info['byte_size']
            files.append(dict(kind=kind, **info, hash_verified=True))
        commands.append(dict(id=key, label=end['label'], command=end['command'], started_at=pair[0]['started_at'], ended_at=end['ended_at'], returncode=end['returncode'], outputs=files))
    traces = {}
    for p in Path(m['process_trace_dir']).glob('*.jsonl'):
        records = [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines()]
        if any('v3' in json.dumps(q, ensure_ascii=False) for q in records): traces[p.name] = records
    original = {p['parameter_id']: p for p in old_i['parameters']}
    current = {p['parameter_id']: p for p in i['parameters']}
    numeric = [dict(parameter_id=key, old_value=q['value'], current_value=current[key]['value'], equal=q['value'] == current[key]['value'], original_classification_retained=all(q.get(k) == current[key].get(k) for k in ['kind','dimension','time_basis','period','scenario','unit'])) for key,q in original.items()]
    assert len(numeric) == 51 and all(q['equal'] and q['original_classification_retained'] for q in numeric)
    source_reuse = [dict(source_id=s['source_id'], raw_capture_same=s['capture'] == next(x for x in old_i['sources'] if x['source_id'] == s['source_id'])['capture'], published_date=s['published_date'], date_uncertainty=s.get('date_uncertainty')) for s in i['sources']]
    assert all(q['raw_capture_same'] for q in source_reuse)
    result = dict(timestamp=dt.datetime.now(dt.timezone.utc).isoformat(), protected=protected, artifacts=artifacts, commands=commands, process_traces=traces, runtime_inventory=runtimes, original51_parameters=numeric, new_context_parameters=[q for q in i['parameters'] if q['parameter_id'] not in original], source_capture_reuse=source_reuse, repair_findings=repair['findings'], skill_steps=steps['steps'], executor_fact_index_read=dict(keys=list(declared_facts), claims=len(declared_facts['source_claims']), fact_index_sha256=sha(EX/'fact_checks_v3.json')))
    save('recheck_v3_ledger.json', result)
    print(json.dumps(dict(immutable133='PASS', emitting_artifacts=len(artifacts), commands=len(commands), failures=[q['id'] for q in commands if q['returncode']], traces=len(traces), original51_numbers='PASS', new_context_parameters=len(result['new_context_parameters']), source_capture_identity='PASS'),ensure_ascii=False))
elif sys.argv[1] == 'claims':
    import fitz
    from bs4 import BeautifulSoup
    inventory = load(HERE/'independent_original_inventory.json')
    names = {'tencent_h1_2026_official':'interim_2026_official','tencent_corporate_overview_sep2026':'corporate_overview_20260916','tencent_results_2q2026':'results_2q2026',old_i['sources'][0]['source_id']:'annual_2025',old_i['sources'][1]['source_id']:'annual_2024'}
    source_docs = {}; source_receipts = []
    for sid, name in names.items():
        orig = next(q for q in inventory if q['name'] == name); path=Path(orig['path'])
        assert sha(path) == next(q for q in i['sources'] if q['source_id'] == sid)['capture']['snapshot_sha256']
        doc = fitz.open(path); source_docs[sid]=[dict(page=k+1,text=page.get_text()) for k,page in enumerate(doc)]
        source_receipts.append(dict(source_id=sid,path=str(path),sha256=sha(path),pages=len(doc),parser='MuPDF original reopened'))
    html = old_out/'netease_2q2026.html'; sid='netease_results_2q2026'
    assert sha(html) == next(q for q in i['sources'] if q['source_id'] == sid)['capture']['snapshot_sha256']
    soup=BeautifulSoup(html.read_bytes(),'html.parser'); text=soup.get_text(' ',strip=True)
    source_docs[sid]=[dict(page='HTML',text=text)]
    source_receipts.append(dict(source_id=sid,path=str(html),sha256=sha(html),parser='BeautifulSoup original HTML'))
    normalized=lambda v:' '.join(v.split())
    checks=[]; contexts={}; unique={}
    for c in i['evidence_claims']:
        match=re.search(r'cited PDF page\s*(\d+)',c['locator']) or re.search(r'PDF page\s*(\d+)',c['locator'])
        declared_page=int(match.group(1)) if match else 'HTML'
        candidates=source_docs[c['source_id']]
        hits=[q['page'] for q in candidates if normalized(c['excerpt']) in normalized(q['text'])]
        good=declared_page in hits
        excerpt_good=hashlib.sha256(c['excerpt'].encode('utf-8')).hexdigest() == c['excerpt_sha256']
        src=next(q for q in i['sources'] if q['source_id']==c['source_id'])
        content_good=c['content_sha256']==src['capture']['snapshot_sha256']
        capture_good=c['capture_receipt_sha256']==src['capture']['receipt_sha256']
        row=dict(claim_id=c['claim_id'],source_id=c['source_id'],target_type=c['target_type'],target_id=c['target_id'],support_type=c['support_type'],locator=c['locator'],declared_page=declared_page,matched_pages=hits,excerpt_sha256=c['excerpt_sha256'],excerpt_hash_ok=excerpt_good,content_sha_ok=content_good,capture_binding_ok=capture_good,original_locator_match=good,extracted_value=c.get('extracted_value'),unit=c.get('unit'),period=c.get('period'),status='PASS' if good and excerpt_good and content_good and capture_good else 'FAIL')
        checks.append(row)
        key=c['source_id']+'|'+str(declared_page)
        if key not in contexts:
            context=next(q for q in candidates if q['page']==declared_page)
            contexts[key]=dict(source_id=c['source_id'],page=declared_page,full_original_context=context['text'],claim_ids=[])
        contexts[key]['claim_ids'].append(c['claim_id'])
        key=c['source_id']+'|'+c['excerpt_sha256']
        unique.setdefault(key,dict(source_id=c['source_id'],locator=c['locator'],excerpt=c['excerpt'],claim_ids=[]))['claim_ids'].append(c['claim_id'])
    parameters=[]; byclaim={q['claim_id']:q for q in checks}
    for p in i['parameters']:
        rows=[byclaim[q] for q in p['claim_ids']]
        parameters.append(dict(parameter_id=p['parameter_id'],value=p['value'],kind=p['kind'],unit=p['unit'],period=p['period'],rationale=p.get('rationale'),claim_ids=p['claim_ids'],source_ids=p['source_ids'],claims_match_target=all(q['target_type']=='parameter' and q['target_id']==p['parameter_id'] for q in rows),claims_originally_bound=all(q['status']=='PASS' for q in rows),support_types=[q['support_type'] for q in rows]))
    result=dict(sources=source_receipts,claims=checks,parameters=parameters,unique_excerpts=list(unique.values()),full_original_contexts=list(contexts.values()),research_coverage=i['research_coverage'],growth_driver_tree=i['growth_driver_tree'],segment_recognition=[dict(name=q['name'],recognition=q['recognition']) for q in i['segments']],management_communication_coverage=i['management_communication_coverage'],targets=i['management_targets'])
    save('recheck_v3_claims_and_contexts.json',result)
    print(json.dumps(dict(claims=len(checks),parameters=len(parameters),unique_excerpts=len(unique),original_contexts=len(contexts),failures=[q for q in checks if q['status']!='PASS'],parameter_binding_failures=[q['parameter_id'] for q in parameters if not q['claims_match_target'] or not q['claims_originally_bound']]),ensure_ascii=False))
elif sys.argv[1] == 'producer':
    db=EX.parents[4]/'.source_catalog/catalog.sqlite3'
    con=sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row;con.execute('PRAGMA query_only=ON')
    ids=['sa-f5cc0cf223e6460596a950f65d89f054','sa-f7d91778e20847cfbd744aeaca2e6454']
    rows=[dict(q) for q in con.execute('SELECT * FROM source_metadata_assertions WHERE assertion_id IN (?,?)',ids)]
    con.close()
    original=load(HERE/'independent_current_producer_rows.json')
    old=next(q for q in original['rows']['source_metadata_assertions'] if q['assertion_id']==ids[0])
    current_old=next(q for q in rows if q['assertion_id']==ids[0]); assert old==current_old
    request=load(EX/'v3_source_facts_2025.request.json');receipt=load(EX/'v3_source_facts_2025.receipt.json')
    result=dict(mode='ro/query_only',database=str(db),assertions=rows,old_row_unchanged=True,request=request,receipt=receipt)
    save('recheck_v3_producer_assertions.json',result)
    print(json.dumps(result,ensure_ascii=False))
elif sys.argv[1] == 'final':
    inventory=load(EX/'v3_runtime_inventory.json')['current_runtime']
    runtime=[]
    for q in inventory:
        a=sha(q['installed_path']); b=sha(q['canonical_path'])
        runtime.append(dict(**q,current_installed_sha256=a,current_canonical_sha256=b,unchanged=a==q['installed_sha256'] and b==q['canonical_sha256']))
    assert all(q['unchanged'] for q in runtime)
    os.environ['REVENUE_PUBLICATION_REGISTRY']=str(OUT/'publications.jsonl')
    sys.path.insert(0,str(Path(old_m['skill_root'])/'scripts'))
    import publication_registry as reg
    entries=reg._read_entries()
    f=load(OUT/'forecast.json');s=load(OUT/'snapshot.json');old_f=load(old_out/'forecast.json')
    assert any(q['artifact_type']=='forecast' and q['input_sha256']==f['input_sha256'] and q['result_sha256']==f['result_sha256'] for q in entries)
    assert any(q['artifact_type']=='snapshot' and q['input_sha256']==s['input_sha256'] and q['artifact_id']==s['snapshot_id'] and q['result_sha256']==s['forecast_result_sha256'] for q in entries)
    cmd=[sys.executable,'-B',str(Path(old_m['skill_root'])/'scripts/publication_registry.py'),'audit','--result',str(OUT/'forecast.json')]
    ran=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8');assert ran.returncode==0,(ran.returncode,ran.stderr)
    for seg in f['segments']:
        old_seg=next(q for q in old_f['segments'] if q['name']==seg['name'])
        assert seg['scenarios']==old_seg['scenarios']
    assert f['consolidated_forecast']==old_f['consolidated_forecast']
    assert f['sensitivities']==old_f['sensitivities']
    assert f['confidence']['score']==old_f['confidence']['score']==64
    original_claims={q['claim_id']:q for q in i['evidence_claims']};params={q['parameter_id']:q for q in i['parameters']}
    recognition=[]
    for seg in i['segments']:
        linked=[original_claims[q] for q in seg['recognition']['basis_claim_ids']]
        policy=' '.join(q['excerpt'] for q in linked)
        assert '控制權' in policy and '主要責任人' in policy and '按總額或淨額' in policy
        recognition.append(dict(segment=seg['name'],claim_ids=seg['recognition']['basis_claim_ids'],timing_and_principal_agent='PASS',mode=seg['recognition']['mode'],presentation=seg['recognition']['presentation']))
    mapped=[]
    for driver in i['growth_driver_tree']['drivers']:
        for node in driver['evidence_nodes']:
            linked=[original_claims[q] for q in node['claim_ids']]
            assert all(q['target_type']=='growth_driver' and q['target_id']==node['evidence_id'] for q in linked)
            mapped.append(dict(driver_id=driver['driver_id'],evidence_id=node['evidence_id'],claim_ids=node['claim_ids'],conclusion=node['conclusion'],combined_excerpt=' '.join(q['excerpt'] for q in linked)))
    required_sources={'games':{i['sources'][0]['source_id'],'tencent_h1_2026_official','netease_results_2q2026'},'socialnetworks':{i['sources'][0]['source_id'],'tencent_h1_2026_official'},'marketingservices':{i['sources'][0]['source_id'],'tencent_h1_2026_official','tencent_corporate_overview_sep2026'},'fintechbusinessservices':{i['sources'][0]['source_id'],'tencent_h1_2026_official','tencent_corporate_overview_sep2026'}}
    rationale_closure=[]
    for p in i['parameters']:
        if p['kind']!='analyst_assumption':continue
        linked=[original_claims[q] for q in p['claim_ids']]
        linked_sources={q['source_id'] for q in linked}
        prefix=p['parameter_id'].split('_growth_rate_')[0]
        required=required_sources.get(prefix,{'tencent_h1_2026_official'})
        assert required<=linked_sources
        rationale_closure.append(dict(parameter_id=p['parameter_id'],claim_ids=p['claim_ids'],linked_source_ids=sorted(linked_sources),all_required_fact_contexts_bound=True,future_value_is_analyst_assumption=True))
    assert len(rationale_closure)==45
    used=set()
    for seg in i['segments']:
        used.add(seg['base_revenue_parameter_id'])
        for sc in seg['scenarios'].values():
            for ids in sc['driver_parameter_ids'].values():used.update(ids)
    context_ids={p['parameter_id'] for p in i['parameters'] if p['parameter_id'].startswith('context_')}
    assert len(context_ids)==2 and not (context_ids & used)
    assert params['context_group_top5_customer_revenue_share']['value']==6.5/100
    assert params['context_group_largest_customer_revenue_share']['value']==3.4/100
    auth=load(EX/'v3_official_auth.json')
    for q in auth['attempts']:
        p=Path(q['raw_path']);assert sha(p)==q['sha256'] and p.stat().st_size==q['bytes']
        assert q['pdf_magic']==p.read_bytes().startswith(b'%PDF-')
    assert sum(q['bytes'] for q in auth['attempts'])==auth['aggregate_bytes']==196676
    assert auth['status']=='BLOCKED_UNAUTHENTICATED' and all(not q['same_sha_as_original'] for q in auth['attempts'])
    asof=[]
    for source in i['sources']:
        u=source.get('date_uncertainty')
        if not u:continue
        assert u['exact_publication_day'] is None and u['date_semantics']=='available_as_of_upper_bound'
        assert source['published_date']==u['available_as_of']==u['actual_read_date']==i['as_of_date']=='2026-10-08'
        asof.append(dict(source_id=source['source_id'],available_as_of='2026-10-08',exact_publication_day=None,old_assertion=u['previous_date_assertion'],accepted_scope='local/live availability on cutoff date only; no exact publication or annual sameSHA authentication'))
    narrative=load(HERE.parents[1]/'existing_narrative_current_vs_asof.json')
    assert narrative['new_worker_runs']==narrative['new_model_calls']==0 and not narrative['forecast_input_consumption_proven']
    narrative_summary=dict(evidence_path=str(HERE.parents[1]/'existing_narrative_current_vs_asof.json'),sha256=sha(HERE.parents[1]/'existing_narrative_current_vs_asof.json'),scope='MAIN recorded existing MSFT TXT evidence; no new HK Worker and no HK forecast consumption',current_reads=[q['evidence_span_count'] for q in narrative['checks'] if q['returncode']==0],asof_refusals=[q['refusal'] for q in narrative['checks'] if q['returncode']])
    initial=load(HERE/'final_review_integrity.json')['report_sha256']
    assert sha(HERE/'review.md')==initial['review.md'] and sha(HERE/'review.json')==initial['review.json']
    result=dict(runtime=runtime,registry=dict(entries=entries,command=cmd,returncode=ran.returncode,stdout=ran.stdout,stderr=ran.stderr,original_registry_sha256=sha(OUT/'publications.jsonl'),runtime_sha256=sha(Path(old_m['skill_root'])/'scripts/publication_registry.py'),chain_and_bindings='PASS'),old_numerical_output_equals_v3=True,confidence_score=64,recognition_closure=recognition,evidence_node_closure=mapped,rationale_closure=rationale_closure,context_only_parameters_not_used=sorted(context_ids),official_authentication=auth,date_availability_semantics=asof,narrative_existing_scope=narrative_summary,initial_review_unmodified=initial)
    save('recheck_v3_final_dependency_checks.json',result)
    print(json.dumps(dict(runtime=len(runtime),registry_audit=ran.returncode,registry_chain=len(entries),unchanged_old_numbers=True,recognition=len(recognition),node_mappings=len(mapped),rationales=len(rationale_closure),asof_bounds=len(asof),initial_review_preserved=True),ensure_ascii=False))
