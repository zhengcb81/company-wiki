from pathlib import Path
import argparse, json
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--pages',nargs='*',type=int);p.add_argument('--keywords',nargs='*');a=p.parse_args()
meta=json.loads((ROOT/(a.label+'_source_inspection.json')).read_text(encoding='utf-8'))
pages=json.loads(Path(meta['parsed_pages_path']).read_text(encoding='utf-8'))
for x in pages:
 if (a.pages and x['page'] in a.pages) or (a.keywords and any(k in x['text'] for k in a.keywords)):
  print('PAGE '+str(x['page'])+'\n'+x['text'])
