import ctypes as C
from ctypes import wintypes as W
import json,os,runpy,sys
from pathlib import Path
root=Path(__file__).resolve().parents[4]
script=root/'docs/plans/du11-source-closure-2026-10-18/review/skill-sync-root-cause-20261026/diagnose_runtime.py'
observation=runpy.run_path(str(script))['observe']()
k=C.WinDLL('kernel32',use_last_error=True);a=C.WinDLL('advapi32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
k.CloseHandle.argtypes=[W.HANDLE];k.LocalFree.argtypes=[C.c_void_p]
k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)]
a.OpenProcessToken.argtypes=[W.HANDLE,W.DWORD,C.POINTER(W.HANDLE)]
a.GetTokenInformation.argtypes=[W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.POINTER(W.DWORD)]
a.ConvertSidToStringSidW.argtypes=[C.c_void_p,C.POINTER(W.LPWSTR)]
a.IsTokenRestricted.argtypes=[W.HANDLE]
def token(pid):
 process=k.OpenProcess(0x1000,False,pid)
 if not process:return {'pid':pid,'query_error':C.get_last_error()}
 try:
  name=C.create_unicode_buffer(32768);n=W.DWORD(len(name));k.QueryFullProcessImageNameW(process,0,name,C.byref(n))
  t=W.HANDLE()
  if not a.OpenProcessToken(process,8,C.byref(t)):return {'pid':pid,'query_error':C.get_last_error()}
  try:
   need=W.DWORD();a.GetTokenInformation(t,25,None,0,C.byref(need));buf=C.create_string_buffer(need.value)
   if not a.GetTokenInformation(t,25,buf,need,C.byref(need)):raise C.WinError(C.get_last_error())
   sid=C.cast(buf,C.POINTER(C.c_void_p))[0];text=W.LPWSTR()
   if not a.ConvertSidToStringSidW(sid,C.byref(text)):raise C.WinError(C.get_last_error())
   try:il=text.value
   finally:k.LocalFree(text)
   flags={}
   for key,kind in [('is_appcontainer',29),('has_restrictions',21)]:
    value=W.DWORD();size=W.DWORD()
    flags[key]=bool(value.value) if a.GetTokenInformation(t,kind,C.byref(value),C.sizeof(value),C.byref(size)) else {'query_error':C.get_last_error()}
   return {'pid':pid,'image':name.value,'integrity_sid':il,'is_token_restricted':bool(a.IsTokenRestricted(t)),**flags}
  finally:k.CloseHandle(t)
 finally:k.CloseHandle(process)
observation['independent_token_details']={'self':token(os.getpid()),'parent':token(os.getppid())}
observation['no_writer_invoked']=True
print(json.dumps(observation,ensure_ascii=True))
