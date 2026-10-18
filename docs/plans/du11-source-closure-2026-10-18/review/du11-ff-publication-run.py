"""Independent isolated snapshot run; never run from an author/prod tree."""
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
RELS=['tools/complexity_diagnostics.py','tools/ci_tests.py','tests/test_complexity_diagnostics.py','tests/test_ci_tests.py']
REL_TRANSPORT='scripts/transcript_tool_transport.py'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(args):return subprocess.run(['git','-C',str(SOURCE),*args],capture_output=True,check=True,timeout=30).stdout
before={r:sha(SOURCE/r) for r in RELS+[REL_TRANSPORT]}
receipt={'head':git(['rev-parse','HEAD']).decode().strip(),'source_sha256_before':before}
oldtable=ast.parse(git(['show','HEAD:tools/ci_tests.py']).decode())
newtable=ast.parse((SOURCE/'tools/ci_tests.py').read_text())
def ci(tree):
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CI_TESTS' for t in n.targets))
old,new=ci(oldtable),ci(newtable)
receipt['ci_table']={'before':len(old),'after':len(new),'added':sorted(set(new)-set(old)),'removed':sorted(set(old)-set(new)),'unique':len(new)==len(set(new))}
start=time.monotonic()
with tempfile.TemporaryDirectory(prefix='du11-ff-publication-review-') as directory:
    root=Path(directory);snap=root/'snapshot';snap.mkdir();temp=root/'tmp';temp.mkdir();guard=root/'guard';guard.mkdir()
    archive=git(['archive','--format=tar','HEAD','scripts','tools','tests/test_complexity_diagnostics.py','tests/test_ci_tests.py','pyproject.toml'])
    with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
        assert all((snap/m.name).resolve().is_relative_to(snap.resolve()) and (m.isfile() or m.isdir()) for m in tf.getmembers())
        tf.extractall(snap,filter='data')
    for rel in RELS:(snap/rel).write_bytes((SOURCE/rel).read_bytes())
    (snap/'tests/test_publication_independent.py').write_bytes((OUT/'du11-ff-publication-controls.py').read_bytes())
    (guard/'sitecustomize.py').write_text('''import sys,os

def audit(event,args):
    if event in {"socket.connect","socket.getaddrinfo","socket.gethostbyname","socket.gethostbyaddr"}:
        with open(os.environ["DU11_NETWORK_LOG"],"a",encoding="utf8") as f:f.write(event+"\\n")
        raise RuntimeError("offline review network guard")
sys.addaudithook(audit)
''',encoding='utf8')
    env={k:os.environ[k] for k in ['SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','SYSTEMDRIVE'] if k in os.environ}
    env.update(USERPROFILE=str(root),TEMP=str(temp),TMP=str(temp),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONPATH=os.pathsep.join([str(guard),str(snap/'scripts'),str(snap/'tests')]),DU11_NETWORK_LOG=str(root/'network.log'))
    sentinel=root/'sentinel';sentinel.write_bytes(b'restore baseline');sentinel_before=sha(sentinel),sentinel.stat().st_mtime_ns
    nodes=['tests/test_complexity_diagnostics.py::test_json_stdout_preserves_unicode_paths_under_non_utf8_child_stdio','tests/test_ci_tests.py::test_shared_ci_table_covers_pure_local_reuse_and_current_reader_regressions','tests/test_ci_tests.py::test_real_pytest_failure_reports_node_and_restores_owned_temp','tests/test_ci_tests.py::test_timeout_also_cleans_owned_scratch','tests/test_publication_independent.py']
    cmd=[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','--basetemp',str(temp/'pytest'),*nodes,'--junitxml',str(OUT/'du11-ff-publication-independent.xml')]
    proc=subprocess.run(cmd,cwd=snap,env=env,capture_output=True,timeout=90)
    (OUT/'du11-ff-publication-independent.log').write_bytes(proc.stdout+proc.stderr)
    receipt.update(command=cmd,returncode=proc.returncode)
    xml=ET.parse(OUT/'du11-ff-publication-independent.xml').getroot()
    receipt['suite']=(xml.find('testsuite') if xml.tag=='testsuites' else xml).attrib
    receipt['snapshot_sha256']={r:sha(snap/r) for r in RELS+[REL_TRANSPORT]}
    receipt['network_attempts']=len((root/'network.log').read_text().splitlines()) if (root/'network.log').exists() else 0
    receipt['sentinel_unchanged']=(sha(sentinel),sentinel.stat().st_mtime_ns)==sentinel_before
    receipt['archive_sha256']=hashlib.sha256(archive).hexdigest()
    receipt['owned_temp']=str(root)
receipt['owned_temp_removed']=not root.exists()
receipt['source_sha256_after']={r:sha(SOURCE/r) for r in RELS+[REL_TRANSPORT]}
receipt['source_unchanged']=before==receipt['source_sha256_after']
receipt['wall_seconds']=round(time.monotonic()-start,2)
(OUT/'du11-ff-publication-independent-run.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print(json.dumps({k:receipt[k] for k in ('returncode','suite','ci_table','network_attempts','owned_temp_removed','source_unchanged','wall_seconds')}))
