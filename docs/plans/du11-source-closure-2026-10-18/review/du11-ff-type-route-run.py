"""Independent original public mypy command in an owned source snapshot."""
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time
import xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent
SOURCE=Path('C:/Users/郑曾波/.codex/worktrees/du11-ff-reception/filing-fetch')
RELS=['scripts/transcript_reuse_selection.py','.pre-commit-config.yaml','scripts/transcript_tool_transport.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(args):return subprocess.run(['git','-C',str(SOURCE),*args],capture_output=True,check=True,timeout=30).stdout
before={r:sha(SOURCE/r) for r in RELS}
receipt={'head':git(['rev-parse','HEAD']).decode().strip(),'sha256_before':before}
old=ast.parse(git(['show','HEAD:scripts/transcript_reuse_selection.py']).decode())
new=ast.parse((SOURCE/RELS[0]).read_text(encoding='utf8'))
for i,node in enumerate(new.body):
    if isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name) and node.target.id=='_QUALIFICATION_FIELDS':
        new.body[i]=ast.Assign(targets=[node.target],value=node.value)
receipt['ast_identical_after_erasing_only_new_annotation']=ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
start=time.monotonic()
with tempfile.TemporaryDirectory(prefix='du11-ff-type-route-review-') as directory:
    root=Path(directory);snap=root/'source';snap.mkdir();temp=root/'tmp';temp.mkdir();guard=root/'guard';guard.mkdir()
    archive=git(['archive','--format=tar','HEAD','scripts','pyproject.toml','.pre-commit-config.yaml','tests/test_du11_transcript_reuse_selection.py'])
    with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
        assert all((snap/m.name).resolve().is_relative_to(snap.resolve()) and (m.isfile() or m.isdir()) for m in tf.getmembers())
        tf.extractall(snap,filter='data')
    for rel in RELS[:2]:(snap/rel).write_bytes((SOURCE/rel).read_bytes())
    (snap/'tests/test_type_route_independent.py').write_bytes((OUT/'du11-ff-type-route-controls.py').read_bytes())
    (guard/'sitecustomize.py').write_text('''import os,sys

def audit(event,args):
    if event in {"socket.connect","socket.getaddrinfo","socket.gethostbyname","socket.gethostbyaddr"}:
        with open(os.environ["DU11_NETWORK_LOG"],"a",encoding="utf8") as f:f.write(event+"\\n")
        raise RuntimeError("offline review network guard")
sys.addaudithook(audit)
''',encoding='utf8')
    env={k:os.environ[k] for k in ['SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','SYSTEMDRIVE'] if k in os.environ}
    env.update(USERPROFILE=str(root),TEMP=str(temp),TMP=str(temp),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONPATH=os.pathsep.join([str(guard),str(snap/'scripts'),str(snap/'tests')]),DU11_NETWORK_LOG=str(root/'network.log'),MYPY_CACHE_DIR=str(root/'mypy-cache'))
    sentinel=root/'sentinel';sentinel.write_bytes(b'baseline restore');s_before=sha(sentinel),sentinel.stat().st_mtime_ns
    command=[sys.executable,'-B','-m','mypy','scripts/filing_contracts.py','scripts/fetch_filing.py']
    p=subprocess.run(command,cwd=snap,env=env,capture_output=True,timeout=60)
    (OUT/'du11-ff-type-route-mypy.log').write_bytes(p.stdout+p.stderr)
    receipt['mypy']={'command':command,'returncode':p.returncode,'output':p.stdout.decode('utf8').strip()}
    command=[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','--basetemp',str(temp/'pytest'),'tests/test_type_route_independent.py','--junitxml',str(OUT/'du11-ff-type-route-independent.xml')]
    p=subprocess.run(command,cwd=snap,env=env,capture_output=True,timeout=30)
    (OUT/'du11-ff-type-route-independent.log').write_bytes(p.stdout+p.stderr)
    xml=ET.parse(OUT/'du11-ff-type-route-independent.xml').getroot()
    receipt['pytest']={'command':command,'returncode':p.returncode,'suite':(xml.find('testsuite') if xml.tag=='testsuites' else xml).attrib}
    receipt['snapshot_sha256']={r:sha(snap/r) for r in RELS}
    receipt['sentinel_unchanged']=(sha(sentinel),sentinel.stat().st_mtime_ns)==s_before
    receipt['network_attempts']=len((root/'network.log').read_text().splitlines()) if (root/'network.log').exists() else 0
    receipt['archive_sha256']=hashlib.sha256(archive).hexdigest();receipt['owned_temp']=str(root)
receipt['owned_temp_removed']=not root.exists()
receipt['sha256_after']={r:sha(SOURCE/r) for r in RELS}
receipt['source_unchanged']=before==receipt['sha256_after'];receipt['wall_seconds']=round(time.monotonic()-start,2)
(OUT/'du11-ff-type-route-independent-run.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print(json.dumps({'mypy':receipt['mypy'],'pytest':receipt['pytest']['suite'],'unchanged_ast':receipt['ast_identical_after_erasing_only_new_annotation'],'owned_temp_removed':receipt['owned_temp_removed'],'source_unchanged':receipt['source_unchanged'],'network_attempts':receipt['network_attempts'],'wall_seconds':receipt['wall_seconds']}))
