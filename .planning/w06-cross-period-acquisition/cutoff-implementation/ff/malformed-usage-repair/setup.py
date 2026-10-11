"""TDD setup for independently found malformed stdout/verified usage erasure."""
import hashlib
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
ROOT = Path('C:/Users/郑曾波/Projects/company-wiki')
FREEZE = ROOT / '.planning/w06-cross-period-acquisition/cutoff-implementation/product-freeze.json'
freeze = json.loads(FREEZE.read_text(encoding='utf-8'))
TREE = Path(freeze['roots']['ff'])
PLAN = TREE / '.planning/w06-cutoff-result'
snapshot = []
for item in freeze['files']:
    path = Path(freeze['roots'][item['repository']]) / item['path']
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != item['sha256']:
        raise RuntimeError('Original product freeze drift before independent finding repair')
    snapshot.append(item)
(HERE / 'before.json').write_text(json.dumps({'schema_version': 'malformed-usage-repair-before/1', 'old_freeze_sha256': hashlib.sha256(FREEZE.read_bytes()).hexdigest(), 'files': snapshot}, ensure_ascii=False, indent=2), encoding='utf-8')
with (PLAN / 'task_plan.md').open('a', encoding='utf-8') as stream:
    stream.write('''

## E — 独立验收 malformed stdout 用量保真共因修复

2026-10-11 ROOT重新打开本线；旧134/4与freeze不覆盖。独审三个向量stdout {broken-json/[]/null，stderr当前request完整usage1次987bytes；API成功解析usage后JSONdecode/non-dict再用空receipt覆写，实际用量丢失。
写集仍仅现有FF five-file；实际产品只transport、实际测试只launch contract，ET冻结全部不改。先追加3个正规业务RED，随后_et_result在实际receipt解析后建立一个局部共用unavailable投影；每次只parse usage一次，所有已收到receipt后的失败都消费同一validated snapshot，不能因正文异常重置。pre-receipt transport异常仍unknown，未知/污染usage不得冒complete。无新增身份复验/门禁。
测试节点：3RED→共用实现→一次FF5文件集中责任/lint/diff；不重复41/ET全部/原matrix180s或CaseSpec期待。新central证据ff/malformed-usage-repair/；新product-freeze-v2由总作者封存，旧文件原SHA保留。独立审查agent仅集中复验。Next Step：E业务RED直接实施，不等小节点签收。
''')
with (PLAN / 'findings.md').open('a', encoding='utf-8') as stream:
    stream.write('\nE根因：用量来自stderr、stdout文档合法性独立。_et_result582已解析合格usage，590/598错误分支再_parse空receipt覆盖，606又重复parse同receipt。失败信息和用量应共享一份已验snapshot；错误内容不意味着未知网络用量。独审probe-result/trace保留且只读。\n')
with (PLAN / 'progress.md').open('a', encoding='utf-8') as stream:
    stream.write('\nE启动：ROOT独审3FAIL（malformed stdout+complete bound stderr）；先检查旧8产品SHA一致，ET3不改，旧freeze e13ee23..留证。无网络/keys/config/raw/Git写。\n')
test = TREE / 'tests/test_transcript_launch_contract.py'
source = test.read_text(encoding='utf-8')
source += '''

@pytest.mark.parametrize("stdout", [b"{broken-json", b"[]", b"null"])
def test_malformed_stdout_preserves_independently_verified_usage(
    tmp_path, monkeypatch, stdout,
):
    receipt = {"schema_version": "earnings-retrieval-usage/1", "request_id": "w07",
               "usage_complete": True,
               "usage": {"requests_used": 1, "response_bytes_used": 987}}
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return stdout, json.dumps(receipt).encode("utf-8"), 0
    monkeypatch.setattr(transport_module, "_run_bounded_json", run)
    transport = _transport(tmp_path)
    monkeypatch.setattr(transport, "_et_environment", lambda: ({}, None))
    public = transport._et_result(request=_request(), limits=_limits())
    assert public["status"] == "provider_unavailable"
    assert public["reason"] == "provider_result_invalid"
    assert public["provider_requests"] == 1
    assert public["provider_response_bytes"] == 987
    assert public["provider_usage_complete"] is True
    assert public["provider_started"] is True
    assert public["provider_calls"] == 1
    assert public["retryable"] is False
    assert "source_ref" not in public
    assert len(calls) == 1
'''
test.write_text(source, encoding='utf-8', newline='\n')
print(json.dumps({'old_freeze_unchanged': True, 'et_product_changes': 0, 'test_file_written': 1, 'product_changes': 0}))
