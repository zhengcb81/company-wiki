# W07 MAIN 持久配置闭合复核 — M2 接受

日期：2026-10-09。本次独立复核只覆盖 MAIN 在已接受 W07 基础上补齐的持久启动路径。旧 `transcript_residual_acceptance.md` 的 FF67/ET73 结果和旧暂缓报告均保留；没有重复整套，也没有改旧记录。

## 精确对象与结论

- FF 本地主线：`44c778b4b4f8d5deb7f376ed7016aefde5bb25c9`，`C:/Users/郑曾波/Projects/filing-fetch`。
- ET 主线：`c91f5f54bc2a24e7b5d6e648dba3f9d578f5fa52`，`C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts`。
- 本次实际 CWP CLI 源码所在 HEAD：`cba23b8eb27cf63b47517d62539b3fe3d86bd63b`，`C:/Users/郑曾波/Projects/company-wiki`。

**持久配置补齐可关闭本地工程 M2。** 默认 FF companion 路径现在能够从所选 `company_wiki.json` 找到 ET 工具与 key 文件，不依赖每次手动 export 或显式注入 transport/tool。亲跑的三仓链路确实入库原文并由 CWP reader 校验，后续两次复用未再启动 ET 或下载。M3 当前真实 FMP 鉴权、套餐 entitlement、费用和真实公司研究仍待 MAIN；本报告不冒称已执行真实供应商、RF 或整家公司流程。

本审查不做实现、commit、merge、push、安装或生产配置变更。精确远端 CI 和安装由 MAIN 另行记录，本地 M2 不替代它们。

## 本次亲跑检查

运行环境只保留 OS 必要变量，启用 `PYTHONUTF8=1`、`PYTHONDONTWRITEBYTECODE=1` 和隔离 HOME/USERPROFILE。测试不读取真实 key、完整环境、ET 生产 config 或已安装配置。所有源码只读，所有 fake key/config/raw/runtime 都在独占 TemporaryDirectory，结束后恢复为不存在。

| 检查 | 真实结果 | 证据 |
| --- | --- | --- |
| 新增持久启动 10 个用例 | **10 passed，0 skipped，0.72s** | chunk `917ce3`，exit 0 |
| 实际 FF 默认 companion facade → 所选 relative tool/key → 真实 ET CLI/supervisor/worker（私有 fake HTTP seam）→ 真实 CWP query/import/verified reader | **通过**；first=downloaded，fake GET 1，measured requests=1，response_bytes=862 | chunk `6cad61`，exit 0 |
| 第二次 fetch_if_missing 重放与第三次 reuse_only | **通过**；均 unknown_publication，相同 SourceRef，provider_calls=0，仅 CWP query/reader | 同上 |
| 原文/selected config/key/catalog 前后检查与 fixture 清理 | 字节及 mtime 均未变，ET runtime 清空，两个 TEMP 均不存在 | 同上及测试输出 |
| 退休的 independent allowed_handle_roots 夹具 | 保持拒绝，stable code=config_error，消息仍指出该字段 | 同上 |

### 新增 10 用例的实际命令

cwd 为 FF 主线。环境设置 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`，没有 `EARNINGS_TRANSCRIPTS_TOOL`、`FMP_API_KEY`、`FMP_API_KEY_FILE`；`--basetemp` 为独占空目录。每个名称都带前缀 `tests/test_transcript_launch_contract.py::`：

```text
python -X utf8 -m pytest
  test_persistent_tool_path_starts_real_child_without_launch_environment
  test_persistent_tool_user_profile_token_uses_configured_profile
  test_explicit_tool_override_preserves_precedence_over_persistent_tool
  test_bad_persistent_tool_has_measured_pre_http_zero
  test_public_loader_and_doctor_accept_persistent_tool_without_reading_key
  test_public_loader_rejects_malformed_persistent_tool
  -q -rs --tb=short -p no:cacheprovider --basetemp <owned TEMP/fixtures>
