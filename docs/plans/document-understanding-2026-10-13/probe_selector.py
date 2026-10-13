"""Finite 3-document, native parser/selector diagnostic. No model/store writes."""
from pathlib import Path
import hashlib
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from company_wiki.source_catalog.narrative_evidence import parse_pdf_bytes, select_narrative_evidence


def main():
    samples=json.loads((OUT/'sample_manifest.json').read_text(encoding='utf8'))['samples']
    cases={'cn-q-business':('quarterly_report',[2,3]),'cn-equity':('unknown',[61,62,63,68]),'hk-annual':('annual_report',[11,12,13,24])}
    rows=[]
    for key,(kind,pages) in cases.items():
        r=next(r for r in samples if r['id']==key)
        p=Path(r['path']);p=p if p.is_absolute() else ROOT/p
        before=p.stat();data=p.read_bytes();sha=hashlib.sha256(data).hexdigest();start=time.monotonic()
        print('START',key,flush=True)
        parsed=parse_pdf_bytes(data,source_id='urn:company-wiki:source:sha256:'+sha,source_sha256=sha,parser_version='0.1.1',language='zh')
        package=select_narrative_evidence(parsed,title=p.name,existing_kind=kind,selector_version='0.8.0')
        chosen={s.locator for s in package.evidence_spans}
        focus=[{'locator':u.coordinates.locator(),'kind':u.unit_kind,'text':u.raw_text[:500],
                'truncated':len(u.raw_text)>500,'selected':u.coordinates.locator() in chosen}
               for u in parsed.units if u.coordinates.page_number in pages]
        rows.append({'sample':key,'source_sha256':sha,'kind_fallback':kind,'routed_kind':package.document_kind,
            'source_units':len(parsed.units),'selected':len(chosen),'candidates':package.candidate_count,
            'status':package.status,'physical_coverage_complete':package.coverage_complete,
            'opaque_pages':list(parsed.opaque_pages),'table_scan_pages':list(parsed.table_scan_pages),
            'deferred_table_pages':list(parsed.deferred_table_pages),'elapsed_seconds':round(time.monotonic()-start,3),
            'raw_unchanged':hashlib.sha256(p.read_bytes()).hexdigest()==sha and p.stat().st_mtime_ns==before.st_mtime_ns,'focus':focus})
        (OUT/'selector_probe.json').write_text(json.dumps({'scope':'3-case diagnostic, not overall recall','model_calls':0,'raw_copies':0,'rows':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print('DONE',key,rows[-1]['elapsed_seconds'],len(chosen),package.status,flush=True)


if __name__=='__main__':main()
