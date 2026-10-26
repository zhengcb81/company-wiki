from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util,errno,hashlib,json,os,socket,sys,time
root=Path(__file__).resolve().parents[3]
out=Path(__file__).parent
source=root/'cw-ff19/tools/sync_installs_b3.py'
spec=importlib.util.spec_from_file_location('independent_installer',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
results=[]
def snap(path):return {p.relative_to(path).as_posix():(p.read_bytes().hex(),p.stat().st_mtime_ns) for p in path.rglob('*') if p.is_file()}
def deny_net(*a,**kw):raise AssertionError('independent installer probe forbids network')
with patch.object(socket.socket,'connect',deny_net),patch('socket.create_connection',deny_net):
 with TemporaryDirectory(prefix='r19i-',dir=root) as temp:
  temporary=Path(temp);canonical=temporary/'source'
  files={'SKILL.md':b'new skill','CHANGELOG.md':b'new changelog','config/company_wiki.json':b'new template','scripts/fetch.py':b'new fetch','scripts/other.py':b'new other','references/a.md':b'ref'}
  for name,body in files.items():p=canonical/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
  m.CANONICAL=canonical
  def target(name):
   parent=temporary/name;d=parent/m.SKILL;d.mkdir(parents=True)
   for rel,body in {'SKILL.md':b'old skill','scripts/fetch.py':b'old fetch','scripts/other.py':b'owner other','notes/user.md':b'owner notes','config/company_wiki.json':b'owner config'}.items():
    p=d/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
   return parent,d
  parent,d=target('permission');before=snap(d);attempts=[];error=PermissionError(errno.EACCES,'controlled actual permission error')
  def denied_open(path,flags,mode=0o777,*a,**kw):attempts.append((str(path),flags,mode));raise error
  with patch.object(m.os,'open',denied_open),patch.object(m.os,'access',side_effect=AssertionError('permission must not be guessed as collision')):
   try:m._stage_file(d);raise AssertionError('permission swallowed')
   except PermissionError as caught:assert caught is error
  assert len(attempts)==1
  attempts.clear()
  with patch.object(m.os,'open',denied_open):result=m.sync(parent,files=['SKILL.md','scripts/fetch.py'])
  assert len(attempts)==1 and result['status']=='failed' and snap(d)==before
  assert attempts[0][1]&os.O_CREAT and attempts[0][1]&os.O_EXCL and attempts[0][2]==0o600
  results.append({'case':'PermissionError exact object and one attempt','attempts':len(attempts),'errno':error.errno,'same_exception_object':True,'target_snapshot_unchanged':True,'selected_batch_stops':True,'pass':True})
  parent,d=target('collision_limit');occupied=d/'.ff-install-aaaaaaaaaaaa';occupied.write_bytes(b'owned existing collision');before=snap(d);attempts=[];real_open=os.open
  def count_open(path,flags,*a,**kw):attempts.append(str(path));return real_open(path,flags,*a,**kw)
  with patch.object(m.uuid,'uuid4',return_value=SimpleNamespace(hex='a'*32)),patch.object(m.os,'open',count_open):result=m.sync(parent,files=['SKILL.md'])
  assert result['status']=='failed' and len(attempts)==8 and snap(d)==before
  results.append({'case':'eight real O_EXCL collisions exhaust finitely','attempts':len(attempts),'preexisting_collision_bytes_mtime_preserved':True,'target_snapshot_unchanged':True,'pass':True})
  parent,d=target('collision_recover');occupied=d/'.ff-install-aaaaaaaaaaaa';occupied.write_bytes(b'owned existing collision');before=snap(d);attempts=[];names=iter(['a'*32,'a'*32,'b'*32]);sync_calls=[];real_fsync=os.fsync
  def traced_fsync(fd):sync_calls.append(fd);return real_fsync(fd)
  with patch.object(m.uuid,'uuid4',side_effect=lambda:SimpleNamespace(hex=next(names))),patch.object(m.os,'open',count_open),patch.object(m.os,'fsync',traced_fsync):result=m.sync(parent,files=['SKILL.md'])
  after=snap(d)
  assert result['status']=='completed' and len(attempts)==3 and len(sync_calls)==1 and (d/'SKILL.md').read_bytes()==files['SKILL.md']
  assert all(after[k]==v for k,v in before.items() if k!='SKILL.md') and set(after)==set(before)
  results.append({'case':'two actual collisions then successful exclusive creation','attempts':len(attempts),'fsync_calls':len(sync_calls),'only_selected_file_changed':True,'collision_file_untouched':True,'no_new_staging_residue':True,'pass':True})
  parent,d=target('replace_failure');before=snap(d);real_replace=os.replace
  def fail_replace(src,dst):
   if Path(dst).name=='fetch.py':raise OSError(errno.EIO,'controlled replace failure')
   return real_replace(src,dst)
  with patch.object(m.os,'replace',fail_replace):result=m.sync(parent,files=['SKILL.md','scripts/fetch.py'])
  after=snap(d);assert result['status']=='partial' and result['targets'][0]['written']==['SKILL.md'] and result['targets'][0]['not_written']==['scripts/fetch.py']
  assert all(after[k]==v for k,v in before.items() if k!='SKILL.md') and set(after)==set(before)
  assert not list(d.rglob('.ff-install-*'))
  results.append({'case':'failed promotion keeps owner bytes, pending files and removes staging','status':result['status'],'written':result['targets'][0]['written'],'not_written':result['targets'][0]['not_written'],'unselected_files_and_config_unchanged':True,'no_staging_residue':True,'pass':True})
  parent,d=target('CAS');mystage=m._stage_file
  def owner_edit(parent):
   result=mystage(parent);(d/'SKILL.md').write_bytes(b'concurrent owner edit');return result
  with patch.object(m,'_stage_file',owner_edit):result=m.sync(parent,files=['SKILL.md'])
  assert result['status']=='failed' and result['targets'][0]['conflicts']==['SKILL.md'] and (d/'SKILL.md').read_bytes()==b'concurrent owner edit' and not list(d.rglob('.ff-install-*'))
  results.append({'case':'CAS still detects owner edit at new staging seam','conflict':True,'owner_edit_preserved':True,'no_staging_residue':True,'pass':True})
 evidence={'schema_version':'w19-installer-independent-probe/1','status':'PASS','runtime':sys.version,'source_lf_sha256':hashlib.sha256(source.read_bytes().replace(b'\r\n',b'\n')).hexdigest(),'results':results,'temporary_root':str(temporary),'temporary_root_absent':not temporary.exists(),'real_installation_targets_touched':False,'ACL_changes':0,'network_calls':0}
 assert evidence['temporary_root_absent']
 (out/'installer-probe-results.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(evidence,ensure_ascii=False,indent=2))
