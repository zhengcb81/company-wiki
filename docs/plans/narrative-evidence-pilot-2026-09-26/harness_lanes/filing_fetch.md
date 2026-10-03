# FF 独占施工卡：财报复用、精确下载与电话会议编排

> 可单独交给一个 filing-fetch harness。**唯一写入目录**：`C:\Users\郑曾波\Projects\filing-fetch` 的本仓集成 worktree。`filing-fetch-transcript-companion` 旧 worktree 只读参考；ET/CWP/RF、全局安装的 filing-fetch skill 只读。总指挥接收本仓实现后统一更新全局技能入口。不得读取或 stage `config/FMP_API_KEY.txt` 的内容。

> **2026-10-01 当前状态：**FF 根当前检出 `fcap@d35b6f5`，与 `origin/main` 同步；本地名为 `main` 的 ref `c9799b7` 比远端落后 39 个提交。SourceRef v2 worktree `5532ce0` 与 transcript companion worktree `29085f7` 当前无工作区改动，但 `fetch_filing.py`、`filing_contracts.py`、`transcript_companion.py`、`test_transcript_companion.py` 等核心路径有重叠。由一个 FF owner 在最新远端主线基础上收拢两条 WIP；不要让两个 harness 分别合并或覆盖同一文件。全局计划/S0b golden 与本仓 E2E 仍待验，不能把分支存在等同于功能已并线。

> **2026-10-03 状态更新：**单owner已在FF `codex/ff-source-companion-integration` 汇合SourceRef v2与companion；本仓v1、v2、ET `/2`、CWP真实import/verified-open与FF→CWP E2E为 **191 passed, 1 skipped**（旧生产opt-in skip；新E2E无skip）。CWP返回pathless SourceRef并统一保存原始JSON。FF/CWP commit/push收据待下方总计划记录；FF→CWP→RF正式consumer G-A仍是下一大节点。没有真实FMP API 请求或密钥读取。此状态取代2026-10-01“仍待汇合”的快照。

开工输入包：本卡、S0a observed 接口表、CWP/ET 的 S0b golden（未产时标 pending）、只读 P/T 样本清单和本仓 fake provider fixture；本仓只复制所需样本到自己的隔离测试根。

## 已知状态和依赖

2026-09-29 只读 `git worktree list` 所见是历史基线：主目录 `fcap@d35b6f5`，SourceRef v2 与 companion WIP 当时仍在早期提交。当前准确 HEAD、base 和 overlap 以本卡首段的 2026-10-01 更新为准。**只设这一名 FF 写入者**，先核 live refs 和脏树，把有效 WIP 保存为可恢复提交，再在基于实际最新 main 的单一集成分支内先完成 SourceRef v2、后移植 companion；逐 hunk 合并，不将两个脏树互相覆盖。CWP SourceRef/operation golden 与 ET tool `/2` golden 是外部输入；未冻结时可先写本仓测试和清理 WIP，不切默认路由。

## 输入、输出和职责

- 输入：公司/证券、market、精确 fiscal period 或 latest-as-of、显式采集意图；CWP `SourceRef 2.0`/source operation/verified read 接口（真实 producer golden），ET 的精确 transcript `/2` 工具（真实 golden）。
- 先问 CWP 已索引来源；精确已有报告直接复用。latest-as-of 查询 provider metadata 后判断 gap，未请求下载不打开网络正文。真实缺口只调用一次精确候选 CWP acquisition；CWP 保存 immutable raw、SHA 和来源版本，FF 不碰 CWP catalog/公司物理目录。
- 保持既有 v1 默认 JSON/退出码。显式 v2 envelope 输出逻辑 SourceRef、filing 与 transcript 各自状态、请求期间、缺口/失败原因；无稳定物理路径。版本由本仓**真实 serializer golden**固定，旧计划的 `1.3` 仅作兼容背景。财报成功/电话会失败分开报告，可单独重试 companion，不回滚已保存财报。
- 电话会议只在请求中能唯一确定 FY/Q 时调用 ET 一次。全年财报本身不推断 Q4；期次无法确定返回 `period_unresolved/not_requested` 类具名结果并且零抓取。原语言 TXT 交 CWP canonical import，不做 PDF 转录或翻译。

