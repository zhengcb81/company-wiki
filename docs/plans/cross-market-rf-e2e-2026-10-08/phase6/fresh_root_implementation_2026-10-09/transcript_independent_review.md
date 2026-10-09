# W07 两仓独立复核 — 暂缓验收

日期：2026-10-09。审查对象：FF `f2182732f1ad8363b2d10d947042c924319db0f5`，ET `1d03de61e681c3769102d634f6dfb45498044962`。FF worktree：`C:/Users/郑曾波/AppData/Local/Temp/ff-fresh-transcript-launch-20261009`；ET worktree：`C:/Users/郑曾波/AppData/Local/Temp/et-fresh-transcript-launch-20261009`。

结论：**暂缓 W07 acceptance**。关键正常路径通过离线复核，但存在一个可复现 P1 凭证泄漏边界缺陷，以及一个 P2 受污染用量回执仍被声明完整的缺陷。审查员没有修改两仓源码、配置、原文、已有 PWF，也没有 commit、merge、push、install。最终两仓 `git status --short` 均为空。本报告是唯一 CWP 写入。

## 实际执行与证据范围

只使用内存构造的 synthetic key、独占 TEMP 夹具、既有 FakeSession/private launcher seam 和精确提交源码。没有读取生产 key 文件、ET config 或完整主机环境；没有真实供应商请求、外部 HTTP 或收费。下文 `http_calls=1`、`provider_requests=1` 全部表示离线 fake transport 的计量，不能当作真实鉴权或 entitlement 证据。

亲自执行的三个 pytest 命令均在普通 OS 权限下完成，未跳过：

| 仓库/检查 | 结果 |
| --- | --- |
| FF `tests/test_transcript_launch_contract.py`，显式 `W07_ET_TOOL` 指向接受审查的 ET worktree | 29 passed，0 skipped，3.19s |
| ET `tests/test_launch_capability_contract.py` | 9 passed，0 skipped，5.11s |
| FF `tests/test_transcript_companion_transport.py::test_real_cwp_cli_import_and_unknown_publication_replay`，显式 `COMPANY_WIKI_SOURCE_ROOT` 指向 CWP `src` | 1 passed，0 skipped，4.25s |

调用形态：`python -m pytest <上述目标> -q -rs --tb=short -p no:cacheprovider --basetemp <独占 TEMP/fixtures>`；FF 新合同模块设置非秘密的 `W07_ET_TOOL`。测试子进程环境只保留运行必需 OS 变量，设置 `PYTHONDONTWRITEBYTECODE=1`、`PYTHONUTF8=1` 及 synthetic profile。未 dump 环境。首次 sandbox 运行因嵌套子进程 TEMP 写入 WinError 5 阻断，不能计作产品失败；随后按既有任务授权使用 `require_escalated` 跑相同离线范围，得到上表结果，没有绕过审查拒绝。

另一个亲跑 TEMP bridge 将 FF 所选配置的 `fmp_api_key_file: keys/selected.key` 解析到真实 ET `transcript_tool.main` 子进程，继而运行真实 supervisor/worker 和 private fake HTTP launcher。bridge 在子进程中断言 runtime 参数收到预期 synthetic key、key 不在 FF stdin/argv、`FMP_API_KEY_FILE` 已剥离。结果：

```json
{"cwp_env_stripped":true,"et_runtime_fixture_clean":true,"provider_requests":1,"secret_in_result":false,"status":"fetched","usage_complete":true}
```

实际 CWP CLI 重放检查验证原文 JSON 字节保持、SourceRef 重用、未知 publication 未变为已验证、第二次不再调用 ET fixture。它使用 synthetic CWP 目录与配置，不写生产来源库。

FF handoff 中的 `203 PASS / 1 existing skip / 39 subtests`、最终 wire `42 PASS / 0 skip`、ET `116 PASS` 是实现者 receipt；审查员读取了精确提交中的 `green_summary.json`，**没有冒称亲跑这些完整套件**。

## P1：合法 JSON 字符转义绕过两仓泄漏检查，并可进入公开 reason

位置：ET `transcript_api.py:673-680,710,780`；FF `scripts/transcript_tool_transport.py:80-94,492-531`。

