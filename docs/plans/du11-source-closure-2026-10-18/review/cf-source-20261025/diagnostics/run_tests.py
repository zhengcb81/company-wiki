"""Bounded ROOT test execution with an owned, restored temporary root."""
import json,os,shutil,stat,subprocess,sys,tempfile,time
from pathlib import Path
root=Path(__file__).resolve().parents[2];scratch=Path(__file__).resolve().parent
node=root/'docs/plans/du11-source-closure-2026-10-18/review/cf-source-20261025'
name=sys.argv[1];tmp=Path(tempfile.mkdtemp(prefix=name+'-',dir=scratch))
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHONIOENCODING='utf-8',TEMP=str(tmp),TMP=str(tmp))
start=time.monotonic()
try:
 cmd=[sys.executable,'-X','utf8','-m','pytest','-q','-p','no:cacheprovider',*sys.argv[2:]]
 p=subprocess.run(cmd,cwd=root,env=env,capture_output=True,encoding='utf-8',timeout=180)
 (node/(name+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8')
finally:
 assert tmp.resolve().parent==scratch.resolve()
 for f in tmp.rglob('*'):f.chmod(stat.S_IREAD|stat.S_IWRITE|(stat.S_IEXEC if f.is_dir() else 0))
 shutil.rmtree(tmp)
result={'command':cmd,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3),'temporary_root_restored_absent':not tmp.exists(),'paid_calls':0,'downloads':0}
(node/(name+'-receipt.json')).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));print((p.stdout+p.stderr)[-4500:]);sys.exit(p.returncode)
