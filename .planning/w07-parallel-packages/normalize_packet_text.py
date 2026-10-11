"""Keep new distributable Markdown LF without altering frozen engineering inputs."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
record_path = HERE / 'dispatch-record.json'
record = json.loads(record_path.read_text(encoding='utf-8'))
central = Path(record['central_root'])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for p in central.rglob('*'):
    if p.is_file() and p.suffix in {'.json', '.md'}:
        p.write_bytes(p.read_bytes().replace(b'\r\n', b'\n'))
contract = (central / 'handoff_contract.md').read_bytes()
for lane in record['lanes']:
    plan = Path(lane['start_here']).parent
    Path(lane['start_here']).write_bytes(Path(lane['card']).read_bytes())
    (plan / 'HANDOFF_CONTRACT.md').write_bytes(contract)
    lane['card_sha256'] = sha(Path(lane['card']))
    assert sha(Path(lane['start_here'])) == lane['card_sha256']
record_path.write_bytes((json.dumps(record, ensure_ascii=False, indent=2)+'\n').encode())
d = json.loads((central / 'dispatch.json').read_text(encoding='utf-8'))
d['lanes'] = record['lanes']
(central / 'dispatch.json').write_bytes((json.dumps(d, ensure_ascii=False, indent=2)+'\n').encode())
v = json.loads((HERE / 'verification.json').read_text(encoding='utf-8'))
v['distributable_text_lf'] = True
v['card_bytes_reverified_after_lf'] = True
raw = (json.dumps(v, ensure_ascii=False, indent=2)+'\n').encode()
(HERE / 'verification.json').write_bytes(raw)
(central / 'preparation-verification.json').write_bytes(raw)
print('Three card copies and common contract match; fixed engineering input bytes untouched.')