ET 检测只在 `json.loads` 前查 `api_key.encode()` 和 `json.dumps(api_key, ensure_ascii=True)` 的一种字节表现。合法 JSON 允许将 ASCII 也写成 `\uXXXX`。当 provider JSON 的 `content` 把 synthetic key 全部用此形式编码，原始 payload 不含明文 key，但 `json.loads` 会恢复 key。ET v1 返回 `fetched` 并在公开 `content_utf8` 中暴露它。ET v2 返回 `fetched`，将同一原始 JSON 放进 base64 payload；FF 只解 base64 后再次做相同字节搜索，未解 provider JSON 的字符串，因此 `_credential_exposed` 返回 false。该原文可继续被 CWP importer 保存并在后续规范化中解出 key。此问题不需要无效 JSON、供应商网络或改写原文。

FF 外层 stdout 也有同一缺口：`_credential_exposed` 虽 `json.loads(stdout)`，却只取 `provider_payload_base64`，不检查其余已解码字符串。一个合法 JSON failure 的 `error_code` 若以 `\uXXXX` 表达 synthetic 纯字母数字 key，保护函数不拒绝；随后 `_et_result` 解码它并通过 `isalnum()` 判定，将其复制进公开 `reason`。这构成明确输出泄漏。

最小反例可在 ET worktree 执行；脚本只用内存 synthetic key 和 FakeSession，FF 只有构造目录/假 tool 文件写在 TEMP。先在普通 OS shell 中设置 `PYTHONDONTWRITEBYTECODE=1`。以下构造值是专用测试哨兵，绝非真实 API key，也未从主机取得：

```python
import os, sys, json, time, tempfile
from pathlib import Path
safe = {n: os.environ[n] for n in
        ('SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'COMSPEC', 'PATHEXT')
        if n in os.environ}
os.environ.clear()
os.environ.update(safe)
sys.dont_write_bytecode = True
FF = Path('C:/Users/郑曾波/AppData/Local/Temp/ff-fresh-transcript-launch-20261009')
sys.path.insert(0, str(FF / 'scripts'))
import transcript_api as api
import transcript_tool_transport as ff
from tests.test_transcript_api import (
    make_request, FMP_URL, fmp_payload, FakeResponse, FakeSession)

key = 'independentreviewonlycredential012345'  # synthetic only
escaped = ''.join('\\u%04x' % ord(c) for c in key)
payload = json.loads(fmp_payload())
payload[0]['content'] += key
raw = json.dumps(payload).replace(key, escaped).encode()
request = make_request(provider='fmp', ticker='MSFT', exchange='NASDAQ', fiscal_quarter=3)
for include in (False, True):
    session = FakeSession({FMP_URL: FakeResponse(
        FMP_URL, raw, content_type='application/json')})
    r = api.fetch_transcript(request, fmp_api_key=key,
        include_source_payload=include, session_factory=lambda: session)
    print(json.dumps({'v2': include, 'status': r['status'],
        'raw_key_in_payload': key.encode() in raw,
        'decoded_content_contains_key': key in json.loads(raw)[0]['content'],
        'public_content_contains_key': key in r.get('content_utf8', ''),
        'ff_guard_rejects': ff._credential_exposed(json.dumps(r).encode(), b'', key)}))

root = Path(tempfile.mkdtemp(prefix='w07-independent-repro-'))
tool = root / 'never_executed.py'
tool.write_text('# injected fixture', encoding='utf-8')
t = ff.EarningsTranscriptsTransport(wiki_root=root, transcript_tool=tool,
                                    deadline=time.monotonic() + 30)
os.environ['FMP_API_KEY'] = key
receipt = {'schema_version': 'earnings-retrieval-usage/1', 'request_id': 'probe',
           'usage_complete': True,
           'usage': {'requests_used': 1, 'response_bytes_used': 12}}
out = json.dumps({'schema_version': 'earnings-transcript-result/2',
    'request_id': 'probe', 'provider': 'fmp', 'status': 'provider_error',
    'error_code': key}).replace(key, escaped).encode()
original_runner = ff._run_bounded_json
ff._run_bounded_json = lambda *a, **k: (out, json.dumps(receipt).encode(), 0)
req = {'request_id': 'probe', 'security_id': 'MSFT', 'exchange': 'NASDAQ',
       'fiscal_year': 2026, 'fiscal_quarter': 3, 'as_of_date': '2026-09-30'}
limits = {'timeout_seconds': 10, 'max_bytes': 1000000, 'max_cost_usd': '0.00'}
r = t._et_result(request=req, limits=limits)
print(json.dumps({'reason_contains_key': key in r.get('reason', ''),
    'reason_is_leak_classification': r.get('reason') == 'provider_credentials_leaked',
    'provider_requests': r.get('provider_requests')}))
ff._run_bounded_json = original_runner
```

