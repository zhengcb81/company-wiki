from pathlib import Path
import json, os, datetime, hashlib

ROOT = Path(__file__).resolve().parent
OUT = Path(os.environ['TEMP']) / 'cwp-rf-e2e-20261008' / 'CN-688012'
OUT.mkdir(parents=True, exist_ok=True)
ROOT.joinpath('requests').mkdir(exist_ok=True)
specs = [('annual2025', 'annual_report', 2025, None), ('annual2024', 'annual_report', 2024, None), ('half2026', 'semi_annual_report', 2026, 'H1'), ('q12026', 'quarterly_report', 2026, 'Q1')]
for label, kind, year, period in specs:
    req = dict(schema_version='2.0', company_query='688012', market='CN', document_kind=kind, mode='exact', fiscal_year=year, as_of_date='2026-10-08', filing_intent='reuse_only')
    if period: req['fiscal_period'] = period
    ROOT.joinpath('requests', label + '.json').write_text(json.dumps(req, ensure_ascii=False, indent=2), encoding='utf-8')
event = dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), agent_id='rf_cn_execution', step='1', action='initialize fixed identity and isolated output', tool='local-file', input_summary='CN 688012; 2025 base, 2026-2028 forecast; as_of 2026-10-08', source_url=None, artifacts=[str(OUT)], outcome='created', error=None)
ROOT.joinpath('events.jsonl').write_text(json.dumps(event, ensure_ascii=False)+'\n', encoding='utf-8')
print(json.dumps(dict(output_root=str(OUT)), ensure_ascii=False))
