# M3-USAGE 独立验收与根修 — ACCEPTANCE

状态：责任工程及公开离线子进程链已通过；MAIN 总集成、提交、推送和真实公司研究另行完成。源码已稳定，不再修改；本子任务没有 commit。

## 原交付核对

- CWP `704c374f`（代码 `d65e421c`），FF `f0f4e363`，RF `741f7c01` 实际 diff 与施工卡写集相符。
- 原 handoff 所列全部 source byte SHA 与 8 条 RED/GREEN/restore log SHA 实读匹配。
- 新增 `acquisition-observation/1` 是同一 operation budget 的只读投影；FF envelope sibling 与 RF 原样传递，没有第二账本、额外人审或授权链。
- 原交付只读 fresh 复跑：CWP 49 PASS；FF 40 PASS；RF 98 PASS。首次 sandbox TEMP 创建失败单列环境错误，未当产品 RED；随后真实独立 TEMP 全部恢复。

## 验收实际发现并系统修复

1. Dayu 自有 CLI 把初始费用 counter 0 发作旧 1.0 receipt，父层误当已知免费。新增可选 `acquisition_cost_observed`，success、handled failure、progress、cleanup 分支保真；Dayu 外部仓零修改。
2. 将旧 1.0 counter 与新 observation certainty 分离，覆盖 SID 等所有 legacy adapter：无新 proof 的 legacy 0 -> cost=null；legacy 正数 -> 已报告下界且 usage_complete=false；只有明确 true 的 fee proof 可称完整，包括明确免费的0；false -> unknown。旧 counter、收费预算和下载策略逐值保持。
3. 跨同一 operation 的已知/未知费用两顺序累积均保留已知下界，后来有 receipt 不会擦掉早期未知。新 completeness 标志只影响 observation，不影响旧 acquisition usage/重试策略。
4. 三仓 outcome=[]/{} 都会 TypeError，坏可选诊断可吞原错误；已加字符串判定，整体丢坏诊断并保留独立 cause/receipt。CWP 允许 null exchange 而 FF/RF 不允许的合同裂缝统一为整数，unknown 由 *_complete=null 承载。
5. HTTP 空响应本身证明 provider 已启动；complete=false 后仍继续计已观察响应并保留末次 metadata，下界不会丢新观察。
6. 原公开 E2E 夹具在 metadata HTTP 500 后仍返回成功，不曾覆盖真硬失败。新增公开 RF->FF->CWP->loopback provider 硬失败检查点，先 RED 实证 exit0!=3，再修夹具，保持原错误 upstream_unavailable、2次metadata交换、unknown fee null、无重试/无正文下载。
7. 新 observation HTTP metadata字典增加合法 dict[str, Any] 注解修复实际 mypy 67/72；未 ignore。

原sealed交接/日志不改；新的反例、后续语义升级与 GREEN 日志均独立保留。

## 最终责任与公开链证据

- `green-final-company-wiki.{log,json}`：169 PASS (23 新验收反例 + 146 原责任回归)，53.41s。
- `green-final-filing-fetch.{log,json}`：44 PASS，含原透传、失败连续性、malformed 主错保留。
- `green-revenue-forecast.{log,json}`：101 PASS（RF 原责任与新增形状控制）；后补独立主错控制见下面公开包。
- `green-v2-public-usage-e2e.{log,json}`：7 PASS，18.26s，3 公共子进程 E2E + 4 RF 新控制；US下载/复用、CN下载、missing 与真hard-failure。
- `public_e2e_logs_v2/`：每次实际 argv、exit、stdout/stderr与 SHA，含 us_hard_failure；测试 provider 的已知费用显式声明 true，旧 1.0 receipt 形状不改。
- 所有测试独立 TemporaryDirectory，json 收据 temp_restored=true；无生产文档/配置/key 写入。三份生产配置与集成配置 byte SHA 一致，见 acceptance-source-snapshot.json。
- 三仓 Ruff 受改责任文件 PASS。直接额外扩大到4个owned旧模块的 mypy 9条既有诊断保留于 mypy-owned-runtime.log（4个Decimal|str旧预算类型、1个reported_retryable旧属性、4个外部Dayu缺stub）；不把额外扩大检查列为发布门，MAIN实际公开模块 gate 已独立通过，不改外部项目或添加ignore。

## MAIN 集成要求

- MAIN已负责 `error_taxonomy.structured_error` sibling publication、FF CI_TESTS登记；本子任务未触共享文件。
- 旧 handoff runtime byte SHA 是旧交付，不可拿来签收根修后的源码；MAIN依据当前 source closure重新记录实际HEAD及runtime安装闭包。
- 保留已接受工程状态与真实公司研究状态分别记录；以上0公网provider、0模型调用、0收费tokens/费用；旧7模型+1FF未知费用不核销。
- 正常 hooks、commit/push、exact-head CI、共同集成链与后续真实资料研究验收由 MAIN 统筹。

## 源码写集

见 acceptance-source-snapshot.json：CWP4个runtime及专用测试2个；FF validator+专用测试；RF validator+专用测试与专用E2E。未写sharedPWF、生产配置、原件、Dayu外部仓或StockInfoDLSimple仓。