## 门禁清理和本仓施工顺序

1. 用 v1 golden 锁住当前用户 CLI。`fetch_filing.py` 的 `--allow-download` + 请求内五字段 authorization + policy export/hash 二次复核收敛为一个明确采集意图及 CWP 精确 `RequestPlan`；保留候选唯一、as-of、预算、错期、错误 SHA 和路径安全。FF 不实现第二套根目录 ACL。现有 `PausedWorkerScope` 仅为防止旧 Worker 并发副作用，其替换/保留须与 CWP 唯一 owner 和自动重试合同一致，不改成新的人工批准。
2. 完成 SourceRef v2 opt-in：FF 只持 CWP 逻辑引用和版本，不要求消费者传 raw root/path；纠正 WIP 中 response version 仍报旧号的问题。旧 fallback 只为真实存在的 v1 持久调用保留，切换后的无用 transport 删除。
3. 在同一分支移植 transcript companion：调用 ET 真 tool/CLI、CWP 真 transcript importer 边界，使用显式配置定位包入口，不猜相邻 checkout；仅 FY+Q 唯一时调用现行 `/2`，精确 period、独立状态和重试幂等。Motley 默认禁用且 FMP 缺 key/402/无权益时，companion 返回 `provider_unavailable`/entitlement 具名状态且 0 不必要正文网络，财报结果仍保留；不生成额外 rights-policy/reviewer/period authorization receipt。
4. 生成 FF envelope 正反例和 CLI 退出码表交总指挥；总指挥用它与 RF consumer 对接。FF 不修改 RF 的 prompt-review 状态处理。全局 filing-fetch skill 的最终安装/入口更新由总指挥在 G-A 通过后做，FF 只交补丁说明与验证命令。

## 独立测试包

- v1 保真与 v2 SourceRef：现行 `tests/test_fetch_filing.py`、`test_fc802_gap_orchestration.py`、`test_policy_containment_fc501.py`、`test_zr405_policy_roots.py`、`test_fc905b_envelope_fields.py`；`tests/test_source_ref_v2.py`、`test_source_ref_v2_db_query.py` **目前只在上述 SourceRef WIP 工作树，先导入有效实现/测试或新建后才运行**。负例包括未知版本、多余 path、错 SHA、as-of 后版本、撤回、stale gap、0 意外网络和超额。
- companion：`tests/test_transcript_companion.py` **目前只在上述 companion WIP 工作树，先导入或新建**；在旧 fake 单测外增加本仓 CLI→ET 真工具解析（可注入 fake HTTP）→CWP importer 真边界的隔离 E2E：一次成功、重复复用 0 下载、歧义期次 0 网络、两个 provider 均不可用时具名降级、财报成功/电话会失败、原语言 TXT 和 locator 回放。
- 隔离实例：`tests/test_e2e_isolated_wiki.py`，真实 FF CLI/CWP 入口，不 monkeypatch 掉 producer 和 consumer；正式 FF→CWP→RF、FF→ET→CWP 汇合由总指挥 G-A 负责。每次测试使用本仓专属不存在的短目录，退出时核测试根恢复、原文及生产 catalog 不变。

交接提供本仓 base/branch/commit、v1 与 v2 golden、ET `/2` 的消费版本、明确请求到 0/1 网络调用表、测试命令/退出和未解 hold。若 CWP/ET 生产者 golden 尚未冻结，标接口 `pending`，继续可独立的测试工作；不得自行猜字段并宣称跨仓完成。

**本线自动验收：**v1 默认 CLI 回归与 v2/companion 新路由测试通过；已索引复用/歧义期次/不可用provider不会触发多余正文调用，精确缺口最多一次下载；财报和电话会状态独立，原文/SourceRef可回放。只用短临时根；正式FF→CWP fixture E2E实测原始bytes、catalog与verified-open。G-A对RF消费者可用性仍须由总指挥另验。
