import pathlib,sys,runpy,hashlib
repo=pathlib.Path(sys.argv[1]).resolve(); test=pathlib.Path(sys.argv[2]).resolve()
scripts=repo/'skills/revenue-forecast-audit/scripts';sys.path.insert(0,str(scripts))
import summary_checkpoint_observations as c
assert pathlib.Path(c.__file__).resolve().parent==scripts
print('BOUND_HELPER '+str(c.__file__)+' RAW_SHA256='+hashlib.sha256(pathlib.Path(c.__file__).read_bytes()).hexdigest(),file=sys.stderr)
sys.argv=[str(test)];runpy.run_path(str(test),run_name='__main__')
