# W06 最后一个 cutoff 失败：只读共因诊断与修复写集

状态：`ROOT_CAUSE_CONFIRMED_NOT_REPAIRED`。ROOT 原 41 项矩阵 **40 PASS / 1 FAIL，164.62 秒**；唯一失败 `call_past_cutoff`。本诊断没有执行矩阵、测试、网络、LLM、Git 变更或产品写入，没有读取密钥。ROOT 负责实施、最后矩阵回放和发布。

## 1. 结论

日期限制正确执行，未发生未来电话会入库或历史资料误用。失败是跨层结果投影丢失事实原因，原测试断言合理。不能放宽期待，也不能把 `candidate_count=0` 猜成 cutoff。

实际输入：Apple/AAPL，2025 Q2，`as_of_date=2026-12-31`；唯一响应记录 `call_date=2027-06-01`。ET HTTP seam 根据真实 ET request 填入 symbol/year/quarter，日期取固定 fixture；不是错误季度导致排除。实际 provider 请求 1 次、响应 512 字节、usage complete=true，FF→ET supervisor/worker 实际运行，CWP import=0。

原始 ET receipt：`earnings-transcript-result/2`、`status=not_found`、`candidate_count=0`，没有日期或原因。FF 最终为 `provider_unavailable` / 同名泛化 reason。矩阵 actual `eligible=false`，但 `cutoff_diagnostic=false`，因此 FAIL。

## 2. 两处共因和透明层

| 责任层/位置 | 实际行为 | 责任结论 |
|---|---|---|
| ET `transcript_api.py::_fetch_fmp_transcript`，710–718 | 真实空 JSON 列表返回 not_found/candidate_count=0 | 普通未找到 |
| 同函数，722–747 | 先核验实际 symbol、FY/Q、规范日期、非空正文 | 当前反例已通过，不应再引入另一身份库 |
| 同函数，759–767 | 唯一合法记录 call_date 超过 as-of，返回与空列表同形的 not_found | **第一处信息丢失：来源层明知日期排除，却不携带原因** |
| ET `retrieval_worker.py`，176–188 | 将 API result 整体序列化到内部信封 | 未删字段 |
| ET `retrieval_runtime.py::_load_result_file`，287–302 | 有界读/既有 request+schema 验证后原样返回 result | 未删字段，不需重写 supervisor |
| ET `transcript_tool.py::_supervised_result`，103–104 | 原样返回 outcome.result | 未删字段 |
| FF `scripts/transcript_tool_transport.py::EarningsTranscriptsTransport._et_result`，605–621 | 所有非 fetched 均转 provider_unavailable，只读有限已知 error_code | **第二处信息丢失：把合法空结果与 provider 故障合并** |
| FF `scripts/transcript_companion.py::_acquire`，178–183 | 已能接纳 not_found，并保留 reason/实际用量 | 无需新审批或再解析正文 |

这不是 CWP 原件保存、scope、SHA 或虚拟化的缺陷；这次来源根本没有进入 importer。CWP 12 个冻结产品文件仍匹配作者冻结，matrix 的 9 个模块 binding 也一致。

## 3. 同类设计缺口

不应只给 AAPL/FMP/这个日期加特判。ET Motley `fetch_transcript` 903–924 也把“期间不符”和“期间正确但发表日晚”压成同一个空结果；`_listing_candidates` 1061–1081 先丢弃未来元数据，`discover_transcripts` 1263–1294 再筛期间，无法解释无候选原因。至少 fetch/discover 的同类排除要保留来源层已经观察到的原因，不追加 HTTP 或传递正文。

**必须先验证身份/目标期间，再判断日期排除**：列表中只有其他季度的未来公告不能被误报为当前季度 cutoff。合法目标期晚日期与错误 symbol/quarter 混杂时，保留现有 provenance 拒绝；多合法候选的歧义不得为了 cutoff 变绿而取消。截止日当天仍允许现有正常路径。

FMP 的 call_date 不是 publication_date。call_date 晚于 as-of 足以证明不符合时间范围；call_date 不晚于 as-of **不足以证明发表日在当时可见**，原 `publication_date=null` / `as_of_cutoff_verified=false` 语义保持。

## 4. 最小兼容接口决定

1. ET 请求 `/1`、结果 `/1` 和 `/2` 版本及成功 goldens 不变。`not_found` 保留现有 `fiscal_period`、`candidate_count=0`（可用候选数）语义。
2. 优先复用 ET 已有机器诊断字段 `error_code`，**不同时再造同义 `reason`**。已验证唯一电话会因日期排除时加 `error_code="call_after_as_of"`；已验证目标期发表日期排除用 `publication_after_as_of`。普通空列表/只有别期候选，不填 cutoff 码。
3. 可选 ET 日期诊断仅为真实 `as_of_date` 与已验证 `call_date`/`published_date`，不携带内容、key、带 key URL、raw payload。若不用日期字段，原因本身已满足现有业务合同；避免为本次验收扩公开 FF 字段集。
4. FF `_et_result` 在既有有限响应投影处区分合法 `not_found`，保留状态，并映射有限机器原因：明确 cutoff → 同名 reason；旧 receipt/普通空结果 → `exact_transcript_missing`。未知任意字符串不能裸透传，也不能伪造 cutoff。凭证/402/429/worker/timeout 的具名错误语义保持。
5. 实际 requests/response bytes/usage complete/unknown 沿既有 observation 传递，零 importer、零重试、零重复请求；不从结果状态猜零消耗。外层 companion/envelope 已允许 not_found/reason，无需变更其版本、重跑身份判断或另加审批。
6. FF `et_v2_contract.py` 当前只是既有消费者契约测试边界，生产 transport 没调用。为其补 `not_found` 分支及可选诊断合同，保留成功 26 字段合同和现有 failure goldens。**不要把它新增接入 production 作为第二次身份/字节校验。**

