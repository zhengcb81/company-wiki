"""Stage minimal producer and recognition changes after witnessed RED runs."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
RF = Path('C:/Users/郑曾波/Projects/revenue-forecast')
SID = Path('C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite')
stage = HERE / 'second_fix_stage'
stage.mkdir(exist_ok=True)

def replace_exact(text, old, new):
    assert text.count(old) == 1, f'expected exactly one occurrence of {old[:80]!r}'
    return text.replace(old, new)

sid = (SID / 'src/cninfo_api.py').read_text(encoding='utf-8')
sid = replace_exact(sid,
    '# Cninfo periodic announcements category (annual/semi/quarterly all share it).',
    '# Official periodic categories differ. Quarterly discovery covers both Q1\n'
    '# and Q3; existing title/period filters select the requested report.')
sid = replace_exact(sid, '"semi_annual_report": "category_ndbg_szsh",',
    '"semi_annual_report": "category_bndbg_szsh",')
sid = replace_exact(sid, '"quarterly_report": "category_ndbg_szsh",',
    '"quarterly_report": "category_yjdbg_szsh;category_sjdbg_szsh",')
(stage / 'cninfo_api.py').write_text(sid, encoding='utf-8')

constants = (RF / 'scripts/contracts/constants.py').read_text(encoding='utf-8')
constants = replace_exact(constants, 'RECOGNITION_TIMING = {"point_in_time", "over_time"}',
    'RECOGNITION_TIMING = {"point_in_time", "over_time", "mixed"}')
constants = replace_exact(constants, 'PRESENTATIONS = {"gross", "net"}',
    'PRESENTATIONS = {"gross", "net", "mixed"}')
(stage / 'constants.py').write_text(constants, encoding='utf-8')

segments = (RF / 'scripts/forecast/segments.py').read_text(encoding='utf-8')
before = '    if timing == "over_time":\n'
addition = '''    if timing == "mixed" or presentation == "mixed":
        # These values describe a published aggregate, not an activity-level
        # recognition algorithm. Never invent one uniform timing/principal
        # policy for a segment whose component policies differ.
        require(
            mode == "modeled_as_recognized",
            f"{name} mixed accounting requires already recognized revenue",
        )
        scenarios = segment.get("scenarios")
        require(
            isinstance(scenarios, dict) and set(scenarios) == set(SCENARIOS)
            and all(isinstance(item, dict)
                    and item.get("model") in {"direct_growth", "direct_revenue"}
                    for item in scenarios.values()),
            f"{name} mixed accounting requires direct_growth/direct_revenue",
        )
        boundary = recognition.get("aggregation_boundary")
        require(
            isinstance(boundary, str) and bool(boundary.strip()),
            f"{name} mixed accounting requires aggregation_boundary",
        )
        transforms = {"progress_measure", "progress_parameter_ids", "lag_years",
                      "carry_in_parameter_ids"} & recognition.keys()
        require(
            not transforms,
            f"{name} mixed accounting cannot contain recognition transforms: "
            f"{', '.join(sorted(transforms))}",
        )
'''
segments = replace_exact(segments, before, addition + before)
(stage / 'segments.py').write_text(segments, encoding='utf-8')
print('staged 3 responsibility files')
