# Findings — M3-USAGE lane

## 接管事实
- 前内置 agent terminal errored、无源码修改；三仓 worktree 与总卡 base 完全一致（2026-10-10 实测）。
- W06 seed 三文件为空骨架（task_plan 只有 6 行 scope/steps，findings/progress 空）。

## Phase 1 consumer map（三 Explore agent，2026-10-10）

### CWP producer（src/company_wiki/source_catalog/ = SC）
- 成功路径今天完全没有 usage：SourceEnsureResult(38-60) 只有 schema_version/status/acquisition/resolution/attempt/canonical_import(+可选 acquisition_failure)。usage 只在失败时经 attach_acquisition_failure(132-134) 发布。
- AcquisitionBudget(download_budget.py:37-48) 已有全部所需计数：response_bytes_used(entity)、wire_response_bytes_used、cost_usd_used、usage_complete、wire_usage_complete、provider_started、usage_reported。跨整个 operation 累积（discover+fetch 多次 subprocess），不是最后一次 invocation。
- adapter 子进程成功回执已含 acquisition_usage + http_wire_bytes + http_wire_usage_complete（dayu_sdk_cli.py:259-261；adapter_process.py:250-256），但在父进程边界丢弃，不进 SourceEnsureResult。
- bounded_http.py 已测 wire bytes（_record_http 111-122 按 chunk 计 wire）与 entity bytes（identity 同步、gzip/deflate 解压后）。请求/响应交换次数今天不计数。
- 安全 HTTP 观察已存在：response_observation(bounded_http.py:77-86) = status_code/mime_type/content_encoding/wire_content_length 四字段，挂在 ProviderBudgetStop.http_observation。
- 校验：validated_usage(acquisition_failure.py:29-44) 严格 3 键；validated_failure(51-66) 严格 7 键。加字段必须走 sibling/新版本。
- operation DTO：source_operation.project_operation_result → operation_projection.project_source_operation(120-145)，operation_schema_version=1.0；_contains_physical_field(56-65) 禁键名含 path/location/root/bundle。
- CLI(cli.py MAIN-owned)：ensure handler 把 caller-owned budget 藏在 args._acquisition_budget(695)，--source-ref-v2 时走 project_operation_result(1368-1375) 后 stdout JSON(1389)。成功 usage 的天然接缝在 project_operation_result 收到的完整 result payload。
- 测试基建：tests/integration/test_acquisition_failure_cli_e2e.py 已有合成 json_command_v1 provider 脚本 + 真实 CLI 子进程模式（本卡 E2E 模板）。conftest.py:30-50 默认禁 socket；真 HTTPServer 模板在 tests/support/narrative_batch_fixtures.py:68-70。
- journal(AcquisitionJournal) 不存 usage；改动它=改 schema，不做。
- official_source_flow 已有成功 usage DTO 先例（out["acquisition_usage"]）。

### FF
- v2 成功 filing 无任何 usage 字段；transcript companion 有完整先例：_TRANSCRIPT_KEYS 白名单含 provider_calls/provider_requests/provider_response_bytes/provider_usage_complete/provider_started（ff_v2_envelope.py:16-22）。
- _validated_operation(fetch_filing.py:874-888) 闭集 _SOURCE_OPERATION_FIELDS（含 acquisition_failure）——operation DTO 新字段须同步加白名单（fetch_filing.py 在本线写集内）。
- ff_provider_cause.validated_acquisition_failure 深拷贝 7 键 DTO 原样保真；garbage 静默丢弃不报错。
- FF→CWP：[python, -m company_wiki.source_catalog.cli, --config <wiki_root>/config/source_catalog.yaml, ensure, ..., --source-ref-v2]，cwd=wiki root，env=dict(os.environ)+PYTHONUTF8=1；wiki root 由 FF config/环境（CI 用 FILING_FETCH_V2_WIKI_SRC）解析。无 dotenv。
- 测试为 pytest（tools/ci_tests.py 聚焦列表）；test_failure_usage_continuity.py 用真实子进程 producer.py 模式，且不在 CI_TESTS 列表——新 m3 套件应加入。
- reuse 证明：resolution_outcome∈{reused_existing,reused_after_discovery} ⇔ download_events==0（1041-1048 强制）。

### RF
- resolve_filing_result 返回完整 v2 envelope 原样（usage stays producer-owned）；_validate_pathless_result 递归拒绝 path 类键。
- failure_observation(filing_upstream_cause.py:166-188) 是唯一投影点：upstream_cause/acquisition_failure/source_failure_reason/stage/calls/downloads/attempts。
- 成功侧无 acquisition_usage 提取（grep 证实仅失败侧 3 处）；成功 envelope 整体进 sidecar（source_preparation.py:448-449），reuse_receipt 有 download_calls/outcome。
- E2E 模板：tests/test_source_failure_observations.py:244-314 用 --filing-fetch-root 指向合成 FF root + PYTHONPATH 注入合成 reader，真实 source_preparation.py 子进程。
- RF 测试 runner 是 pytest；无 test_m3_acquisition_usage*。

### 设计要点（初定，待 INTERFACE_CHANGE.md 定稿）
- 新 sibling：acquisition-observation/1，挂 operation DTO（成功/gap/失败都可带）；键名避开 path/location/root/bundle。
- wire bytes 与 entity bytes 分开；cost_usd null=未知（无 provider 回执），有回执才是观察值；usage_complete=false ⇒ 下界。
- metadata/body 交换次数需新增计数（bounded_http 每响应计一次 → budget.http_exchanges_used）。
