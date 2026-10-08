from pathlib import Path
import argparse, datetime, hashlib, json, os, subprocess, sys
ROOT = Path(__file__).resolve().parent
OUT = Path(os.environ['TEMP']) / 'cwp-rf-e2e-20261008' / 'CN-688012'
OUT.mkdir(parents=True, exist_ok=True)
p = argparse.ArgumentParser(); p.add_argument('label'); p.add_argument('--response'); a = p.parse_args()
files = sorted(ROOT.joinpath('commands').glob('*ff-' + a.label + '-diagnostic.stdout.txt'))
response=Path(a.response) if a.response else files[-1]
payload = json.loads(response.read_text(encoding='utf-8'))
formal= 'company_wiki_trace' in payload
ref = payload['company_wiki_trace']['source_ref'] if formal else payload['filing']['source_ref']
config = str(ROOT.parents[4] / 'config' / 'source_catalog.yaml')
# A read-only diagnostic while the source_preparation schema defect is reported to MAIN.
command = [sys.executable, '-B', '-m', 'company_wiki.source_catalog.source_reader_cli', '--config', config, '--document-id', ref['document_id'], '--source-id', ref['source_id'], '--content-sha256', ref['content_sha256'], '--purpose', 'filing_reuse']
proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60, env=dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1'))
if proc.returncode: raise RuntimeError(proc.stderr.decode('utf-8'))
receipt = json.loads(proc.stderr)
assert hashlib.sha256(proc.stdout).hexdigest() == ref['content_sha256']
assert len(proc.stdout) == ref['byte_size']
raw = OUT / (a.label + '.pdf'); raw.write_bytes(proc.stdout)
(ROOT / (a.label + '_raw_receipt.json')).write_text(json.dumps(dict(command=command, source_ref=ref, receipt=receipt, diagnostic_only=not formal,preparation_response=str(response)),ensure_ascii=False,indent=2),encoding='utf-8')
import fitz
doc = fitz.open(stream=proc.stdout, filetype='pdf')
pages = [dict(page=i+1, text=page.get_text()) for i,page in enumerate(doc)]
dest = OUT/(a.label+'_pages.json'); dest.write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
summary=dict(label=a.label, output_root=str(OUT), raw=str(raw), sha256=ref['content_sha256'], byte_size=len(proc.stdout), pages=len(pages), parsed_pages_path=str(dest), manifest=receipt['manifest'])
(ROOT/(a.label+'_source_inspection.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
with (ROOT/'events.jsonl').open('a',encoding='utf-8') as f:
 f.write(json.dumps(dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),agent_id='rf_cn_execution',step='3',action='CWP verified binary read and deterministic PDF page text extraction',tool='source_reader_cli+PyMuPDF',input_summary=command,source_url=receipt['manifest']['source_url'],artifacts=[str(raw),str(dest)],outcome='sha_size_verified; actual formal RF source-preparation' if formal else 'diagnostic_only, not an RF source_preparation success',error=None),ensure_ascii=False)+'\n')
