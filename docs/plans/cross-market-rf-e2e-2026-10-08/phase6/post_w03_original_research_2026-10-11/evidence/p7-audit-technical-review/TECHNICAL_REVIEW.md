# P7-AUDIT 独立技术只读接收

可接收工程基础闭包；交付中的请求绑定合同仍有三处材料缺陷，暂不能据此声称“真实请求符合 effective_scope，且 child 必然消费 builder 记录的同 SHA”。本次不是公司四审，不作投资研究质量判断。

交付身份已核对：docs HEAD `40b38103f4b96860617e9bae98ec5b4ea8ee08d5`，source `18a52f16e605e2ca33bcf5dff5b7d4176077aa1c`，base `78c2b1089200937a9371548f3f8a212c501fdfcd`。HANDOFF SHA 为 `946afe381eced7697e849ee535480017c48d791b68bce58fa9d1fa1aaaa12f2d`。

亲核 Git 工作树 clean；`audit_run.py`、`numeric_audit.py`、五份旧测试模块（59 tests）及旧 fixtures 与 base 无差异。已读 HANDOFF/json/PWF、五个 helpers、九个 references、原 E2E driver/fixture 与 ROOT 两项诊断。原 96-test 完整通过日志 SHA `3a88257e4669c90601bc368972d7d01fe7ef336a44a602da468df98c165cfeb0` 与 E2E 日志 SHA `26bc6547eff65072fe065cdff98c967721b428b29787541af695b2939ffa5e50` 一致，本次未重跑整 suite。CodeGraph 在 audit 工作树未初始化；只读范围内未 init。默认沙箱 Git status 的“must be run in a work tree”由已授权 escalated 只读命令解决，未改 Git 配置或其他 owner 环境。

六个真实微型 probe 的完整命令、exit、stdout/stderr、SHA 与产物在 [probe-results.json](probe-results.json)，计划先存于 [probe-plan.md](probe-plan.md)。前三个仅调用 pure helper 与 native CWP 纯 budget 构造；后三个是 pure 序列化与本地 supplied fake child，不调用 native acquisition。

| Probe | 实际观察 | 能证明的范围 |
|---|---|---|
| P01 零费用 | helper 拒绝 `0.00`；CWP budget 构造接受 | 零费用资源合同不兼容，未执行 provider |
| P02 负数 | helper 与 native 构造都拒绝 `-0.01` | 负数拒绝正确 |
| P03 NaN | helper 与 native 构造都拒绝 `NaN` | 非有限费用拒绝正确 |
| P04 外层/正文 | 外层 P1/100/1.00，正文 P2/1000/10.00，accepted、diagnostics=[] | helper 记录与请求正文能错绑 |
| P05 未改请求 | builder=frozen=child，SHA `ee373648…`，正文仍矛盾 | 真实本地冻结链忠实传递错绑字节；不能证明 provider 超支 |
| P06 build 后改自有请求 | builder `ee373648…`，frozen=child `fcb8c8f3…`；input/output complete=true，exit0 | P7 composition 未传 builder expected SHA；W11 对当前字节的冻结记录本身正确 |

首轮 P05 在极深证据路径遇 Windows 路径长度错误；失败 driver 与自有 attempt 留存，改用 Windows 扩展路径表示重试相同六个语义案例，未追加其他 probe。

## 缺陷与最小责任修正

**TECH-P7-001 / P1：费用域不兼容。** `execution_request.py:36,44` 对 money 使用 `number <= 0`。CWP `src/company_wiki/source_catalog/download_budget.py:15–24` 的域为 finite nonnegative；FF `scripts/filing_contracts.py:319–323` 允许 `0`/`0.00`。责任在 P7 cap parser。仅 money 改为有限且非负，负/NaN/bool仍拒绝，byte/token/time正整数规则与 min(scope,deploy)保持。未知/null不转零。零 cap 与免费 native 操作兼容，不证明 native 已执行或已证明费用。

**TECH-P7-002 / P1：外层元数据未与 native 请求绑定。** `execution_request.py:152–168` 校验外层 profile/limits，`:170–174` 独立序列化 `template.request`，`:190–194` 却记录前者。P04/P05 确认这两部分可矛盾。责任是 native 请求生产者/接线 adapter 与 P7 builder 的合同衔接，真实资源 enforcement 继续属于 FF/CWP/native owner。最小修正是由实际 native 合同生成一次控制字段，再从真正送出的 request/config/argv 取得观察值并比较边界。例如 FF 明确映射现有 `acquisition_limits.max_bytes/timeout_seconds/max_cost_usd`，不能递归扫所有 RF JSON 把业务数值当资源字段。没有资源控制字段的 native JSON 记录 declared 与 observed/unknown，不虚称已绑定/已执行 enforcement。这里的 generic P2 字段没有证明任何实际 provider endpoint 会接受它。

**TECH-P7-003 / P2：builder 身份没有进入 prelaunch freeze。** `audit_run.py:461` 和 `:598` 无 expected digest 输入；`:513` hash 当前输入，`:618` 启动 child。这符合 W11 原“冻结当前输入”的语义，缺口在 P7 composition 对 `executor.md:45` / `workflow.md:51` 的同 SHA 保证。修正应在 P7 opt-in 接线携带 builder expected digest，并在 child 启动前比较已冻结的 exact bytes SHA；单独先读一次 hash 会留下竞态。可给现有冻结边界一个可选 expected-digest 参数/hook，旧 capture 不传时语义保持。局部输入不一致记具名失败和 child_started=false；这是本调用输入合同，不能变成人签或全局发布门。

## 可以接收的基础闭包与验证建议

五 helpers 的 API 清楚：fresh attempt/脱敏公共辅助、`build_execution_request`、`join_status_index`、`check_provenance`、`aggregate_findings/check_coverage`；join/provenance/coverage仍是小索引与诊断，quality_status=`not_evaluated`。transport/business 分列、call费用一次计数、unknown/null、原片段quote/actor/date诊断、四元组 issue key、旧 report v1/旧 runs 只读兼容可作为工程基础接收。详列接口与引用在 [technical-review.json](technical-review.json)。

现有测试覆盖外层放大、负控与未改请求的正向 SHA 链，但没有封住这次发现的三个合同缺口。接入当前 expert 根因裁决时，先补有意义 RED：零费用自由操作、实际 native owner 形状的正文/外层矛盾、build 后修改导致 prelaunch mismatch；GREEN 验证对齐/小于边界、负/NaN、旧无期待 digest 的 capture、无控制字段的正常 RF JSON兼容。保留59旧断言，不新增全部JSON许可schema，不把 helper 测试通过写成 live cap enforcement。

W01–W08 与这三项发现交本次根因 expert 合并已有 owner 计划裁决，不另起第二整改流程。RC-08 的“诊断/阻断”张力不构成新增全局门依据。native owner继续负责一次身份解析、来源/原件与真实资源上限；本次没有二次身份或跨仓文件写入。当前公司四审期间未切安装 runtime，canonical audit仍沿既定 base。

状态如实为 `no_remote` / `not_triggered`；本次 GET=0、provider=0、project model=0、新增费用=0.00。source、原测试、配置、安装、sealed company run与共享PWF未修改。只写本接收证据目录。接收已完成，停止在报告交付。

