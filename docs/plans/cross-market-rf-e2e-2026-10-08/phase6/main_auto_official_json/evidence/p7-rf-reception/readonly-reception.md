# P7-RF 独立只读接收验收 — 2026-10-11

## 结论

**source_partial（源码交付部分接收，尚不能标为完整卡通过或直接发布）**。已交付的 scope / observation-period 修复和只读诊断真实可运行；新实测发现转换参数自身适用期间与实际输出期间的关系仍漏校准诊断。另有交接已披露的 MAIN 4.2.1 版本接线未落地。两项由 MAIN 集成修复，不增加人工许可或逐节点签收。

## 实际分支、范围与交付记录

- RF 工作目录：`C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/revenue-forecast`。
- 分支：`codex/p7-rf-calibration-binding`；实际 HEAD `183c9534b90549c094fc32a51ff6ada1e9cb5227`；源码交付 `05aa2661c9cdc34cb7e9ce3cf7e83b43bee7f556`；后两提交仅交接文档。
- base `6883bf00548abb9891eab6762aeaa89e3898b202` 为真实祖先；本次前后 HEAD、完整 Git status（空）一致。
- base→HEAD 36 个文件，均在卡独占写集：15 个生产/测试/reference/fixture 文件及自己的 `.planning/p7-rf-scoped-calibration/**`。未改算法、period contract、source preparation、CI/hooks、owner WIP、安装副本或邻仓。
- HANDOFF、handoff JSON、三份 PWF、共享启动接口和 MAIN patch 均实读。handoff 的 7 个日志 SHA 均匹配；pre-push 日志 SHA 另行匹配。确切 SHA 在 `readonly-reception-summary.json`。
- Git 存在正常提交；hooks Passed 与 pre-push 拦截有真实记录。独立验收没有重演 commit/push，不能由 commit 对象反推出从未使用 no-verify。
- 当前无 upstream，handoff 如实记录 push 被正常门阻拦、remote 无本分支、exact CI not_triggered。接收期间没有 fetch/merge/push/reset/stash/安装。

## 独立集中实测（不是复用交付日志）

运行 `readonly_reception_driver.py`，本次最终完整 receipt：`readonly-reception-receipt.json`。

1. 当前源码集中责任：`test_scoped_calibration_support.py`、`test_research_support_diagnostics.py`、既有 `test_research_evidence_roles.py`，**25 passed in 9.23s**（外层调用计时 15.03s）。现有样例、未知范围、stress、未进 DAG 的合法 upper 参考、仅单 driver/year 支持、跨业务 scope、情景、算术/confidence、强重算等责任正负控均绿。
2. 三组重新生成的 synthetic native 输入，经真实 `build_auditable_case.py` → `run_target_measurement_e2e.py`（实际 validate-only、compute/Markdown、snapshot 三命令）→ `research_support_diagnostics.py`。不是手写 native 输出，不取客户目录夹具；来源由真实 `build_revenue_source_record_from_verified_read` 处理既有版本化合成 read/ref/body 合同。

| 组别 | 真公共 CLI | calibration | Segment A FY2026 ×3 | FY2027 / Segment B |
|---|---|---|---|---|
| 正控 | 全部 exit 0，真实 snapshot/registry/Markdown | referenced_range，reasons=[] | supported | unsupported |
| 只改变 conversion observation.period 为 FY2031 | 全部 exit 0 | unverified，含逐参数/claim 的 unverified_period 原因 | unsupported | unsupported |
| 同时改变 conversion 参数、claim、observation.period 为 FY2031，收入输出仍 FY2026 | 全部 exit 0 | **错误 referenced_range，reasons=[]** | **错误 supported** | unsupported |

正控与 observation-only 负控的收入 `consolidated_forecast` 完全相等，confidence.score 同为 49.0，保持 stable-fsum/1；引擎实际 4.2.1。真实输出/输入/linked input/来源 preparation、snapshot 和命令记录 SHA 在本次 receipt，不沿用交付输出。

3. 实际诊断 CLI 对输出 Low 借用 Base 参数、过期 excerpt SHA 各 exit 2，分别报 `calibration output scenario mismatch`、`claim excerpt hash mismatch`。unknown-range 保持 null/unverified，stress 保持 stress。
4. 当前 emitter registry 独立 API 实读：schema3.7/3.8 的 output 模式拒绝旧4.2.0、接受4.2.1；3.9 接受两者。这与交接的未应用 MAIN patch 一致，尚不能声称旧4.2.0 output 兼容已完成。

## 发现 1：转换适用期间与实际输出期间关联遗漏（真实系统缺口）

定位：`scripts/research/native_dependencies.py:94` 只比较 observation.period 与其 parameter.measurement_period/period；`scripts/research/evidence_roles.py:173` 只消费任何 covering observation 的 `bound`。`_calibration` 验证 reference input 的 observed_period、真实 formula/ordered input IDs 和 output 的 scope/scenario/unit，但没有确认 conversion 的**适用期间**与它实际校准的 output/消费单元期间的关系。

反例没有变造 hash、没有把未知证据填 0，也没有偷换场景：

