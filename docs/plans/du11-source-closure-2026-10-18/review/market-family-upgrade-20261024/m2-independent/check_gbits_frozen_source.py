from pathlib import Path
import gzip,json,hashlib,zipfile,io,xml.etree.ElementTree as ET,re
base=Path('docs/plans/du11-source-closure-2026-10-18/review/market-family-upgrade-20261024');out=base/'m2-independent'
original=Path('C:/Users/郑曾波/Projects/company-wiki/companies/吉比特/raw/research/中泰-吉比特财报交流会0409.mp3-文稿-转写结果.docx')
raw=original.read_bytes();before=hashlib.sha256(raw).hexdigest();assert before=='63777874f5956f37ed32f4839c170340af4f61ee7594b99423acc698968a158a'
with zipfile.ZipFile(io.BytesIO(raw)) as z:xml=z.read('word/document.xml')
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
paras=ET.fromstring(xml).findall('w:body/w:p',ns)
w='{'+ns['w']+'}'
def visible(node):
    if node.tag==w+'t': return node.text or ''
    if node.tag in {w+'tab',w+'br',w+'cr'}:return ' '
    if node.tag in {w+'del',w+'moveFrom'}:return ''
    return ''.join(visible(child) for child in node)
texts=[visible(p).strip() for p in paras]
from company_wiki.document_normalization.text import normalize_text
old=json.loads(gzip.decompress((base/'m2-native-real-selection/du5-cn-gbits-call.json.gz').read_bytes()))
new=json.loads(gzip.decompress((base/'m2-intent-real-selection/du5-cn-gbits-call.json.gz').read_bytes()))
oldloc={x['locator'] for x in old['observed']['selected_evidence']}
rows=[]
for x in new['observed']['selected_evidence']:
    match=re.fullmatch(r'loc:v1/paragraph:(\d+)',x['locator']);assert match
    index=int(match[1]);original_text=normalize_text(texts[index]);assert original_text==x['text'],(index,original_text,x['text'])
    if x['locator'] not in oldloc:
        rows.append({'locator':x['locator'],'paragraph_index':index,'source_role':x['source_role'],'text':x['text'],'text_sha256':hashlib.sha256(x['text'].encode()).hexdigest(),'previous_paragraph_excerpt':texts[index-1][-350:] if index else '', 'next_paragraph_excerpt':texts[index+1][:350] if index+1<len(texts) else ''})
assert hashlib.sha256(original.read_bytes()).hexdigest()==before
r={'source_sha256':before,'paragraph_count':len(texts),'selected23_exact_original_matches':True,'baseline_selected':len(old['observed']['selected_evidence']),'new_selected':len(new['observed']['selected_evidence']),'new_rows':rows,'all_selected_roles':sorted({x['source_role'] for x in new['observed']['selected_evidence']}),'old_gold_status':new['evaluation']['status'],'source_unchanged':True,'limits':'Independent raw ZIP/XML check of frozen selection observations. Not current final source replay, new M1 gold acceptance, formal summary or RF PASS. First probe missed OOXML tabs; corrected XML-visible walker accounts for tab/br/cr.'}
(out/'real-gbits-frozen-source-check.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=False,indent=2))
