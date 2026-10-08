import json,hashlib
from pathlib import Path
import fitz
H=Path(__file__).resolve().parent;P=H.parent.parent
M=json.loads((P/'executions'/'CN-688012'/'manifest_v3.json').read_text(encoding='utf-8'))
O=Path(M['output_root']);T=O.parent.parent/'CN-688012-review'/'v3';T.mkdir(exist_ok=True,parents=True)
rows=[]
for ident,page in [('1225482894',4),('1225482911',4),('1225482918',3),('1225482917',2)]:
 raw=O/'announcements'/(ident+'.pdf');doc=fitz.open(raw);dest=T/f'{ident}-p{page}.png'
 doc[page-1].get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(dest)
 rows.append(dict(announcement_id=ident,pdf_page=page,raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),image=str(dest),image_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),status='rendered_pending_visual_read'))
(H/'v3_visual_target_receipt.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False))
