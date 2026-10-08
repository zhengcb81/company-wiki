import pathlib,subprocess,json,hashlib,datetime
H=pathlib.Path(__file__).resolve().parent
T=pathlib.Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/CN-688012-review')
POP=pathlib.Path('C:/Users/郑曾波/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')
jobs=[('half',176),('half',177),('annual',25),('annual',65),('annual',218),('annual',219)]
rows=[]
for name,page in jobs:
 dest=T/(f'{name}-p{page}')
 args=[str(POP),'-f',str(page),'-l',str(page),'-r','140','-png','-singlefile',str(T/(name+'.pdf')),str(dest)]
 subprocess.run(args,check=True,timeout=30,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 p=dest.with_suffix('.png');rows.append({'file':str(p),'page':page,'source_label':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'command':args})
(H/'visual_table_render_receipt.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False))
