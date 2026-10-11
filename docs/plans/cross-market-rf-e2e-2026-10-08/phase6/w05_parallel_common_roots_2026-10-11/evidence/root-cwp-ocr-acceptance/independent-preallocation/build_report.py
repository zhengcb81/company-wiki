"""Reconcile bounded independent probes and ROOT replay; no product/raw writes."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
PROJECT = Path('C:/Users/郑曾波/Projects/company-wiki')
TREE = PROJECT.parent/'_harness_worktrees/w05/cwp-ocr-root'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


probe = load(HERE/'probes.json')
assert probe['status'] == 'PASS' and len(probe['results']) == 34
assert probe['source_before'] == probe['source_after']
assert all(sha(TREE/p) == value for p, value in probe['source_after'].items())
real_dir = EVIDENCE/'preallocation-real-e2e'
real = load(real_dir/'root-real-e2e-result.json')
receipt = load(real_dir/'root-real-e2e-receipt.json')
product = load(real_dir/'product-freeze.json')
assert real['status'] == 'COMPLETED' and receipt['status'] == 'PASS' and receipt['exit_code'] == 0
assert product['before'] == product['after'] and product['unchanged']
assert all(sha(TREE/p) == value for p, value in product['after'].items())
assert receipt['input_before'] == receipt['input_after'] and receipt['raw_config_unchanged']
assert len(receipt['input_before']) == 5
assert receipt['scratch_before'] == receipt['scratch_after'] == 'absent'
assert real['baseline_match']['lines_compared'] == 22 and real['baseline_match']['text_box_confidence_exact']
assert real['replay']['fresh_adapter'] and real['replay']['exact_match']
assert len(real['slide7']['recovered_lines']) == 2
assert real['slide7']['recovered_confidences'] == [0.98912,0.99044]
assert all(p['status'] == 'COMPLETED' and p['elapsed_seconds'] < 85 for p in real['phases'].values())
previous_real = load(EVIDENCE/'root-real-e2e-result.json')
for key in ('recovered_lines','recovered_boxes','recovered_confidences','recovered_locators'):
    assert real['slide7'][key] == previous_real['slide7'][key], key
assert real['source_read']['via'] == 'SourceVersionReader.open_version'
for key in ('project_network_calls','project_provider_calls','project_llm_calls','cost_usd'):
    assert receipt[key] == 0
assert real['network_calls'] == real['paid_calls'] == 0

preserved = []
for folder in ('independent','independent-post-deadlock'):
    manifest = load(EVIDENCE/folder/'manifest.json')
    for record in manifest['files']:
        actual = sha(EVIDENCE/folder/record['path'])
        assert actual == record['sha256'], (folder,record['path'])
        preserved.append({'path':folder+'/'+record['path'],'sha256':actual})
for name in ('root-real-e2e-original-fail-result.json','root-real-e2e-original-fail-receipt.json','root-real-e2e-original-fail.log'):
    path = EVIDENCE/name
    relative = path.relative_to(PROJECT).as_posix()
    committed = hashlib.sha256(subprocess.check_output(['git','show','c145da9b:'+relative],cwd=PROJECT)).hexdigest()
    assert committed == sha(path)
    preserved.append({'path':name,'sha256':committed,'commit':'c145da9b'})

red = EVIDENCE/'preallocation/red.log'
assert '7 failed, 30 deselected' in red.read_text(encoding='utf-8',errors='replace')
assert load(EVIDENCE/'preallocation/before.json') == load(EVIDENCE/'preallocation/after.json')
author_freeze = load(EVIDENCE/'preallocation/freeze.json')
assert author_freeze['legal_before_after_equal'] and author_freeze['cases'] == 15
assert all(sha(TREE/p) == value for p,value in author_freeze['source_sha256'].items())
evidence_paths = ['preallocation/report.md','preallocation/freeze.json',
    'preallocation/red.log','preallocation/green-attempt.log','preallocation/green.log','preallocation/ruff.log',
    'preallocation/before.json','preallocation/after.json',
    'preallocation-real-e2e/root-real-e2e-result.json','preallocation-real-e2e/root-real-e2e-receipt.json',
    'preallocation-real-e2e/product-freeze.json',
    'independent-post-deadlock/review.json','independent-post-deadlock/manifest.json']
record = {
    'schema_version':'root-w05-ocr-independent-preallocation-acceptance/1',
    'date':'2026-10-11', 'status':'PASS_WITH_SCOPE',
    'reviewer_is_product_non_author':True,
    'merge_recommendation':'Accept final frozen Windows native boundary and production ROI preallocation resource contract. No P1 defect found in this scope',
    'tree':str(TREE), 'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=TREE,text=True).strip(),
    'product_sha256':probe['source_after'],
    'independent_execution':{'vectors':34,'passed':34,'seconds':probe['seconds'],
        'budgets_and_zero_renderer_vectors':6,'render_and_inference_failed_charge_vectors':2,
        'mode_transform_reference_vectors':15,'mode_luminance_reference_vectors':8,
        'scan_roi_and_deadline_vectors':2,'size_only_former_oversize_canvas_vectors':1,
        'actual_ocr_repeated':False,'formal_54_repeated':False,'old_184_or_22_repeated':False},
    'root_execution_reviewed':{'formal_red':7,'focused_green':54,'focused_seconds':3.78,
        'author_15_before_after_receipts_equal':True,'ruff':'PASS',
        'real_e2e':{'status':'PASS','total_seconds':receipt['elapsed_seconds'],
            'phases':real['phases'],'phase1_native_seconds':85,'phase2_native_fallback_seconds':90,
            'per_phase_emergency_seconds':90,'outer_emergency_seconds':195,
            'product_frozen_before_after':True,'original_22_text_box_confidence_exact':True,
            'two_definitions_and_locators_equal_to_prior_pass':True,
            'recovered_confidences':real['slide7']['recovered_confidences'],
            'all_5_raw_config_before_after_sha_equal':True,
            'scratch_before_after':['absent','absent'],
            'scratch_peak_retained_bytes':receipt['scratch_peak_retained_bytes']}},
    'checks':[
        {'id':'OCR-POST-07','status':'CLOSED_FOR_FROZEN_SHA',
         'check':'Exact crop/canvas geometry planned, entire canvas including padding atomically reserved before render, native infer and retry; previous 63.984M unbudgeted allocation is rejected as size-only geometry'},
        {'id':'OCR-PRE-01','status':'PASS',
         'check':'All margin/split/upscale max_image/max_total rejection probes emit zero target render calls; prior successful attempt charges remain'},
        {'id':'OCR-PRE-02','status':'PASS',
         'check':'Render/native failure remains charged once; reserved attempts and rejected diagnostics retained'},
        {'id':'OCR-PRE-03','status':'PASS',
         'check':'Small legacy grayscale/raster reference agrees for legal modes/PNG transforms and original coordinate maps; entire padded stack reserved, not just ink pixels'},
        {'id':'OCR-PRE-04','status':'PASS',
         'check':'Source ROI scan reads alternate rows only, O(W) counts, no full grayscale/crop analysis raster, observes deadline before first column/every64 columns/at completion'},
        {'id':'OCR-PRE-05','status':'STATIC_PASS',
         'check':'Configured composer checks source dimensions and shared full-image budget before native decode/infer; recovery re-loads only already-validated source before planning. No claim of guards on arbitrary direct low-level utility callers'},
        {'id':'OCR-PRE-06','status':'PASS_WINDOWS_WITH_SCOPE',
         'check':'Existing edade53c boundary and native metadata regression remain pinned; no change to config/model/identity/approval chain; new real SourceReader+locator replay supports deployment compatibility'},
    ],
    'static_boundaries':{
        'source_max_image_pixels_default':16_000_000,'request_total_pixels_default':96_000_000,
        'transformed_output_cap_checked_before_render':True,
        'split_analysis_auxiliary':'O(W) count list plus geometry tables; no allocated W*H analysis raster',
        'scan_work':'W*ceil(H/2) sampled source pixels; current deadline checked every64 columns',
        'production_input_mode':'Already-loaded RGB source in recover_regions',
        'one_pixel_palette_converter':'Alternative utility modes only; P cache <=256; not an entire analysis image',
        'budget_rejection_counters':'Pixel/attempt counters atomic; regions_started can mark selected region even when first reservation rejects'},
    'limitations':[
        'Windows runtime only; POSIX guardian remains statically reviewed, not executed',
        'Whole-process peak RSS and maximum-size throughput were not measured; bounded source decode and successful crop/PIL/PNG buffers still consume memory',
        'Low-level build_* render utilities rely on the production planner/reservation caller; direct standalone use has no resource-limit argument',
        'Margin single-image rejection vector tests the ROI seam under newly stricter limits after source preapproval; unchanged public source cap would reject source first',
        '184 combined suite is pre-EOF-fix; 22 native suite pre-preallocation; post-preallocation evidence is54 focused+34 independent vectors+ROOT configured real replay',
        'Kernel owner death can leave bounded owned TEMP files; native tree ownership remains OSJob/guardian responsibility',
        'No certified complete OCR recall, W04 summary quality, source financial fact truth or RF economic judgment'],
    'preserved_prior_evidence':preserved,
    'reviewed_evidence_sha256':{p:sha(EVIDENCE/p) for p in evidence_paths},
    'resource_cost':{'network':0,'providers':0,'LLM':0,'cloud_ocr':0,'real_native_inference_by_reviewer':0,
        'raw_originals_opened_by_reviewer':0,'model_downloads':0,'fees_usd':0},
    'writes':{'only':str(HERE),'product_changed':False,'old_fail_changed':False,
        'config_changed':False,'shared_pwf_changed':False,'git_commit_or_install':False,
        'test_scratch_created':False,'synthetic_image_data':'In memory only; no downloaded/test data files retained'},
}
(HERE/'report.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
files = [{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(HERE.iterdir())
         if p.is_file() and p.name!='manifest.json']
(HERE/'manifest.json').write_text(json.dumps({'schema_version':'root-w05-ocr-independent-preallocation-manifest/1',
    'status':record['status'],'files':files},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':record['status'],'independent':34,'seconds':probe['seconds'],
    'real_e2e_seconds_reviewed':receipt['elapsed_seconds'],
    'phase_seconds':{k:v['elapsed_seconds'] for k,v in real['phases'].items()},
    'old_evidence_files_sha_verified':len(preserved),'retained_bytes':sum(p.stat().st_size for p in HERE.iterdir() if p.is_file())}))
