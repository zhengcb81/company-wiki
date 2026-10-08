from pathlib import Path
import json, shutil
HERE=Path(__file__).resolve().parent
OUT=Path(json.loads((HERE/'before.json').read_text(encoding='utf-8'))['output_root'])
for name in ('input.json','forecast.json','forecast.md'):
 p=OUT/name;target=OUT/(p.stem+'-v1'+p.suffix)
 if p.exists() and not target.exists():shutil.copyfile(p,target)
p=OUT/'input.json';data=json.loads(p.read_text(encoding='utf-8'))
record=next(r for r in data['management_communication_coverage'] if r['category']=='latest_investor_presentation')
record.update(status='checked',source_ids=['tencent_corporate_overview_sep2026'],conclusion='Latest dated presentation linked in official investor kit is September16 Corporate Overview, captured/read24pages. Same original also covers strategy; this does not claim the unavailable August12 Q2 earnings deck was read.')
for key in ('rationale','search_event','search_description'):record.pop(key,None)
data['data_gaps']=[g.replace('latest exact earnings PPT review incomplete.','August12 exact earnings PPT unavailable; September16 Corporate Overview is latest official dated investor-kit presentation and is checked separately.') for g in data['data_gaps']]
data['forecast_version']='2026-10-08-hk-v2'
p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'communication_coverage.json').write_text(json.dumps({'coverage':data['management_communication_coverage'],'management_targets':[],'ledger_scope':'Latest September official investor presentation and strategy are same original. No quantified recognized-revenue guidance identified in read originals; call/fullannouncementinterval still unavailable, not asserted absent.'},ensure_ascii=False,indent=2),encoding='utf-8')
print('Preserved v1 input/result and immutable snapshot; updated semantic classification only, numerical assumptions unchanged.')
