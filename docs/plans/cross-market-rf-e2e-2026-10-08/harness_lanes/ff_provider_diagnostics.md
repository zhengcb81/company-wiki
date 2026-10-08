# R6-FF-CAUSE：上游失败原因与真实调用状态的安全传播

## 任务与开工

可立即独立启动，任务量中等。工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/ff-diagnostics`；分支 `codex/cmrf-provider-diagnostics-20261008`。使用 worktrees.json 的已发布 main 精确基线，不从旧安装副本施工。

读本卡、README/handoff_interface、root_cause_remediation/follow_up_plan、FF SKILL以及本仓 AGENTS。已核实缺口在 `scripts/fetch_filing.py::_run_company_wiki_json` / `_classify_wiki_error`：具名 producer 失败经处理后只输出 ensure exited 1/fatal。当前 retry只对 catalog争用做自动重试。`FilingFetchError` 位于 filing_contracts.py；v2错误序列化在 ff_v2_envelope.py。

本线是已有实测缺口，不重做刚已完成的电话会费用/能力升级。最新 ET/FF 的 exact和实际用量接口固定；账户 entitlement 仍外部限制。

## 独占范围

允许 FF 的 `scripts/fetch_filing.py`、`filing_contracts.py`、`ff_v2_envelope.py`、新小型错误诊断模块、相关 tests，以及 `docs/implementation/cmrf-provider-diagnostics-20261008/`。不改 transcript_companion/transcript_tool_transport、ff_process_transport及OS子模块、SKILL、配置/凭证、CI、安装副本和共享旧PWF。 MAIN 不同时写本线范围。

只能只读 CWP/RF/ET接口，不跨仓改或增加依赖。canonical FF目录的 `config/FMP_API_KEY.txt` 属 owner WIP，不读入日志/不提交。实际下载、入库和来源资格的决策仍由 CWP 做，FF不能复制存储实现。

## 对外输出接口与兼容

保留原 v1/v2 source/ref形状、现有 status/error_code/retryable及calls/downloads意义；使用一个可选 `upstream_cause` 诊断字段，v1顶层、v2的filing内，字段结构：

```json
{
  "schema_version": "filing-upstream-cause/1",
  "operation": "identify | ensure | resolve | close-gap | query",
  "code": "具名安全机器码或unknown",
  "provider_started": null,
  "usage_complete": null,
  "retry_scope": "none | catalog_contention | caller_decision"
}
```

- 不输出 raw stderr、exception text、任意command、物理目录/URL query/密钥；不把没有证据的 started/usage填false/true。只从版本化公开结构读取有限字段；未知/过大/损坏保持unknown及已有fatal语义。
- `code` 使用经验证的CWP公共机器码和有限映射，禁止直接复制未验证message字符串。CWP未提供字段时诚实null；测试进程日志证明是否启动仅写测试报告，不能生产推测。
- 明确区分provider尚未启动（配置/能力/预算预检）、已启动账户/HTTP拒绝、下载后验真失败、未知最后usage、catalog竞争。只有现有明确catalog争用按共用总deadline自动重试；账户拒绝、不支持、预算、坏hash/身份/期间、未知最终用量不盲目重试。
- 如果当前错误serializer/consumer不允许新诊断字段，给兼容测试和MAIN接口差异清单。不要升级顶层错误码为宽泛upstream_error使所有失败都retryable，也不悄悄改RF/CWP来接受。

## 先验证接口，而非凭空设计错误格式

1. 从当前 CWP `source_catalog/cli.py` 等公开入口与真实失败结果只读调查：机器schema、error_type/安全code、是否已有usage/provider_started。以 rg/CodeGraph 查实际文件/调用方；既有fatal和旧类名兼容保持。
2. 本线写 task_plan/findings/progress及一张小接口观察表。先RED复现“有机器原因但只剩ensure exited/fatal”，再写metadata缺失/未知格式的正当unknown行为及秘密内容不外泄反例。
3. 共用诊断解析器与FilingFetchError可选诊断，把成功和失败预算边界保留；不要向多个分支复制同一JSON/error解析。只消耗有界stderr，沿用既有OS进程树和总deadline。
4. 公开 v1/v2 CLI 传递诊断，保持财报/电话会独立结果、原零下载复用trace及统计。不把统计calls（CWP CLI次数）当provider HTTP次数。与已完成transcript实际provider_requests区别明确。
5. 用真实CWP CLI和隔离tmp做一个集中E2E，保留unknown字段的诚实状态；如果producer没有足够机器字段，交MAIN需要补的字段而非自己跨仓补。提交本分支和五文件交接。

## 测试包及验收

建议新 `tests/test_provider_cause_contract.py`、`tests/test_provider_diagnostics_cli.py`，同时复核既有 fetch_filing / FF v2 / golden / source reuse / catalog retry / limits的实际存在测试入口。跨仓E2E可放本线 `docs/.../run_isolated_cause_e2e.py`，明确手动大节点，非每次commit网络门。

- 真实结构且可区分：支持不足/预算deadline/账户拒绝/验字节失败/catalog争用；未知结构、过大/截断/混合stderr、恶意code、带key/绝对路径的message不漏出；schema/request身份错配不被采纳为成功。
- 原自动retry范围不扩大，catalog backoff共享剩余总deadline，硬截止/unknown usage不自动重新请求；deadline和failure cleanup走现有owned树机制。
- CLI v1/v2确实输出可选诊断，SourceRef无物理字段，成功golden保持，复用0下载trace保持；失败不是空成功。主line代码禁止根据ticker/sourceSHA/page白名单判原因。
- 集中E2E只做本地/fake provider：配置坏/无预算能力等让**真实CWP CLI**发结构错误再过FF公开CLI；另一个合法reuse按SourceRef强验字节。在fake provider中记录启动/HTTP/usage，核FF诊断；不调用真正市场或模型。独立catalog/原件小夹具退出恢复，不写生产source_catalog.yaml。
- 新诊断API新增后跑仓内静态检查及tests/test_complexity_ratchet.py，避免简单解析器过于混杂导致CI仅静态门失败；不放宽旧门阈值来藏业务缺陷。大节点集中行为测试，日常CI不加几十分钟任务。

## 交付

按 handoff_interface.md 给精确baseline/commits、实际observed upstream schemas、安全字段映射、RED/GREEN、公开CLI结果、目录恢复。代码功能完成与provider外部限制分别报告。MAIN最终接入RF报告/测试套件并合主线；本线不改主线、不整套安装覆盖、不买套餐。
