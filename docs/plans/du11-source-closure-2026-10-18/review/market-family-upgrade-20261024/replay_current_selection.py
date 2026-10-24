"""Bounded local research replay; public selector, existing DU-BENCH evidence/oracle.

No model, provider, download, source rewrite or alternative selection algorithm.
0.9.0 is explicitly under acceptance; this does not claim the 0.8 default switched.
Machine-local original bindings are supplied separately and never committed here.
"""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import time
import sys
import subprocess
from collections.abc import Mapping

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path.insert(0,str(ROOT))

from tools.document_understanding_benchmark.observer import _parse, _source_evidence
from tools.document_understanding_benchmark.evaluate import evaluate
from company_wiki.source_catalog import narrative_evidence as engine


def plain(value):
    if isinstance(value, Mapping):
        return {k:plain(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):
        return [plain(v) for v in value]
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bindings',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--sample',action='append',required=True)
    args=parser.parse_args()
    assert not args.output.exists(), 'Keep earlier observations immutable'
    args.output.mkdir(parents=True)
    bindings=json.loads(args.bindings.read_text(encoding='utf-8'))
    base=Path('tools/document_understanding_benchmark')
    manifest=json.loads((base/'du5_manifest.json').read_text(encoding='utf-8'))
    rows={r['sample_id']:r for r in manifest['samples']}
    producers=sorted((ROOT/'src/company_wiki').rglob('*.py'))
    producers.append(ROOT/'src/company_wiki/document_understanding/profiles/reading_catalog.json')
    def snapshot():
        return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in producers}
    source_before=snapshot()
    source_digest=hashlib.sha256(json.dumps(source_before,sort_keys=True).encode()).hexdigest()
    summary=[]
    for sid in args.sample:
        sample=rows[sid]
        original=Path(bindings[sid])
        before=hashlib.sha256(original.read_bytes()).hexdigest()
        assert before==sample['source_sha256'], sid
        started=time.monotonic()
        source_id='urn:company-wiki:source:sha256:'+before
        parsed,entry=_parse(engine,original,source_id,before)
        selected=engine.select_narrative_evidence(parsed,title=original.name,
            existing_kind='unknown',selector_version='0.9.0')
        spans=tuple(selected.evidence_spans)
        metadata=plain(selected.reading_context or {})
        # Reading context publishes policies, not the internal route object.
        # Do not fabricate a complete route from policy labels or gold.
        route=metadata.get('route')
        # Use the actual native route if available. Do not reconstruct it from gold.
        observed={'schema_version':'du-observed/1','sample_id':sid,'source_sha256':before,
            'route':route,'selected_locators':[s.locator for s in spans],
            'selected_text':'\n'.join(s.raw_text for s in spans),
            'selected_evidence':_source_evidence(spans,parsed.units),
            'semantic_units':[],'claims':[],
            'coverage':{'native_scan':'complete' if parsed.coverage_complete else 'partial',
                        'complete':selected.coverage_complete,'opaque_pages':list(parsed.opaque_pages),
                        'read_pages':sorted({u.coordinates.page_number for u in parsed.units if u.coordinates.page_number}),
                        'deferred_unit_ids':[],'unassigned_unit_ids':[]},
            'metrics':{'selected_spans':len(spans),'selected_text_bytes':sum(len(s.raw_text.encode()) for s in spans)},
            'execution':{'mode':'adapter','entry_point':'select_narrative_evidence','selector_version':'0.9.0',
                         'parser_entry':entry,'elapsed_seconds':time.monotonic()-started,'calls':0}}
        # Oracle expectations remain the old frozen source-side gold, never selector output.
        gold=json.loads((base/sample['gold_file']).read_text(encoding='utf-8'))
        assert hashlib.sha256((base/sample['gold_file']).read_bytes()).hexdigest()==sample['gold_sha256']
        result=evaluate(observed,gold)
        payload=json.dumps({'observed':observed,'evaluation':result,'selection_metadata':metadata},ensure_ascii=False,default=str).encode()
        (args.output/(sid+'.json.gz')).write_bytes(gzip.compress(payload,mtime=0))
        assert hashlib.sha256(original.read_bytes()).hexdigest()==before
        row={'sample_id':sid,'source_sha256':before,'status':result['status'],
             'metrics':result.get('metrics'),'route':route,'selected_count':len(spans),
             'reading_policies':[{k:r.get(k) for k in ('profile_id','profile_version','family','family_policy')}
                                 for r in metadata.get('reading_policies',[])],
             'mapped_source_count':len(observed['selected_evidence']),
             'producer_tree_sha256':source_digest,
             'parser_entry':entry,'original_unchanged':True,'external_calls':0,
             'seconds':round(time.monotonic()-started,3)}
        summary.append(row)
        print(json.dumps(row,ensure_ascii=False),flush=True)
    (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert source_before==snapshot(), 'Source or catalog changed during observation'
    (args.output/'replay-binding.json').write_text(json.dumps({
        'producer_sha256':source_before,'producer_tree_sha256':source_digest,
        'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'selector_version':'0.9.0','source_stable':True,'new_model_calls':0,'downloads':0,
        'scope':'source selection only; old gold issues retained, no formal summary or RF acceptance'},
        ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