```

参数化展开后恰好 10 个。覆盖配置相对路径、USER_PROFILE、既有 override 优先级、坏路径/未知 token 的零请求有限诊断、loader/doctor 接受新 optional 字段以及无效类型拒绝。其中“starts real child”使用 TEMP 内生成的 JSON stub，确实启动子进程，**它自身不是 ET 的供应商流程**；下面另跑的三仓桥才证明真实 ET 和 CWP。

## 三仓实际链路与边界

独立桥调用的 FF 入口是实际 `fetch_filing._resolve_v2_companion`；没有传入替换 transport、显式 ET tool 或环境 key。所选 TEMP `company_wiki.json` 包含：

```json
{
  "schema_version": "1.0",
  "company_wiki_root": "<owned TEMP/wiki>",
  "earnings_transcripts_tool": "tools/bridge.py",
  "fmp_api_key_file": "keys/selected.key"
}
```

父环境明确没有三个启动/凭证变量。FF 通过正常 loader 与默认 transport 读取这份配置，tool 和 key 都按同一所选配置目录定位。tool 是仅在 TEMP 的轻量 wrapper，导入精确主线 ET `transcript_tool`，传入真实 FF 的 CLI 参数；它只为测试指定既有私有 `tests.test_retrieval_runtime:build_fake_session` seam 和合成响应。CLI、supervisor、worker、预算计量与 runtime 清理均使用实际实现。没有公开环境后门，也没有真实 HTTP。

CWP 夹具先用实际 `company_wiki.source_catalog.cli scan` 建立空来源库。随后以下子进程都经原始 FF bounded transport 实际执行；观察 wrapper 只记录固定模块名和 exit code，调用真实 transport，不替换其返回：

| 第一次调用 | 实际 exit code |
| --- | --- |
| CWP `source_query_cli` | 0 |
| 所选 ET wrapper → 真实 ET supervisor/worker | 0 |
| CWP `transcript_import_cli` | 0 |
| CWP `source_reader_cli` | 0 |

请求为 NASDAQ/MSFT/FY2026/Q3/as-of 2026-09-30，timeout=10s、max_bytes=1,000,000、max_cost_usd=0.00。fake transport 的调用日志只记一个 GET，回执 requests=1、response_bytes=862、complete=true。CWP 公司目录只有一份原文，它与 provider 夹具的 862 字节完全一致；SourceRef 的 SHA 和 byte_size 对应这些实际字节。真实 reader 已实读验证。未翻译或 scrub 原文。

调用 `ff_v2_envelope.success_envelope` 后，公开 transcript 只暴露稳定 SourceRef 和合同元数据；没有 key、配置目录或物理路径。既有 filing 的合成 SourceRef 仍保留。**filing handle 是测试输入，不是本次实际下载或验证的财报；不能将此结果扩展成完整 FF 财报下载/整 RF 通过。**

第二次继续 `fetch_if_missing`，第三次改为 `reuse_only` 且不带 acquisition_limits。两次都重新执行真实 CWP query/reader，取得第一份原文的相同 SourceRef；没有 ET child、import child 或第二个 fake GET，原文文件字节与 mtime 都不变。已知 provider 原始 publication_date 为空，三次均没有伪造 as-of 闭环：第一份为 downloaded 且 cutoff=false，复用为 unknown_publication 且 cutoff=false。复用结果没有新 provider usage 回执，未填造 requests=0/complete=true；明确的 provider_calls=0 由未启动 ET 的实际调用轨迹佐证。

所有 CWP 子环境剥离 FMP_API_KEY/FMP_API_KEY_FILE。ET 子环境获得预期合成 key，但 key 不在 argv/stdin/公开结果。配置、key 和 source_catalog 夹具在运行前后字节和 mtime 一致。

## 清理、工作树与限制

- `C:/Users/郑曾波/AppData/Local/Temp/w07-persist-tests-sh_r2qc6` 已自动移除。
- `C:/Users/郑曾波/AppData/Local/Temp/w07-persist-chain-bamn_i6u` 已自动移除；其所有下载原文、manifest、DB、wrapper、fake key、calls 和 runtime 仅属测试夹具，没有留存到生产目录。
- 没有写 pytest cache/pyc。FF 仍仅保留原有未跟踪 `config/FMP_API_KEY.txt`，ET 仍仅有原 owner `.workbuddy-ai/`/`eval_results.json`；最终 SHA 均与上述接受对象相同。这些真实文件没有读取内容或更改。
- 初始沙箱只读 Git 工作树检查报 `must be run in a work tree`/Permission denied，不能计作产品失败。随后用正常 OS 权限和清除 Git hook 环境影响的只读命令取得正确 HEAD/status；没有 Git 写入或绕过审批拒绝。
- 已读 MAIN_INTEGRATION 中的 5 FAIL/5 PASS RED、79 PASS GREEN 和首轮正常 push 旧 allowlist 文案断言失败记录；这些是实现者历史证据。本次只声称上表亲跑结果。旧独立 allowlist 拒绝的行为在新合成配置中仍通过，不增加第二权限域。

本地 M2 的配置/工具定位与实际三仓桥已经充分，不追加小节点审查。MAIN 下一步继续正常发布/exact CI、选择性安装和两个非秘密持久配置字段；M3 使用既有原始 key 和累计预算记录一次当前真实鉴权/entitlement，不能用 synthetic fake GET 替代。