- reference_lower/upper 仍是合法 FY2025 历史范围；unused upper 仍应允许。
- conversion_low/base/high 的参数 period、绑定 claim.period 与 observation.period **一起**变为 FY2031；数值/单位/scenario/native 公式不变。
- 真正消费它们的输出仍 `0_low_2026`、`0_base_2026`、`0_high_2026`，parameter.period=FY2026，native revenue driver 单元 FY2026。
- 因 observation 与 parameter 自身一致而全部 bound；仅表内一致无法证明 FY2026 已有适用的转换支持。新 diagnostics 又按 output PID 把这个结果投影成 FY2026 supported；错误实际出现在 assembly、forecast、Markdown 和诊断，不只是未使用的纯函数。

这不要求所有日期/期间相等：历史范围、早期披露、跨期管理目标和真实假设仍可用于未来模型。**parameter.period 是该参数的适用期间，不是来源发布日期。**该反例缺的是 FY2031 conversion 到 FY2026 target 的可复查适用/转换关系。应把缺口降为 relation-specific unverified/conditional，保留文档、收入算术和合法假设；不能新设“跨期来源禁止”或严格拒绝整个旧流程。

## MAIN 最小集成接口及验收标准

1. 在共用 `_calibration` / native dependency 层修转换参数到真实 output/消费单元的 target-period 关系。直接 conversion 参数适用 FY2031、target FY2026 且没有可复查跨期桥时，诊断必须保留具体 parameter/claim/output IDs 和实际期间，不能晋升 referenced_range。只处理支持诊断，不改来源身份验证、收入 calculators 或 `operating-research/1` 必填字段。
2. 正控保持：FY2025 历史 reference→FY2026 当期转换→FY2026 输出；unused upper 不必进 DAG；真正显式跨期 native 公式/目标桥可保留，但适用性未知就标 assumption/unverified/conditional，不用文本标签推断可信。输入无 optional research 仍 None，unknown/stress 原语义保持。
3. TDD 增加本次“parameter + claim + observation 同步变更”反例与实际 public offline pipeline 检查；修后 forecast/Markdown/diagnostics 共同降级，真实 run 仍可完成、数值/confidence 不改变。保留旧 observation-only 负控、合法 reference 正控和单 driver/year 支持范围；不能仅补公司名或夹具 PID 特判。
4. 应用交接已有 `MAIN_INTEGRATION_PATCH.patch`：**实际 5 个文件**（schema_compatibility.py + 4 个 test 文件、共 5 处版本断言），恢复 3.7/3.8 的旧4.2.0 documented emitter、接新4.2.1 current emitter。补丁 SHA `9335ad102f8c8764bdaa55ff6c669a9cb9b423e562edfd1429062df2e6848338`。不要改 sealed 原件/旧输出/hash；旧语义需 pinned 4.2.0 runtime，不重签成4.2.1。当前 hook 两项版本失败应按实际接线修复，不绕过。
5. `economic-support-diagnostics/1` 保持可选、只读、input SHA 和请求年/逐 segment×scenario×year/ID 原因，economic_truth_inferred=false；不成为发布许可、身份库或新的签收合同。诊断 CLI 不调用 forecast provider/LLM、不写 registry。安装/正常推送/合线由 MAIN 后续集中完成。
6. 保持 R16/R17/R18/W09 实际经济研究缺口开放；25 责任测试或诊断绿不能替代四独立研究审查和真实公司幅度/时序/joint stress。

## 恢复、费用和准确性限制

- 最终驱动全程 25.84s；0 外部 provider/LLM，USD0，无安装依赖或客户目录。每一个 run_forecast/snapshot 子进程 registry 均在本次 owned TEMP；工具自己的 registry override 也在对应 native 目录。
- 前后 107 个真实 runtime/config/交付与实际测试依赖文件 SHA 全相等，Git status/HEAD 全相等。仅保存 MAIN 指定 evidence；RF仓、生产资料、canonical owner WIP未写。
- 预备 SHA 审计曾误遍历49,295个历史 tracked文件，未开始测试或创建TEMP前已终止；改为实际责任写集与runtime保护，未读取其内容作夹具。没有全湖备份/恢复演练。
- 第一轮实际测试已通过，但清除TEMP时 registry 的 Windows 只读属性触发 WinError5；不归因为RF生产代码缺陷。只对核验的自己的TEMP用 Force 清理；驱动随后先固化receipt、在owned路径内恢复属性再删除，并重跑同一集中包取得上列最终完整证据。未扩大测试范围。两次本次TEMP都已删除；不把首次输出再累计成更多PASS。
- 最终 receipt cleanup.removed=true；子进程环境独立，父环境未改。没有真实供应商成功率、真实经济可信度或远端CI验收结论。本次独立 static 未重跑，交付 static 的SHA已核对；MAIN修复/最终发布时沿正常集中静态门。

## 文件

- `readonly_reception_driver.py`：独立可重跑驱动；修复前返回1表示 source_partial，不伪装GREEN。
- `readonly-reception-receipt.json`：本次真实命令/exit/stdout/stderr/耗时/原生输出SHA/恢复记录。
- `readonly-reception-summary.json`：交付日志、源码、测试、MAIN patch 和本次receipt的确切SHA。
