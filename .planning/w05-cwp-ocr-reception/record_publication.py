"""Record exact normal publication; preserve former failure receipts."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-cwp-ocr-acceptance'
published = '8862372f714209cff1b218d77b5c4b8af6bc74dc'
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
assert head == published
target = EVIDENCE / 'publication.json'
assert not target.exists()
target.write_text(json.dumps({
    'schema_version': 'root-w05-ocr-publication/1', 'status': 'COMPLETE_WITH_SCOPE',
    'integration_commit': 'c7fb1b814e6d03a2f39d2092ab668448bca7e24d',
    'main_merge': 'ae0ca0d3c03f4a974ff26e472860ee306959d091',
    'published_head': published, 'remote_head_verified': published,
    'normal_hooks': True, 'push_gate': {'passed': 3257, 'seconds': 224.81},
    'github_ci': {'id': 38140484490, 'head_sha': published,
                  'status': 'completed', 'conclusion': 'success',
                  'url': 'https://github.com/zhengcb81/company-wiki/actions/runs/38140484490',
                  'verification': 'GitHub public REST API; no credentials read'},
    'focused_preallocation_pass': 54, 'independent_preallocation_pass': 34,
    'existing_fast_smoke_pass': 148, 'real_e2e_seconds': 83.006,
    'originals_config_unchanged': True, 'scratch_restored': True,
    'provider_calls': 0, 'llm_calls': 0, 'fees_usd': 0,
    'scope': 'Windows source/resource/locator; POSIX static only; no peak RSS/full recall/research certification',
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
prefix = '''## ROOT 完成 — 正常主线并入、远端与 CI 已确认 — 2026-10-11

A/B/C/D均完成。正常ROOT merge commit c7fb1b81，master merge ae0ca0d3，已发布8862372f；精确远端SHA相同，现有push3257PASS/224.81秒，GitHub CI38140484490同SHA success。冻结publication.json记录全部范围与实际验收；旧pending勾选/失败记录仅作历史，不再作为待办执行。

原件/config未改；无provider/LLM费用。后续W06测试工具或W04候选修复不重开本卡、不重复整套OCR或3257全集；新的受影响变更按当前现有测试映射检查。

'''
for name in ('task_plan.md', 'findings.md', 'progress.md'):
    p = ROOT / '.planning/w05-cwp-ocr-reception' / name
    old = p.read_bytes()
    assert prefix.encode('utf-8') not in old
    p.write_bytes(prefix.encode('utf-8') + old)
print('OCR exact publication receipt and three closed PWF files recorded')