实测安全摘要，未打印 key 或 provider payload：

```json
{"et_unicode_escape_v1":{"decoded_content_contains_key":true,"ff_guard_rejects":true,"http_calls":1,"raw_key_in_payload":false,"status":"fetched","v1_public_content_contains_key":true},"et_unicode_escape_v2":{"decoded_content_contains_key":true,"ff_guard_rejects":false,"http_calls":1,"raw_key_in_payload":false,"status":"fetched","v1_public_content_contains_key":false},"ff_unicode_error_code":{"provider_requests":1,"reason_contains_key":true,"reason_is_leak_classification":false}}
```

统一根因是**检测字节表现早于协议解码，却在后续将解码后的值输出或保存**。base64 解码不是 JSON 字符串解码；canonical JSON encoding 也不是所有合法 JSON 表现的集合。

所需修复边界：保留有界原始字节检查；在解码外层 stdout/stderr JSON 与有界 provider JSON 后，检查所有已解码字符串（含对象键、值、数组项）是否含已知凭证，命中则拒绝完整原文与 DTO。不得 scrub/rewrite 敏感字节后另存“干净原件”。公开失败 code 应采用已知合同枚举；`isalnum()` 不足以授权任意 child-controlled text 进入公开 reason。此反例要求拒绝状态 `provider_credentials_leaked`，且公开 DTO 无已知 key、无 provider payload；原文不得导入。

## P2：完整 JSON 形式的受污染 receipt 仍被声明 usage_complete

位置：FF `scripts/transcript_tool_transport.py:60-76,492-497`。

`_provider_usage` 仅核对 schema/request_id/complete 与两个非负计数，允许额外字段；`_et_result` 先保存其数值，再做泄漏检测。因此一个本身包含 key 的合法 receipt（例如在外层多一个 `detail`）会被识别为泄漏，却依然发布 `provider_requests=1`、`provider_started=true`、`provider_usage_complete=true`。这不符合 handoff 的“contaminated receipt stays unknown”合同。已有测试只把 key 直接追加到 stderr，形成无法解析的 JSON，没覆盖合法 JSON contamination。

以上脚本初始化之后，复现追加代码如下；runner 保证只返回离线内存数据，不启动子进程：

```python
contaminated = dict(receipt, detail=key)
ff._run_bounded_json = lambda *a, **k: (
    json.dumps({'status': 'provider_error', 'error_code': 'provider_failure'}).encode(),
    json.dumps(contaminated).encode(), 0)
r = t._et_result(request=req, limits=limits)
print(json.dumps({name: r.get(name) for name in
    ('reason', 'provider_requests', 'provider_started', 'provider_usage_complete')}))
ff._run_bounded_json = original_runner
```

实测摘要：

```json
{"provider_requests":1,"provider_started":true,"provider_usage_complete":true,"reason":"provider_credentials_leaked"}
```

所需修复：stdout contamination 但独立干净 receipt 时可保留已测用量；**receipt 本身污染**时计数应 `null`、`provider_started=null`、`provider_usage_complete=false`，不能造 `0`，也不能宣称完整。对 stderr 已解码 JSON 的检测应与 P1 使用同一边界，不只处理附加字节。建议新增原始/转义 `detail` 的合法 JSON 反例，与干净 receipt 的 stdout 泄漏保留用量测试成对验证。

## 已验证的通过项与后续边界

HKEX、unknown TOKYO 与 NASDAQ 大小写在真实 ET CLI 的离线新合同测试中分类正确；不支持市场/交易所与缺凭证均有准确预检零用量。FF companion/public v2 保持成功 filing SourceRef；missing/invalid usage 保持未知；配置路径类型验证与 doctor 的新增 optional field 合同一致；显式坏文件不 fallback；ET worker 凭证桥、CWP env 剥离与真实 CWP 原文重放通过。

M3 真实鉴权/entitlement 尚未执行，应由 MAIN 使用现有配置和预算单独记录真实请求/费用。无 key、无 scope 或 synthetic provider error 均不能替代该节点。W08 既有 ChildTimeout/ChildFailed 分类不属于本报告声称已修复的范围。

修复者应先补上述有界解码与 receipt 独立污染边界，重跑最小红例及新合同模块，再交独立复核。当前通过项不消除 P1/P2，W07 保持待验收。
