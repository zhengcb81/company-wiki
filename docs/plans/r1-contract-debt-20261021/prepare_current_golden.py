"""Prepare reviewed current-v2 files in owned tmp; never writes a repository golden."""
from __future__ import annotations
from copy import deepcopy
import hashlib, json, os, socket, sys
from pathlib import Path
from datetime import datetime, timezone

PLAN=Path(__file__).resolve().parent
TREE=PLAN.parents[2]
TMP=Path('C:/Users/郑曾波/Projects/company-wiki/.planning/r1ctfix')
OUT=TMP/'golden-proposal'
OUT.mkdir(exist_ok=False)
for name in ('OPENAI_API_KEY','DEEPSEEK_API_KEY','MINIMAX_API_KEY','MIMO_API_KEY','TAVILY_API_KEY','ANTHROPIC_API_KEY'): os.environ.pop(name,None)
os.environ.update(PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',COMPANY_WIKI_NETWORK='blocked',COMPANY_WIKI_REAL_LLM='0',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
def blocked(*args,**kwargs): raise RuntimeError('offline reviewed fixture cannot open sockets')
socket.socket.connect=blocked
socket.create_connection=blocked
sys.path[:0]=[str(TREE/p) for p in ('src','scripts','tests','tests/contract')]
from company_wiki.automation.models import canonical_json
from support.narrative_transport_fixture import published_fixture
from support.narrative_golden_evolution import assert_reviewed_transcript_evolution
from test_narrative_transport_cli import _cli,_reference

old_dir=TREE/'tests/fixtures/narrative_transport_v1'
scratch=TMP/'gp'
scratch.mkdir()
with published_fixture(scratch) as fixture:
 reference=_reference(fixture)
 result=_cli(fixture,'read',{'schema_version':'narrative-read-request/1','narrative_ref':reference,'as_of_date':'2026-09-01','expected_source':fixture.expected_source})
 assert result.returncode==0,result.stderr
 bundle=json.loads(result.stdout)
 bundle['expected_read_policy_sha256']='f'*64
 old=json.loads((old_dir/'bundle.json').read_bytes())
 assert_reviewed_transcript_evolution(old,bundle)
 data=canonical_json(bundle).encode('utf-8')
 reference.update(artifact_version_id='narrative-golden-txt-current-v2',artifact_sha256=hashlib.sha256(data).hexdigest(),byte_size=len(data))
 receipt=json.loads(result.stderr)
 receipt.update(narrative_ref=reference,source_read_policy_sha256='f'*64,read_at='2026-10-03T00:00:00Z')
 request=json.loads((old_dir/'read_request.json').read_bytes())
 request['narrative_ref']=reference
 values={'bundle.json':bundle,'reference.json':reference,'read_receipt.json':receipt,'read_request.json':request}
 for name,value in values.items(): (OUT/name).write_bytes(canonical_json(value).encode('utf-8'))
 (OUT/'invalid_request.json').write_bytes((old_dir/'invalid_request.json').read_bytes())
 metadata=deepcopy(json.loads((old_dir/'metadata.json').read_bytes()))
 metadata.update(schema_version='narrative-transport-golden/2',fixture_scope='reviewed current TXT snapshot; historical v1 files retained unchanged')
 metadata['file_sha256']={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in metadata['file_sha256']}
 (OUT/'metadata.json').write_bytes(canonical_json(metadata).encode('utf-8'))
 record={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'status':'reviewed_proposal','historical_bundle_sha256':hashlib.sha256((old_dir/'bundle.json').read_bytes()).hexdigest(),'current_bundle_sha256':hashlib.sha256(data).hexdigest(),'files':[p.name for p in OUT.iterdir()],'external_model_or_network_calls':0,'repo_golden_writes':0,'semantic_gate':'all12 inspected changes only; exact full-object equality after explicit expected changes; both parser-era source replay'}
 (OUT/'proposal.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(record))
