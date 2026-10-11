"""Read exact existing original PDFs through source transport; zero acquisition."""
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from company_wiki.source_catalog.narrative_evidence import parse_pdf, select_narrative_evidence, verify_pdf_evidence_spans
from company_wiki.source_contract import source_id_for_sha256

EVIDENCE = Path(__file__).resolve().parent
CONFIG = Path(sys.argv[1])  # Explicit read-only catalog configuration supplied by caller.
SAMPLES = (
    ('annual', 'd64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5', 9165875, (44,), ('CVD', 'HAR', 'ALD', '重复量产订单')),
    ('ipo', '19cdb41e03b2d86ac15007753784f5859e1450a2bf79b514a7c0d4bd6830be67', 11211796, (173, 174), ('以销定产', '不会成为', '突发', '短期供货')),
)

def main():
    before_config = sha256(CONFIG.read_bytes()).hexdigest()
    results=[]
    env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    # Caller pins the actual isolated-tree src through PYTHONPATH.
    env['PYTHONDONTWRITEBYTECODE']='1'
    with TemporaryDirectory(prefix='w03-exact-source-') as owned:
        directory=Path(owned)
        for name, digest, expected_size, pages, anchors in SAMPLES:
            p=subprocess.run([sys.executable,'-B','-m','company_wiki.source_catalog.source_reader_cli',
                '--config',str(CONFIG),'--document-id','urn:company-wiki:document:sha256:'+digest,
                '--source-id',source_id_for_sha256(digest),'--content-sha256',digest,
                '--purpose','narrative_derivation'],env=env,capture_output=True,timeout=90)
            receipt=json.loads(p.stderr.decode('utf-8').strip())
            assert p.returncode==0 and receipt['status']=='ok', (name,p.returncode,receipt)
            assert sha256(p.stdout).hexdigest()==digest and len(p.stdout)==expected_size
            original=p.stdout
            path=directory/(name+'.pdf'); path.write_bytes(original)
            parsed=parse_pdf(path,source_id=source_id_for_sha256(digest),source_sha256=digest,
                language='zh',table_pages=pages)
            # A bounded policy examination of the real original pages, preserving
            # their original page/block/table/coordinates and complete raw SHA.
            scoped=replace(parsed, units=tuple(u for u in parsed.units if u.coordinates.page_number in pages))
            old=select_narrative_evidence(scoped,title='年报.pdf' if name=='annual' else '招股说明书.pdf',selector_version='0.6.0')
            new=select_narrative_evidence(scoped,title='年报.pdf' if name=='annual' else '招股说明书.pdf',selector_version='0.7.0')
            text=''.join(s.raw_text or '' for s in new.evidence_spans)
            compact=''.join(text.split())
            anchor_result={anchor: ''.join(anchor.split()) in compact for anchor in anchors}
            verified,failed=verify_pdf_evidence_spans(path,source_id=source_id_for_sha256(digest),
                source_sha256=digest,evidence_spans=new.evidence_spans)
            assert failed==() and len(verified)==len(new.evidence_spans), (name,'replay',failed)
            assert path.read_bytes()==original
            results.append({'sample':name,'raw_sha256':digest,'raw_bytes':len(original),
                'whole_parsed_pages':parsed.page_count,'scoped_pages':list(pages),
                'scoped_source_units':len(scoped.units),'legacy_candidate_count':old.candidate_count,
                'legacy_selected_count':len(old.evidence_spans),'new_candidate_count':new.candidate_count,
                'new_selected_count':len(new.evidence_spans),'new_omitted_count':new.omitted_candidate_count,
                'new_status':new.status,'replay_verified':len(verified),'replay_failed':len(failed),
                'anchors':anchor_result,'original_copy_sha256_after':sha256(path.read_bytes()).hexdigest(),
                'selected_locators':[s.locator for s in new.evidence_spans],
                'original_unchanged':True})
            print(json.dumps({'sample':name,'anchors':anchor_result,'selected':len(new.evidence_spans),
                'verified':len(verified),'status':new.status},ensure_ascii=False),flush=True)
            path.unlink()
    assert not directory.exists()
    assert sha256(CONFIG.read_bytes()).hexdigest()==before_config
    result={'provider_calls':0,'llm_calls':0,'cost_usd':0,'owned_temp_restored':True,
        'config_sha256_before':before_config,'config_sha256_after':sha256(CONFIG.read_bytes()).hexdigest(),
        'samples':results}
    (EVIDENCE/'real-source-pdf-node.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert all(all(r['anchors'].values()) for r in results)

if __name__=='__main__':
    main()
