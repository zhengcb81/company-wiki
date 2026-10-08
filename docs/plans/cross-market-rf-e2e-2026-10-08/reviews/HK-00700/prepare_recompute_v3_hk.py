"""Prepare reviewer-owned v3 reuse of the previously independently authored audit."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'recompute_hk.py').read_text(encoding='utf-8')
s=s.replace("m=load(EX/'manifest.json');OUT=Path(m['output_root']);SKILL=Path(m['skill_root'])", "old_m=load(EX/'manifest.json');m=load(EX/'manifest_v3.json');OUT=Path(m['output_root']);SKILL=Path(old_m['skill_root'])")
s=s.replace("REPLAY=OUT.parent/'review-HK-00700-rf_hk_independent_review'", "REPLAY=OUT.parent/'review-HK-00700-rf_hk_independent_review-v3'")
s=s.replace("OUT/'snapshot-v2.json'", "OUT/'snapshot.json'")
s=s.replace("HERE/'independent_calculations.json'", "HERE/'recheck_v3_independent_calculations.json'")
(HERE/'recompute_v3_hk.py').write_text(s,encoding='utf-8')
print('Prepared own reviewer calc, independent TEMP directory and v3 output names')