命名来自原 oracle：`tools/offline_contract_matrix/matrix_outcome.py` 44–47 已接受 `call_after_as_of` 和 `publication_after_as_of`。原 tools/CaseSpec/assertion 一字不改。`call_after_as_of_date` 不在原集合，不选它。

## 5. TDD 写集与三个大节点

### A — 共用行为 RED（不跑全 41）

- ET `tests/test_transcript_api.py`：强化原 478–488 和 122–128，断言具名日期原因；空列表无 cutoff；截止日当天/晚一天；错 symbol/quarter 与晚日期组合保持 provenance 拒绝；多合法候选保持歧义；原 publication unknown 不冒验证。Motley fetch/discover 只统计已验证目标期的晚日期，别期未来资料不误报，listing-only 零正文请求。
- ET `tests/test_retrieval_cli_e2e.py`：真实 CLI→supervisor→worker→API 的假 HTTP，断言 `/2` cutoff 原因与 usage 到 stdout/stderr，worker 清理、无 translator、零正文落盘。用现有 private seam 和 fake key，不复制真实配置或凭证。
- FF `tests/test_transcript_launch_contract.py`：cutoff receipt、旧 not_found、普通空结果、未知诊断、完整/未知用量；旧凭证/402/timeout 保持。非 fetched 响应的既有 request/schema/period 绑定不可因新增分支旁路，复用同层已有 envelope 规则，避免复制验证代码。
- FF `tests/test_transcript_companion_transport.py`：真实 transport/orchestrator 保留最终 not_found/reason、ET 一次、CWP import 零次、实际 usage 保真。
- FF `tests/test_et_s0b_contract.py`：新可选 cutoff + 旧 not_found 合同正控，坏 request/period 不变为合法 cutoff，成功 goldens 字节不变。

旧 ET 测试只 `assert status == not_found`，因此从未约束“排除原因在最终 FF 保留”；这是测试合同覆盖不足，不能靠修改该断言掩盖。RED 的目标是新增跨层原因断言真正失败，而非缺文件/import error。

### B — 共用实现与一次集中责任测试

ET 产品写集只 `transcript_api.py` 的上述 provider selection/结果诊断，必要小共用 cutoff projection；不动下载 budget、supervisor、翻译、密钥配置、原件 writer。FF 产品写集只 `scripts/transcript_tool_transport.py` 的 bounded response mapping、既有测试合同 `scripts/et_v2_contract.py`。统一来源原因 vocabulary，不能按公司/季度/测试 id 分支。

所有上述责任测试一次集中跑，旧受影响 golden 一次 check，相关 lint/diff 一次。只为实际余留失败扩查，不添加每函数签收或重复全量测试。每个可写 repo 使用独立 worktree，ROOT 协调，不写当前冻结作者工具。

### C — ROOT 原 41 项大节点回放

不改原 CaseSpec/oracle/fixture/request/期待；新 attempt、新 scratch。原 `40 PASS/1 FAIL` 保存，明确对照最后 case 从 provider_unavailable/无原因 → not_found/call_after_as_of，eligible=false、ET1/CWPimport0、512 字节 usage 保真；整个矩阵仍必须满足原 30s/180s、原始 SHA、cleanup 和完整用量要求。

一次非作者范围验收后由 ROOT 正常提交/并线/推送/必要定点同步。离线合同绿不声称真实 FMP 权益、网络、OCR、LLM或收入模型质量认证。

## 6. 证据与恢复

原 attempt：`company-wiki/.tmp/w06-root-matrix-evidence/attempt-1f64f745d3a94506ae4bc35c8997b562/`，本目录 inputs-before/after JSON 只摘录 cutoff case，不复制全报告或数据湖。9 个实际矩阵模块 binding、12 个 CWP frozen product、21 份输入文件 SHA 均检查。本诊断只在本目录写报告/manifest，没有创建执行 scratch，故没有需要删的原件/测试临时根。

ET CodeGraph 未初始化；遵守只读范围，没有初始化。使用已知正式入口直接读取源码；FF 路径/测试/PWF 由独立诊断 agent 复核。不把较早原工具 19/21/1 或旧 unit PASS 作为当前产品验收。

**Next Step**：ROOT 指派 ET/FF 不重叠的最小 TDD 写集，节点 B 后统一跑原 41 矩阵；本诊断作者 STOP，不改产品。
