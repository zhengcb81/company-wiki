from pathlib import Path
import datetime
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = Path('C:/Users/郑曾波/Projects/revenue-forecast-du8-root-reception')
OUT = Path(__file__).resolve().parent
NAMES = '''management_targets target_measurement_comparison management_target_semantics independent_targets structure_targets du6_target_measurement_boundaries du67_typed_builder_composition output_report data_contract golden_behavior_lock single_owner_guard architecture_dependency_uses du8_target_comparison_owner du8_hand_anchors du8_target_report_roundtrip du8_owner_enforcement du5_money_unit_registry du5_root_unit_boundaries input_quantity_conversion evidence_input_lineage contract_registry schema_compatibility scenarios_confidence growth_driver_tree lint_input publication_pipeline revenue_constraints du8_root_decision_wire'''.split()

def main():
    label = sys.argv[1] if len(sys.argv)>1 else 'root-initial-concentrated'
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='rf-du8-root-') as tmp:
        temp = Path(tmp)
        sentinel = temp/'sentinel.txt'
        sentinel.write_bytes(b'owned-original-state')
        before = sentinel.stat().st_mtime_ns
        env = os.environ.copy()
        env.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                   REVENUE_PUBLICATION_REGISTRY=str(temp/'registry/publications.jsonl'))
        argv = [sys.executable,'-X','utf8','-B','-m','pytest','-q','-p','no:cacheprovider',
                '-o','addopts=','--basetemp',str(temp/'pytest'),
                *[f'tests/test_{name}.py' for name in NAMES]]
        proc = subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,
                              encoding='utf-8',errors='replace',timeout=300)
        (OUT/(label+'.txt')).write_text(proc.stdout+'\n'+proc.stderr,encoding='utf-8')
        assert sentinel.read_bytes()==b'owned-original-state'
        assert sentinel.stat().st_mtime_ns==before
        result={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'argv':argv,'exit_code':proc.returncode,'seconds':round(time.monotonic()-started,2),
                'supplier_calls':0,'sentinel_unchanged':True,
                'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    result['owned_temp_removed']=not temp.exists()
    (OUT/(label+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
    print(proc.stdout[-5000:])
    return proc.returncode

if __name__=='__main__':
    raise SystemExit(main())
