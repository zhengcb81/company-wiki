from pathlib import Path
import datetime as dt, hashlib, json, sys, sqlite3, os
HERE=Path(__file__).resolve().parent
WIKI=HERE.parents[4]
OUT=Path(json.loads((HERE/'before.json').read_text(encoding='utf-8'))['output_root'])
def emit(step,action,tool,summary,urls=None,outcome='success',artifacts=None):
    with (HERE/'events.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps(dict(timestamp_utc=dt.datetime.now(dt.timezone.utc).isoformat(),agent_id='/root/rf_hk_execution',step=step,action=action,tool=tool,input_summary=summary,source_url=urls,artifacts=artifacts or [],outcome=outcome,error=None),ensure_ascii=False)+'\n')
if sys.argv[1]=='set-output':
    p=HERE/'before.json';data=json.loads(p.read_text(encoding='utf-8'));data['superseded_sandbox_output_root']=data['output_root'];data['output_root']=str(Path(os.environ['TEMP'])/'cwp-rf-e2e-20261008/HK-00700');Path(data['output_root']).mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');print(data['output_root'])
elif sys.argv[1]=='events':
    emit('setup','read_contract_and_skills','exec/read','Read common execution contract, RF+FF+PDF skills, all required references and construction guidance; runtime six files match canonical repository.')
    emit('1A','official_search_open','web.run','Opened Tencent results/investors/latest-results (9p), interim (122p), announcements, corporate-kit. Official Q2/H1 released 2026-08-12. Old HKEX annual URL inaccessible in web, local original remains. Latest webcast internal-error; static PPT web-returned text/html zero lines.', ['https://www.tencent.com/investors/results/','https://www.tencent.com/Investors/','https://www.tencent.com/wp-content/uploads/2026/08/Tencent-Announces-2026-Second-Quarter-Results.pdf','https://www.tencent.com/wp-content/uploads/2026/08/E700_IR.pdf','https://www.tencent.com/investors/announcements/','https://www.tencent.com/investors/investor-kit-calendar/'])
    emit('3','actual_source_preparation','run_logged.py','RF entry→configured FF repo→CWP: annual language zh excludes indexed language null; no-language yields fiscal_year mismatch. H1 fetch fails ensure rc1. All requests+failures kept; no fabricated captures.',outcome='failed')
    print('events written')
elif sys.argv[1]=='local-parse':
    import fitz
    result=[]
    for y in [2025,2024]:
        p=WIKI/'companies/腾讯/raw/financial_reports/annual'/f'腾讯：{y}年年度报告.pdf'
        d=fitz.open(p);pages=[dict(page=i+1,text=q.get_text()) for i,q in enumerate(d)]
        dest=OUT/f'annual_{y}_pages.json';dest.write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
        matches=[]
        for q in pages:
            if any(t in q['text'] for t in ['751,766','660,257','收入確認','收入确认','市場推廣服務','营销服务','金融科技及企業服務','國際市場遊戲']):
                matches.append(q)
        result.append(dict(year=y,original=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),pages=len(pages),parsed_pages_path=str(dest),matched_pages=[q['page'] for q in matches]))
        print('\n# ANNUAL',y)
        for q in matches[:17]:print('\n# PDF PAGE',q['page'],'\n',q['text'])
    (HERE/'deterministic_local_parse.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    emit('3','deterministic_pdf_parse','fitz.get_text','Read local annual original bytes for research; this is task-local parsing, not CWP canonical Worker execution, which is not claimed.',artifacts=[str(OUT/'annual_2025_pages.json'),str(OUT/'annual_2024_pages.json')])
elif sys.argv[1]=='db-debug':
    c=sqlite3.connect(f'file:{(WIKI/".source_catalog/catalog.sqlite3").as_posix()}?mode=ro',uri=True);c.row_factory=sqlite3.Row
    for t in ['documents','sources','locations']:
        cols=[q[1] for q in c.execute(f'pragma table_info({t})')];print(t,cols)
    rows=[dict(q) for q in c.execute("select * from documents where document_id in (?,?)",['urn:company-wiki:document:sha256:d19f183452e9b8d0c47bcb7543dcbf435b585b2610759b42c0cba7c13f7361c7','urn:company-wiki:document:sha256:70f529984a87ef7f46d9e1db26bb9ef27eef9c01d29c59aabf69e557b479a6a0'])]
    (HERE/'db_readonly_documents.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(rows,ensure_ascii=False))
