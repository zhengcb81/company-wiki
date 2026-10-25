"""Freeze neutral legacy HTML expectations before changing its parser."""
from collections.abc import Mapping
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from company_wiki.document_normalization import normalize_document

sample=b'''<!DOCTYPE html><html><body>
<h1>Business overview</h1>
<div><p><b>Alpha Services</b></p>
<p>Alpha Services primarily comprises:</p>
<div style="display:flex"><span>\xe2\x80\xa2</span><div><p>Industrial platforms supply subscription software and support services.</p></div></div>
<div style="display:flex"><span>\xe2\x80\xa2</span><div><p>Field services include equipment installation and customer training.</p></div></div>
</div>
<div><p><b><i>Industrial platforms</i></b></p>
<p>Platform customers pay according to their measured usage.</p></div>
<p><b>Beta Services</b></p><p>Beta Services includes:</p>
<ul><li>Consumer products include hardware.<ul><li>Accessories support the hardware.</li></ul></li><li>Retail support includes local repairs.</li></ul>
<p><b>Revenue increased sharply during the year.</b></p>
<p>The products have <b>strong demand</b> in several regions.</p>
<table><tr><th><b>Revenue</b></th><th>2025</th></tr><tr><td>Hardware</td><td>120</td></tr></table>
<p><span style="font-weight:bold">Visible </span><span style="font-weight:normal">normal reset</span></p>
<div style="display:flex"><span hidden>\xe2\x80\xa2</span><p>A flex container alone does not establish a list.</p></div>
<p>In prose the symbol \xe2\x80\xa2 is only punctuation.</p>
</body></html>'''
node=ROOT/'docs/plans/du11-source-closure-2026-10-18/review/cf-source-20261025/frozen-legacy-html'
node.mkdir(exist_ok=True)
if (node/'expected-1.0.json').exists():
    raise FileExistsError('Never regenerate a legacy oracle from modified parser')
sha=hashlib.sha256(sample).hexdigest()
source='urn:company-wiki:source:sha256:'+sha
parsed=normalize_document(sample,source_id=source,source_sha256=sha,mime_type='text/html',parser_version='1.0.0')


def plain(value):
    if isinstance(value,Mapping):return {k:plain(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [plain(v) for v in value]
    return value


rows=[{'unit_id':u.unit_id,'source_id':u.source_id,'parser_name':u.parser_name,
       'parser_version':u.parser_version,'coordinates':asdict(u.coordinates),
       'raw_text':u.raw_text,'unit_kind':u.unit_kind,'source_role':u.source_role,
       'language':u.language,'quality_flags':list(u.quality_flags),'metadata':plain(u.metadata)} for u in parsed.units]
(node/'neutral.html').write_bytes(sample)
result={'status':'FROZEN_BEFORE_HTML_PARSER_CHANGE_NOT_NEW_FEATURE_ACCEPTANCE',
    'source_id':source,'source_sha256':sha,'mime_type':'text/html','parser_version':'1.0.0',
    'runtime':{'python':sys.version,'beautifulsoup4':importlib.metadata.version('beautifulsoup4')},
    'units':rows,'unit_count':len(rows),'old_text_order_coordinates_complete_metadata_bound':True,
    'next_test':'Public explicit legacy normalization and replay must exactly match every field; do not regenerate this expected file to pass a changed parser.'}
(node/'expected-1.0.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'source_sha256':sha,'unit_count':len(rows),'files_bytes':sum(p.stat().st_size for p in node.iterdir())}))
