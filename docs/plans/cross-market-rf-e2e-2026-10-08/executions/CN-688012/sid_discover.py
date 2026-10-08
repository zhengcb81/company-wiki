from pathlib import Path
import datetime, json, os, subprocess, sys
ROOT=Path(__file__).resolve().parent
kind=sys.argv[1] if len(sys.argv)>1 else 'semi_annual_report'
year=int(sys.argv[2]) if len(sys.argv)>2 else 2026
req=dict(security_id='688012',entity='中微公司',document_kind=kind,fiscal_year=year,mode='exact',as_of_date='2026-10-08',fiscal_period='H1' if kind=='semi_annual_report' else 'FY')
req['acquisition_budget']=dict(schema_version='1.0',max_response_bytes=41943040,timeout_seconds=180,max_cost_usd='0.00')
(ROOT/'requests'/f'sid_{kind}_{year}.json').write_text(json.dumps(req,ensure_ascii=False,indent=2),encoding='utf-8')
cmd=[sys.executable,'-B','-m','src.company_wiki_adapter_cli','discover','--config','config.json']
p=subprocess.run(cmd,input=json.dumps(req,ensure_ascii=False).encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd='C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite',env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1'),timeout=180)
sys.stdout.buffer.write(p.stdout);sys.stderr.buffer.write(p.stderr)
with (ROOT/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),agent_id='rf_cn_execution',step='3',action='read-only actual SID discovery diagnostic for missing filing',tool='src.company_wiki_adapter_cli discover',input_summary=req,source_url=None,artifacts=[str(ROOT/'requests'/f'sid_{kind}_{year}.json')],outcome=f'exit {p.returncode}; no fetch or canonical write',error=None),ensure_ascii=False)+'\n')
sys.exit(p.returncode)
