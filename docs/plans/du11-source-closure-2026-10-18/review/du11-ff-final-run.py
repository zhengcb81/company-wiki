"""Archive-bound independent checks. No credentials, production data, or network."""
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

OUT = Path(__file__).resolve().parent
FF = Path('C:/Users/郑曾波/.codex/worktrees/du11-ff-reception/filing-fetch')
CWP = Path('C:/Users/郑曾波/.codex/worktrees/du11-extractive-runtime/company-wiki')
OWN = [FF/'scripts/transcript_tool_transport.py', FF/'tests/test_du11_verified_reader_revalidation.py', CWP/'src/company_wiki/source_catalog/source_reader.py', CWP/'src/company_wiki/source_catalog/source_reader_cli.py']
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def git(repo, args):
    p = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, check=True, timeout=30)
    return p.stdout

def archive(repo, paths):
    return git(repo, ['archive', '--format=tar', 'HEAD', *paths])

def extract(raw, dest):
    with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
        for member in tf.getmembers():
            target=(dest/member.name).resolve()
            assert target.is_relative_to(dest.resolve()), 'archive path escaped'
            assert member.isfile() or member.isdir(), 'unsupported archive entry'
        tf.extractall(dest, filter='data')

start = time.monotonic()
receipt = {'ff_head':git(FF,['rev-parse','HEAD']).decode().strip(), 'cwp_head':git(CWP,['rev-parse','HEAD']).decode().strip(),
           'source_sha256': {str(p):digest(p) for p in OWN}}
before = {str(p):p.read_bytes() for p in OWN}
with tempfile.TemporaryDirectory(prefix='du11-ff-final-root-') as temp:
    root=Path(temp); snap=root/'ff'; snap.mkdir()
    runtime=root/'tmp';runtime.mkdir()
    sentinel=root/'sentinel';sentinel.write_bytes(b'owned baseline')
    sentinel_before=(sentinel.read_bytes(), sentinel.stat().st_mtime_ns)
    ff_archive=archive(FF,['scripts','pyproject.toml','tests/test_du11_transcript_reuse_contract.py','tests/test_du11_transcript_reuse_support.py'])
    extract(ff_archive,snap)
    for rel in ['scripts/transcript_tool_transport.py','tests/test_du11_verified_reader_revalidation.py']:
        (snap/rel).write_bytes((FF/rel).read_bytes())
    (snap/'tests/test_final_independent.py').write_bytes((OUT/'du11-ff-final-controls.py').read_bytes())
    cwp_archive=archive(CWP,['src','pyproject.toml'])
    cwp_snap=root/'cwp';cwp_snap.mkdir();extract(cwp_archive,cwp_snap)
    for rel in ['src/company_wiki/source_catalog/source_reader.py','src/company_wiki/source_catalog/source_reader_cli.py']:
        (cwp_snap/rel).write_bytes((CWP/rel).read_bytes())
    cwp_tar=root/'current-cwp.tar'
    with tarfile.open(cwp_tar,'w') as tf:
        tf.add(cwp_snap/'src',arcname='src');tf.add(cwp_snap/'pyproject.toml',arcname='pyproject.toml')
    guard=root/'guard';guard.mkdir()
    (guard/'sitecustomize.py').write_text('''import os,sys,subprocess
from pathlib import Path
_guard=Path(__file__).parent

def audit(event,args):
    if event in {"socket.connect","socket.getaddrinfo","socket.gethostbyname","socket.gethostbyaddr"}:
        with open(os.environ["DU11_NETWORK_LOG"],"a",encoding="utf8") as f:f.write(event+"\\n")
        raise RuntimeError("offline network guard")
sys.addaudithook(audit)
_original=subprocess.Popen
class GuardedPopen(_original):
    def __init__(self,*args,**kwargs):
        env=kwargs.get("env")
        if env is not None:
            env=dict(env);env["PYTHONPATH"]=str(_guard)+os.pathsep+env.get("PYTHONPATH","")
            kwargs["env"]=env
        super().__init__(*args,**kwargs)
subprocess.Popen=GuardedPopen
''',encoding='utf8')
    env={k:os.environ[k] for k in ['SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','SYSTEMDRIVE'] if k in os.environ}
    env.update({'USERPROFILE':str(root),'TEMP':str(runtime),'TMP':str(runtime),'PYTHONDONTWRITEBYTECODE':'1','PYTHONUTF8':'1',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONPATH':os.pathsep.join([str(guard),str(snap/'scripts'),str(snap/'tests')]),
        'DU11_CWP_TAR':str(cwp_tar),'DU11_ACTUAL_RECEIPT':str(OUT/'du11-ff-final-actual.json'),
        'DU11_NETWORK_LOG':str(root/'network.log')})
    command=[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','--basetemp',str(runtime/'pytest'),
        'tests/test_du11_verified_reader_revalidation.py','tests/test_final_independent.py',
        '--junitxml',str(OUT/'du11-ff-final.xml')]
    if '--actual-only' in sys.argv:
        command[command.index('tests/test_du11_verified_reader_revalidation.py'):command.index('--junitxml')] = ['tests/test_final_independent.py::test_current_real_hk_reader_to_ff_reuse_and_legacy_receipt']
    receipt['command']=command
    result=subprocess.run(command,cwd=snap,env=env,capture_output=True,timeout=150)
    (OUT/'du11-ff-final.log').write_bytes(result.stdout+result.stderr)
    receipt['returncode']=result.returncode
    xml=ET.parse(OUT/'du11-ff-final.xml').getroot()
    receipt['suite']=(xml.find('testsuite') if xml.tag=='testsuites' else xml).attrib
    receipt['network_attempts']=len((root/'network.log').read_text().splitlines()) if (root/'network.log').exists() else 0
    receipt['sentinel_unchanged']=(sentinel.read_bytes(),sentinel.stat().st_mtime_ns)==sentinel_before
    receipt['tested_archive_sha256']={'ff':hashlib.sha256(ff_archive).hexdigest(),'cwp_head_base':hashlib.sha256(cwp_archive).hexdigest(),'cwp_with_reader_overlays':digest(cwp_tar)}
    receipt['snapshot_overlay_sha256']={str(p):digest((snap if p.is_relative_to(FF) else cwp_snap)/p.relative_to(FF if p.is_relative_to(FF) else CWP)) for p in OWN}
    receipt['owned_temp']=str(root)
receipt['owned_temp_removed']=not root.exists()
receipt['input_sources_unchanged']={str(p):p.read_bytes()==before[str(p)] for p in OWN}
receipt['wall_seconds']=round(time.monotonic()-start,2)
(OUT/'du11-ff-final-run.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print(json.dumps({k:receipt[k] for k in ['returncode','suite','network_attempts','owned_temp_removed','wall_seconds']}))

