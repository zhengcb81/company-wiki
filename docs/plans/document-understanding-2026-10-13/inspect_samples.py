"""Read-only architecture reconnaissance; no network, LLM, DB or raw copies.

Run from repository root with: python -X utf8 <this-file>
Writes only bounded observations beside this script, not normalized documents.
Not a production parser, benchmark or corpus discovery API.
"""
from pathlib import Path
import gzip
import hashlib
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from company_wiki.source_catalog.narrative_routing import classify_document_kind
import fitz
from bs4 import BeautifulSoup


def main():
    manifest = OUT / 'sample_manifest.json'
    samples = json.loads(manifest.read_text(encoding='utf-8'))['samples']
    rows = []
    for sample in samples:
        path = Path(sample['path'])
        if not path.is_absolute():
            path = ROOT / path
        started = time.monotonic()
        if not path.exists():
            rows.append({'id': sample['id'], 'status': 'MISSING', 'path': str(path)})
            continue
        before = path.stat()
        data = path.read_bytes()
        row = {'id': sample['id'], 'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(),
               'bytes': len(data), 'expected_family': sample['expected_family'],
               'title_only_kind': classify_document_kind(path.name),
               'scope': 'native-text reconnaissance; not semantic recall evaluation'}
        if path.suffix.lower() == '.pdf':
            doc = fitz.open(stream=data, filetype='pdf')
            texts = [page.get_text() for page in doc]
            row.update(page_count=len(doc), native_text_empty_pages=sum(len(t.strip()) < 30 for t in texts),
                       toc=doc.get_toc()[:28])
            heading = re.compile(r'管理[层層]|业务与技术|業務|募集资金|募集資金|项目|項目|风险因素|風險因素|Business|BUSINESS|Operating|OPERATION|Management|MANAGEMENT|Industry|INDUSTRY|Prospects|PROSPECTS|Q&A|Questions',re.I)
            row['heading_pages'] = [{'page': i+1, 'headings': [line.strip() for line in text.splitlines() if 3 < len(line.strip()) < 65 and heading.search(line)][:4]}
                                    for i, text in enumerate(texts)]
            row['heading_pages'] = [x for x in row['heading_pages'] if x['headings']][:45]
            pages = list(dict.fromkeys([1, *sample.get('pages', [])]))
            row['read_pages'] = [{'page': p, 'excerpt': texts[p-1][:sample.get('excerpt_chars',1800)]} for p in pages if 0 < p <= len(texts)]
            row['page_count'] = len(texts)
            doc.close()
        elif path.suffix.lower() in {'.htm','.html'}:
            soup = BeautifulSoup(data, 'html.parser')
            for node in soup(['script','style','head']): node.decompose()
            for node in list(soup.find_all(lambda tag: tag.name and tag.name.lower() in {'ix:header','ix:hidden'})): node.decompose()
            text = soup.get_text(' ', strip=True)
            row['native_text_chars'] = len(text)
            row['read_passages'] = []
            for pattern in sample.get('patterns', []):
                matches=list(re.finditer(pattern,text,re.I))
                selected=matches[:1]+matches[-1:] if len(matches)>1 else matches
                row['read_passages'].extend({'pattern':pattern,'character_offset':m.start(),'excerpt':text[max(0,m.start()-80):m.start()+1700]} for m in selected)
        else:
            lines=data.decode('utf-8-sig').splitlines()
            row['line_count']=len(lines)
            row['read_passages']=[]
            for pattern in sample.get('patterns',[]):
                hits=[i for i,line in enumerate(lines) if re.search(pattern,line,re.I)]
                for i in hits[:2]:row['read_passages'].append({'pattern':pattern,'line':i+1,'excerpt':'\n'.join(lines[max(0,i-2):i+14])[:2200]})
        after=path.stat()
        row['raw_unchanged']=before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
        row['elapsed_seconds']=round(time.monotonic()-started,3)
        rows.append(row)
        print(sample['id'],row.get('page_count',row.get('line_count','HTML')),row['title_only_kind'],row['elapsed_seconds'],flush=True)
    result={'schema_version':'document-understanding-observations/1','paid_calls':0,'network_calls':0,'raw_copies':0,'production_mutations':0,'samples':rows}
    (OUT/'sample_observations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
