import json, pathlib, hashlib, sys
sys.path.insert(0, '.')
from company_wiki.source_catalog import narrative_evidence as ne
from company_wiki.document_normalization import normalize_document
from tools.document_understanding_benchmark.textutil import anchor_matches
from tools.document_understanding_benchmark.contamination import support_set_digest

BIND = pathlib.Path.home() / '.du-bench' / 'bindings.local.json'
data = json.loads(BIND.read_text(encoding='utf8'))

NEW = {
  'fresh-cn-smic-fy2025': r'C:\Users\郑曾波\Projects\company-wiki\companies\中芯国际\raw\financial_reports\中芯国际：中芯国际2025年年度报告.pdf',
  'fresh-hk-anta-fy2025': r'C:\Users\郑曾波\Projects\company-wiki\companies\安踏體育\raw\financial_reports\annual\2026-04-09_hkexnews_12099632_二零二五年年報.pdf',
  'fresh-us-apple-10k': r'C:\Users\郑曾波\Projects\company-wiki\companies\Apple Inc\raw\financial_reports\annual\2025-10-31_sec_0000320193-25-000079_Apple Inc. 10-K 2025-09-27.htm',
}
data.update(NEW)
BIND.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print('bindings updated ->', len(data), 'entries')

GOLDDIR = pathlib.Path('tools/document_understanding_benchmark/gold')
fail = 0
for sid, path in NEW.items():
    p = pathlib.Path(path)
    raw = p.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    gp = GOLDDIR / f'{sid}.json'
    gold = json.loads(gp.read_text(encoding='utf8'))
    print(f'\n=== {sid} ===')
    print('  sha in gold :', gold['source_sha256'])
    print('  actual sha  :', sha, 'MATCH' if gold['source_sha256']==sha else '*** MISMATCH ***')
    if gold['source_sha256'] != sha:
        fail += 1
    # parse & collect all text
    if p.suffix.lower() == '.pdf':
        parsed = ne.parse_pdf_bytes(raw, source_id='x', source_sha256=sha, language='zh')
        units = parsed.units
    else:
        doc = normalize_document(raw, source_id='x', source_sha256=sha, mime_type='text/html')
        units = doc.units
    alltext = "\n".join((getattr(u, 'raw_text', '') or '') for u in units)
    for fact in gold['facts']:
        for gi, sset in enumerate(fact['any_support_sets']):
            for anchor in sset:
                q = anchor['exact_quote']
                ok = anchor_matches(q, alltext)
                print(f"    [{'OK ' if ok else 'MISS'}] {fact['id']}: {q[:60]}")
                if not ok:
                    fail += 1
    # inject digest
    gold['support_set_digest'] = support_set_digest(gold)
    gp.write_text(json.dumps(gold, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('  support_set_digest injected:', gold['support_set_digest'][:16])

print('\nTOTAL FAILURES:', fail)
