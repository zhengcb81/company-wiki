# N4：可运行的叙述批次、真实模型计量与持久恢复

> **2026-10-06预算已答复：**用户“批准提高token预算”，对应待答的累计160,000方案；费用仍$0.10，保留全部旧未知账与FX余量，不改Config。RF fresh main/remote均6e6b817a，owner两份周日志保持。以下待答描述仅为历史；现在按provider分run执行实际MiMo P01/P04、DeepSeek P07/T01及各自零模型policy。价格已复核官方页，保守沿用既有无缓存国内/FX6 proxy，不凭GET/套餐估算冒充真实账单。

> **本轮启动被自动审批拒绝：**run05命令未创建进程；原因是审批认为此前具体外发目的地仅MiniMax，未明确覆盖MiMo与两份原文。已在UI一次列出MiMo P01/P04和DeepSeek P07/T01、原语言精选片段及两家端点请求授权。答复之前保持0 POST；原token阻塞已解除，不能把此次拒绝当缺凭证/产品测试失败，也不能换命令或端点绕过。

> **2026-10-06 当前交接（覆盖下方2026-10-03/05旧恢复点）：**P5-FF/STORAGE/RF已验收并发布，RF正式main6e6b817a与安装依赖一致；旧全量writer退出，生产存储清理与S6说明/控制收尾已完成，e481578/CI37399248994一次全绿，不重做A/B、P5、清理或三个并行档试验。真实N4C摘要POST尚未验收。正式MiMo为`mimo-v2.6-flash`（`https://token-plan-cn.xiaomimimo.com/v1`），DeepSeek为`deepseek-flash`（`https://api.deepseek.com`），均读取既有Config与环境密钥、8192/温度1.0；[配置只读收据](harness_lanes/results/n4c_flash_preflight_2026-10-05.json)两家GET200不等于摘要成功。旧`mimo-v2.5-pro`与401说明只作历史记录，不能据此再改模型或要求换key。
>
> **最新累计预算恢复点：**[run04](harness_lanes/results/n4c_live_2026-10-05_run04.json)之后保守已占58,523 tokens/33,884 microUSD，另留历史FX余量2,764；60k只剩1,477 tokens，不能容纳配置8192的输出预留。160k累计token cap问题尚待答复，美元仍上限$0.10，不退未知账，不重启旧run清账。授权到达后按当前细则滚动做MiMo P01年报/P04招股、DeepSeek P07中文IR/T01英文电话会，每批加零模型policy对照，provider分run、账本统一累计、RF实际读取与引用/原语言/恢复/总空间同一大节点验收；不把models清单、HTTP200或未生成final当完成证据。当前唯一施工顺序以[总计划Next Step](task_plan.md#next-step)为准。

> **2026-10-05 当前状态：配置遵从修正已实现并完成离线节点验收。**真实入口使用 `scripts/narrative_batch_configured.py` → 既有 `Config.load()` → child-local HTTP Worker；model/base_url/key-env/max_tokens/temperature/reasoning_split均来自既有配置。当前为国内端点、MiniMax-M3、8192、1.0、reasoning_split=true；没有配置的 thinking 不擅自设置。请求文件里旧模型参数不能覆盖配置。零外部LLM调用完成配置测试；真实N4C仍未通过。

> **N4C预算与事实：**run02终态budget_exhausted，无final/RF实读；含旧unknown累计33,660 tokens/16,580 microUSD（不是账单），下一批最多26,340 tokens/$0.083420。国内只读models认证200、国际401证明之前试点端点绕过配置；不把GET结果冒称run02的POST status，也不退未知费用。两次live测试根已恢复，原件/生产/owner不变。截断null-content usage修复 `c543f6a` 的精确SHA CI已绿。

> **2026-10-05 追加完成：**私有投影prompt1.3.0/request schema1.1：`evidence_columns=[id,raw_text,source_role,quality_flags]`，`evidence`用行数组；省略的末尾role/flags继承default_*，例外与空flags逐条保留。每条原文不改，alias→canonical ID仅本地映射，model input hash及持久attempt request hash绑定该映射；摘要入库前还原并验证正式引用。未知/重复映射拒绝，公开SourceRef/Narrative wire不改。selector0.3.1补英文政策标题；通用IR类型也可正确route，完整空扫描才skip。134 Unit+3实际CLI/Worker E2E GREEN。真实招股请求45,471→16,543 B、含8192输出最坏24,863tokens，下一先核价格/套餐再只做P04+policy有限批，以actualusage滚动余量；不一次发四份/不改配置/不退unknown。N4C最终验收仍未完成。

> **并行与已完成边界：**G1/S3、N4A/B和N4-T1/T2已收口，不重复施工。P5三个外包用户已确认开工，见[P5接口总包](harness_lanes/p5_parallel_packages_2026-10-05.md)；MAIN不改它们的独占写集，交付随到随验收。下方旧记录为追溯背景，当前顺序以主计划Next Step为准。

## 1. 已核缺口与目标

### 2026-10-06 N4C恢复准备（MAIN独占，不新建审批门）

上一节点S6已发布/CI绿，本节点先核RF main6e6b817a及owner日志。新增`tools/n4c_live_preflight.py`作为可提交的零模型准备入口：读取原有AUTO未知账+run02及后续小收据，推导剩余预算，不退款；实读P01年报/P04招股/P07 IR/T01 TXT固定SHA，不复制raw；从明确RF提交只读导出当前narrative CLI依赖闭包，在独立短根执行help后清根。配置只经Config.load读取，报告只存无秘密字段。原件/生产/owner前后不变，0模型/下载；预算不足只如实报告，不调整cap或参数。

离线预检只证明资料、账本、配置与consumer bootstrap可用，不等于摘要/真实消费验收。实际四类型覆盖按节点C滚动完成；两家各分run，复用同一累计费用，先小批确认usage再扩展，不用两类样本宣称四类真实模型全过。旧tmp driver在POST前须更新RF固定SHA并通过本入口；收据保存与finally恢复由实际driver承担，不另建控制数据库。

离线预检已实跑GREEN并发布061f534，精确CI37400256960 attempt1 success：当前RF6e6b817a的6模块闭包help退出0，四份原件固定SHA/size通过；真实旧账58523 tokens/33884 microUSD，unknown 4、unsettled 0；费用扣FX余量后剩63352 microUSD，token仅剩1477。正式小收据见[harness_lanes/results/n4c_current_main_preflight_2026-10-06.json](harness_lanes/results/n4c_current_main_preflight_2026-10-06.json)。独立n4pf根恢复absent，原件、生产、owner/用户配置不变，0 provider/POST/download。现有收据不覆盖，后续状态变动用新的output文件名重跑。

```powershell
python tools/n4c_live_preflight.py --rf-root 'C:/Users/郑曾波/Projects/revenue-forecast' --rf-head 6e6b817a1a6e4567293a4dcb835815f3be508a03 --output '<新的小收据JSON路径>'
```

待用`tmp/n4c_provider_live_driver.py`已对齐当前RF，新增`--sample-ids P01 P04`或`P07 T01`供小批覆盖；help已验证。累计token授权到达后先MiMo年报/招股两份，再按实际账单proxy/usage余量做DeepSeek IR/英文电话会（每批另加零模型policy），不要直接同时发四份或两provider同时发。序号用尚未有报告的新run-number，原件/metadata为现有fixture，不能把合成身份当live验证。失败记录照计；全部四类实际生成、真实RF消费/引用回放、原语言、空间/恢复通过才关闭N4C。

**2026-10-06计费接线补漏：**临时driver原先只glob `n4c_live_2026-10-05_run*.json`，跨日收据可能漏计；现已把重复的旧账/run02/run03/后续序号求和删除，增加tools到导入路径并直接调用已提交的`n4c_live_preflight.prior_budget()`。累计tokens/microUSD取该结果，报告的`prior_budget`保存同一结果；全部日期、unknown及重复run拒绝语义因此一致。重新构造driver时必须复用这一个汇总入口，不复制旧日期硬编码算法。计算余量后、创建ROOT之前，若余量不足`model_options['max_output_tokens']`或费用余量≤0，抛出`CAMPAIGN_BUDGET_CANNOT_RESERVE_CONFIGURED_OUTPUT`；这是现有资源上限执行，不增加授权文件。

真实默认60k命令已零模型验证为exit1/上述错误，`tmp/n4live05x5`及run05付费收据仍absent，help正常。跨日+107 tokens/+211 microUSD的隔离夹具正确累加，重复run拒绝，夹具finally恢复absent；真实累计58523/33884和unknown4未改。小结果见[计费接线验证](harness_lanes/results/n4c_campaign_accounting_check_2026-10-06.json)。此结果不是真实摘要验收，token cap答复仍待；不要为绕开拒绝降低已配置输出参数或清空旧账。

1. 生产factory、薄HTTP、完整prompt1.1、真实usage与同AUTO持久预算已发布9ccd29f；测试Replay不当真实provider能力。
2. scope已贯通claim/promotion/reaper/outbox/prepared，S0/N4A发布ff5396c；不重新实现同一范围接口。
3. 有限batch CLI已串event/DAG/Supervisor/dispatcher。67项集中绿验证同run幂等/预算/源SHA/空间cap/目录恢复；生产小批前还要跨run、父kill/ACK与统一owner恢复收口。
4. terminal receipt已实装：只在三job SUCCEEDED、effect verified/outbox delivered、exact final visible+实读hash后去attempt正文；预算与小outbox DTO不动。物理SQLite释放是S6另测，不能把逻辑结果压缩当GB释放。
5. 跨run同源冲突已先RED后修：effect_key含验证job+bundle SHA，work-key/2含publication effect；三个真实CLI run绿，相同正文对象只有一份，旧pin不漂移。升级前effect薄兼容work-key/1，prepared恢复绿；SourceRef/wire/Store通用幂等未放松。
6. OS mutex死亡自动释放，generation CAS/scoped obsolete reaper已实现；实读确认当前无独立AUTO生产daemon，factory已经严格run scope。实际风险是旧catalogWorker/startup/全量派生入口，控制面独立。统一自动owner、退役旧启动路径须在生产小批前完成，不能猜previousrun就可接管；generic scope=None保留库兼容。

目标入口接受明确 SourceRef 列表、当前 catalog 配置、profile、文档/时间/token/费用上限；按 `event→DAG→worker→verify→outbox→visible artifact` 完成并返回 pathless 收据。退出/暂停/杀进程后可从原任务库继续；不自动下载、翻译或生成投资判断。

## 2. 固定接口与文件归属

### N4A：本批 scope（可先实施，无 schema 升级）

- `AutomationStore.claim_next_ready/claim_next_outbox/promote_ready_jobs/reap_expired_attempts` 增加可选 keyword `allowed_job_ids: tuple[str, ...] | None = None`。None 保留原 daemon 语义；空 tuple 表示无工作/无状态修改，不能回退全库。非字符串、空/带边缘空白 ID、超界输入拒绝；去重后最多 900 ID，SQL 参数绑定，不拼 ID 值。
- scope 在读取候选的同一事务 SQL 中筛选，不先领取再放回。终止依赖传播也只更新 scope 中的 child；scope 外 parent 仍可只读判断依赖。
- `Worker`、`WorkerProcessSpec`、`SupervisorConfig` 贯通同一个 `allowed_job_ids`；默认 None 兼容现有工位。Supervisor 的 maintenance 必须同 scope reap/promote。
- `NarrativeEffectDispatcher` 接收可选同 scope；claim、ACK 后 prepared reconciliation 都不得激活非本批 job 的 effect。catalog prepared 列表需先按本批 effect ID 过滤再 LIMIT，避免前 100 个外批对象导致本批饥饿。
- 修改归属：AUTO store/worker/process/supervisor/projection 与 catalog 的 prepared 列表窄过滤；对应 `tests/unit/test_automation_batch_scope.py` 和 `tests/integration/test_narrative_batch_scope_e2e.py`。不改其他仓库。

### N4B：composition / 计量 / 模型（N4A 后）

- 新 production factory 是 importable module-level function `create_runtime(spec: WorkerProcessSpec) -> WorkerRuntime`；只在 child 构造 reader/model/本地 connection。compute 不持模型；model/mixed 一个模型实例，首版模型并发 1。
- 新 batch application/CLI 复用 scheduler、Supervisor、runtime controller、dispatcher。部署路径只在 composition options；业务 DTO 只用 SourceRef / ID / hash。优先一个明确的 `company-wiki-narrative-batch`，不把只读 transport 变 writer。
- request：`schema_version=narrative-batch-request/1`、`sources`（1–100 精确 SourceRef、重复折叠）、`profile=P1|P2|P4`（默认 P1）、`max_seconds`、`max_tokens`、`max_cost_usd`、模型配置的非秘密标识。配置/refs/hash 校验后确定精确 DAG job IDs，持久 run ID/输入 hash；相同 run 恢复，输入/模型/prompt/selector 版本变化具名冲突或新 generation，不能悄悄复用。
- 同一 AUTO store 同时一个 batch coordinator。所有权是自动运行互斥/lease，不是人工授权合同；不能抢已有活跃 owner，不能 pause 其他活跃运行。沿用runtime generation；把主动有限批次与后台暂停明确分开，迁移LegacyWorkerControl调用者后删除旧新互锁，开始/退出/恢复有测试；不长持 CatalogOperationLock 等待解析/HTTP。
- `NarrativeModelResponse` 增加明确 usage/elapsed 信息；无 usage 标 unknown，不能用 0 伪装。现有 replay fixture 可明确为测试计量，产品不引用它。
- 一个薄 OpenAI-compatible HTTP adapter，一次 `generate` 至多一次 provider 请求，无隐式重试、fallback、全局成本日志。凭证从指定 env 在 child 读取，不进入 request/options/日志；网络 timeout、请求/响应字节 cap、错误体限长/脱敏。429/timeout 按既有 Worker retry；无 key 预检具名拒绝。
- 在 AUTO 原数据库新增最小 versioned migration（run/budget 与每 attempt model reservation）。金额用整数 micro-USD、token 用整数，避免 float 累积；同事务预留，两个进程不能超额。绑定 run/attempt/request SHA/model/pricing version，成功记录 provider usage + 配置价格估算，未知 usage/超时/进程失联保留保守 reservation。已结束请求结果无有效摘要也计量；输出截断具名失败。
- reserve 在 HTTP 之前、settle 在 decode/summary 校验之前；不把失败费用丢掉。输入上界按实际 UTF-8 request bytes 加 framing 的保守 token 上界，输出由 provider token cap 决定；供应商 usage 超声明上界则记异常并停止后续外发。不承诺外部 paid call 恰好一次；未知 reservation 不自动释放或伪造 0。
- pricing 是显式配置的带日期/来源费率，计量标 `estimated_usd`，不是供应商账单。2026-10-03 官方[MiniMax PAYG 页面](https://platform.minimax.io/subscribe/token-plan?tab=api-enterprise) M3 ≤512K 标输入 $0.3/M、输出 $1.2/M、cache read $0.06/M；首版保守按所有输入非 cache 计，不从旧 `_PROVIDER_PRICING` 推断新模型价格。仅作为本次候选配置，不自动购买套餐。
- prompt 明确 draft 完整 schema、字段值范围、引用/角色/情态、同语言/不翻译/只给来源摘要；从现行 summary contract 核对后版本升级。不增加模型自我审查第二轮调用。

### N4B：终态中间结果降容

- 只在本来源整个 DAG 终态、effect ACK 且对应工件 visible / binding 匹配后压缩中间正文。active/retry/prepared/ACK 丢失窗口一律保留；skip 保留小 coverage/skip 收据。
- 保留 job/event/source/version/attempt/error/usage/hash 与 final artifact/effect ID，不重复 quote。读取完成工件走已发布 transport；恢复不能从已压缩 result 重新计算依赖，若 lineage 变化生成新 DAG。保留最小 trace，不写第二份 bundle。
- scope 精确、幂等、停机后可继续；旧 evidence/span ID 与 B3 archive 退役另按 G-D，不借此删历史事实。

### N4B：避免再次积累大体积记录

- 原件一份、可用最终叙述包一份、小型来源/usage/失败收据一份；AUTO终态和outbox不再保存同一quote/bundle正文。全文转换只作有期限的解析临时文件；不要重新给全部财务表格/单元格建立百万级span。skip只留原因/coverage/来源引用，不留全文派生。
- 默认不自动生成完整catalog备份、gzip退休span或zstd旧库。确有一次性schema迁移时使用原有维护机制，迁移节点成功后立即按绑定收据收尾，不把同一内容无限保留多份。原文和来源/版本事实仍保留。
- 新批次只增加三个可配置空间预算：单文档最终持久正文2MiB、新叙述流程累计持久增量1GiB、所有该批临时文件峰值2GiB。原始下载和现存legacy目录不占“新增”额度，也不能因额度不足被删。开跑前记录既有目录基线；HTTP前预留本次输出上界，存储不足具名停该批，不循环重试/复制全文。若优质长文确实超过单文档额度，报partial与被截内容的coverage，不静默丢失、不伪报完整；由配置调整下一批。
- 可恢复的active/prepared工作继续保留；退出先清本次临时解析目录，失联目录由现有run/lease状态回收，无活跃owner才能删除。测试也只用独立短根；交付前清自己创建的根，历史工作树在交付并线后及时移除。日志只记ID/hash/状态/字节/token/费用，不重复正文；错误体仍沿用现有限长。
- 测试目录创建、pytest运行和finally清理使用同一OS账号。2026-10-03旧临时树实证：pytest owner-only ACL让另一账号读不到，不是生产权限门；不要因此放宽生产ACL或把不可读统计当零。正常用户发布/测试优先正常用户短根；若用sandbox跑隔离测试，就在同一sandbox清其精确根。Windows/Linux各清自己的run root；测试失败也执行finally并记录残留路径/bytes，不把反复排错基线留在仓库。该要求只并入现有节点B/C恢复原样检查，不增加审查门。
- 总容量统计包含新artifact、AUTO数据库/WAL、metadata、运行日志和临时峰值，不能只报最终bundle很小；SQLite逻辑prune和文件体积分别记录。与原文目录/旧库空间分别出数，避免把全仓45GB误认成46GiB旧DB反弹。预算/重复正文/临时恢复清理测试并入下方节点B，不新增小节点审查。

## 3. TDD 与三个大节点

### 2026-10-04 MAIN补充：模型输入投影收缩

真实失败run只读测量显示：招股书160条span原文共12,201 B，HTTP请求252,185 B；完整EvidenceSpan中的坐标、hash、parser和selection规则重复占据多数输入。60,000-token保守上界因此拒绝请求。MAIN独占改造 automation/narrative_model.py 与新测试 test_narrative_model_request.py，和N4-T1/T2写集互斥。

先RED证明160条合成中文证据可全部保留而模型请求上界低于60,000 token。模型投影仅保留每条span_id、原文、source_role及非空quality_flags；来源身份和选择coverage只附一次。模型只返回证据ID，定位由完整select结果负责，不重复发送locator和空quality_flags数组。完整EvidenceSpan仍保留在select结果，摘要校验/回放及最终artifact使用原合同；不得修改证据ID、截断原文、删片段或放宽账本估算来达标。prompt version升级，绑定新请求hash，使旧run不能静默复用新提示。

GREEN集中验证请求大小、角色/不稳定定位/原语言、证据保留、输入hash变化及现有handler/正式CLI端到端。再只读复测旧run的真实选择结果，只输出字节与计数；不发HTTP、不改旧账本。真实费用由MAIN以后新run测量，不把请求字节节省宣称为实际账单节省。

### 节点 A：scope 与持久记账

先 RED：更高优先级外批 READY；外批 RETRY_WAIT / terminal-parent child / expired attempt；外批同类 outbox；前 100 个外批 prepared；空 scope；真实 spawn factory 收到 scope。预算再覆盖双进程 reserve、相同 attempt 幂等/冲突、kill-before-request / kill-after-request-unknown、失败/坏JSON仍收费、micro-USD 上界。v2→v3 小库 migration、回滚/原表事实保留。实现后集中相关单元/集成，无全仓 coverage。

### 节点 B：正式 batch 端到端（隔离，无付费）

使用正式 production factory、真实独立 CLI 和本地 HTTP stub（测试服务，不是 production replay），走完整 DAG/outbox/transport。多文档 + skip；中英输出不翻译；同 run 恢复无重复调用；源 hash 改变拒绝；ACK 丢失和 worker kill 后复原；费用不足不发请求；stdout/日志无 key；外批任务/DB rows不变。本地服务给真实格式 usage 与错误/timeout；不要求每 helper 审查。

终态降容加入同节点：before/after artifact/ref 读取一致、prune 前后 resume 幂等、pending 不 prune、正文不会在 attempt/effect 重复保留。总增量算 final objects + AUTO DB/WAL + metadata/logs/temp（非仅 bundle size）。有 SQLite freelist 时区分逻辑记录缩小与实际文件释放。

### 节点 C：真实小批与发布

固定独立测试根复制 P01 年报、P04 招股、P07 IR、T01英文TXT，只读原件；P1 基线，P2/P4仅在同批显示实质提升/内存预算内后选择，不以进程数承诺更快。live 模型最多小批明确预算（首次最多 $0.10、60,000 tokens、1 个模型进程；超过只停该批），先检测当前实际 key 可用性，不输出 key。不调用付费 FMP。

自动校验 citation/hash/locator/语言/来源摘要 schema；记录实际模型 usage/估算费用/elapsed/失败、逐份 coverage 与 needs_review/partial 诊断。若真实模型不能稳定遵守合同，保留红证据修 prompt/adapter，不删断言、不开全库。复用 G-C consumer 对新真实产物读取，不重复旧四份 Replay 验收。

所有测试配置/控制/DB/cache/temp/log 均在 unique run root；finally 仅删除本次创建子树，原件 SHA/mtime 与生产配置/控制 fingerprint 前后相同，目录恢复基线。不得把外发凭证写计划或收据。普通 commit/push、已有精简 CI 绿后记录发布。通过并不自动启动无限 daemon；先有限显式批次，再按吞吐/增量逐批扩展。

## 4. 顺序与完成定义

### 2026-10-05 配置遵从修正（当前先做）

真实模型的 composition 必须先调用已有 `scripts/config.py::Config.load()`，遵守项目 `.env` 对受管 LLM key 的既定优先级；不复制 provider 默认表、不自选国际端点、不写死模型或输出上限。将加载后的 `config.llm` 转为无秘密的 HTTP options，转发 model/base_url/api_key_env/max_tokens/temperature 及既定 MiniMax reasoning_split，输出字段遵守现有 LLMClient 的 provider 策略。当前配置没有关闭 thinking，试点不得擅自添加 `thinking=disabled`。模型进程保持 child-local，不复用 legacy 全局 LLMClient；凭证值只留进程环境，不能进入 request、账本或报告。

已用配置→HTTP 请求及实际 CLI/Worker 的离线测试框住实现。正式 composition 入口是 `python -B scripts/narrative_batch_configured.py`，其余 `--project-root/--catalog-config/--automation-db/--work-dir/--request` 沿用有限batch CLI；request的model可省略，真实参数从默认 `Config.load()` 取得。`--llm-config`只选已有加载器的配置路径；离线测试使用独立fixture YAML和显式loopback开关，不改生产配置。底层DTO CLI仍保留纯组合能力，后续真实试点使用配置入口。单次/累计 token 与费用预算是资源限制，不能被用作理由悄悄改写配置中的模型参数。下一真实批最多 26,340 tokens/$0.083420；先完成离线准入测量，不够则拆批，不能重复无证据 paid call。prompt alias 优化在该修正之后实施，保留完整选中正文及 canonical citation 映射，不删证据凑额度。

1. G-C来源消费及B1/B3/B4已完成；现在按task_plan先S0收口、N4A独占并行，不重新恢复/重hash已删除归档或重做旧checkout整理。
2. N4A scope 先 RED→GREEN；与独立模型 HTTP 新文件可以并行，共享 Store/schema/prompt 只由一条 owner 实施。
3. N4B 计量/预算/模型 prompt/factory/batch/retention的节点A+B已集中验收并通过；不重复开工或重跑全套。
4. N4C真实小批→消费者读取→普通发布，须等主计划G1与S3先收口；之后再更新 G-D B2 调用者清单和生产可清理批次。
5. 复核已完成B3收据，不重做旧span墓碑/恢复；不能将N4最终包2%样本比率当总空间已验收。

N4 完成必须有生产代码入口、正常/故障真实 CLI 收据、usage/未知请求账本、batch isolation、恢复与总占用实测。只新增测试 factory、仅 status 变绿、仅保存几份 Replay bundle 均不算完成。

## 5. N4C施工细节（按主计划排在G1/S3之后）

1. 跨run RED先行：同源runA发布、runB相同draft发布、runC不同合法draft发布；effect各自绑定verify job、工件各自exact pin回读，旧pin不取latest；相同正文object按SHA只有一份，runB同run恢复零额外POST。新run用独立work-dir，同run复用baseline。
2. 最小实现：verify effect action hash绑定`verification_job_id + bundle_sha256`，intended_after_hash仍纯bundle SHA；projector work key升级`/2`绑定publication effect key。不新建run→artifact映射/签名文件，不放松ArtifactStore冲突校验。显式新run当前可能再付费，不冒称跨run缓存零模型调用；未来缓存策略由实测决定。
3. 自动owner收敛：production factory已固定run.scope，AUTO CLI现只有只读status/doctor/plan；不虚构已配置AUTO daemon。退役source_catalog `worker/--once`、`worker-start/resume`、install-startup、PS/VBS旧启动和全量normalize/run路径；保留status/stop/uninstall/scan/query/export来源维护。run行一个nullable last_runtime_generation，通过v3→v4迁移；activate_run与gate CAS同AUTO事务绑定，PAUSED可启本run、ENABLED仅匹配本run当前generation可恢复；未知/他run零修改具名拒绝，不写owner签收文件。OS mutex证活进程、binding证恢复归属；正式CLI父kill恢复已通过，旧generation attempt被隔离后reserved费用转unknown且原额保留；提交ACK丢失用commit后注入超时验证重试幂等。尚余source_catalog旧执行入口退出。FF ensure来源采集仍在短commit锁，不加入长期处理owner锁。
4. 节点B本地HTTP正式CLI父进程kill后同run恢复、文件mutex重取、原始来源/旁路任务不变已绿。费用对账事务另以提交成功但返回ACK丢失故障注入证明可重试。batch deadline从入口开始计时，覆盖来源读取、准备、解析、提交；持久/临时峰值按实际文件与SQLite WAL统计，只有总增量和coverage达标才进入四份真实样本节点C。
5. CWP producer caps与FF-S3现已在主线汇合：CNINFO能力以1.2.0声明并经公开真实年报完成下载限额/哈希闭环；FF-S3已进入FF main。Dayu仍不支持真实bounded transport，相关硬限额请求在外发前拒绝。N4专属下一待办是N4C真实样本多文档批次、1/2/4并行吞吐和新增空间测量；它排在主计划G1门禁精简及S3虚拟化收口之后。

### 2026-10-04 真样本入场条件（只读预检结果）

N4C的四种文档仍按主计划在G1/S3之后运行。预选不能直接用数据库中的状态标签替代来源验证；每份样本先由SourceRef query取得精确版本，再由既有pathless open/export验证身份、as-of、元数据可见性与原文字节SHA。

| 类别 | 当前候选 | 本次只读证据 | N4C资格 |
|---|---|---|---|
| 年报 | 金山云2025年报 | SHA `efe2ccd9…`，4,826,662 B；已有4,779 parsed spans及normalized/summary工件 | active且可验证；批次必须作为复用基线，不冒充本次新生成 |
| 半年报 | 金山云2025中报 | SHA `4f589193…`，3,396,644 B；已有2,056 spans和派生工件 | active且可验证；测幂等复用 |
| 季报 | 金山云截至2026-03-31季度业绩 | SHA `37f0eb13…`，309,955 B；active，尚无spans/artifacts | 候选新处理输入；只取经营描述，财务数值不扩成全篇摘要 |
| 投资者关系 | 三七互娱2026-05-11业绩说明会记录 | SHA `3e25aab4…`，133,294 B；narrative_derivation打开通过，正文有具体产品/出海进展及模板话术 | manifest-only SourceExport可在验证SourceRef/原文SHA后输出，缺失capture字段保持null；暂不能进入Worker batch，因为`build_batch_events`仍要求非空`language`。先闭合下方语言输入，再实测消费；不能把null当成已证实元数据 |
| 招股书 | 盛美上海IPO招股说明书 | 旧记录SHA `02adc989…`，7,073,891 B；document和original-primary location均retired | 暂不合格：不可直接用旧SourceRef或物理路径。只有正式再入库/验证取得active可见SourceRef并匹配原文SHA后才能纳入 |
| 电话会TXT | earnings-transcripts既有原语言文件 | CWP当前7条active transcript记录是PDF/JSON sidecar；单次live FMP调用返回402，没有新TXT入库 | 需ET正式工具/既有TXT的完整来源合同导入；不可把旧PDF或假provider envelope算作TXT闭环 |

active catalog盘点总数：年报46、半年报8、季报7、IR 3,682、电话会7；229份招股书全部retired。以上来源分类未调用LLM、未启动Worker、未修改生产数据库，也没有复制raw。实际N4C不因这些预检提前开始：S3关闭后先验证招股书、IR、ET TXT进入既有SourceRef合同；任一类型无合格来源就继续报告缺口，不降低SHA/来源身份/公开日期要求。manifest可稀疏不代表Worker输入齐全。并发1/2/4比较仍需同一批次、相同source set与确定性输出基准，并量实际模型费用、最终工件、SQLite/WAL和scratch峰值。

### RF/CWP接口复核与IR metadata前置（2026-10-04，只读）

- 财报下游沿用RF已发布`SourceRef/2.0`和`company_wiki_source_reader_v2.open_source_version_v2`：pathless精确ref→CWP `filing_reuse` CLI→RF实读bytes SHA/size、身份/财年/期间、published/retrieved与as-of复核。`not_reviewed`不阻断读取。CWP不得复制这一套财报校验器。
- RF `company_wiki_narrative_reader.py`消费已有`narrative-read-request/1`工件引用；原件发现、叙述选择/生成仍由CWP现有SourceVersionReader和N4 Worker负责。
- 三七互娱2026-05-11 IR的document/source active且SHA可实读，但`source_metadata_assertions`行数为0；metadata JSON仅有scanner/acquisition键，所以v2 `describe_version`没有可投影的normalized metadata。现有`upsert_verified_assertion`写入verified/shadow；`activation.apply_activation`才把行变成当前v2 snapshot可见。不能用手动SQL改active、虚构fiscal year/period，或把“raw能打开”当完整SourceExport。
- N4C进入真实IR样本前，先在CWP G1/S3收口内明确并验证一个简单的非周期IR元数据生成路径：只需真实document/source IDs、SHA/size、公司证券身份、source type/document kind、已证实公开日及必要的检索事实；不强制财报期次。不增加人工逐文档签收；如果仍必须走shadow cutover，证明它可由已验证元数据自动、幂等地通过现行snapshot，而不绕过共享解析器。与此同时保留RF财报reader的identity/period/as-of合同。
- 招股书/ET TXT相同原则：正式active SourceRef、实际bytes SHA和可导出来源信息；只复用已有admission/importer。provider权益不可用时不编造ET TXT，不把旧Motley来源sidecar当新授权。

### Sparse SourceExport 与 Worker 语言输入（2026-10-04）

- SourceExport v2 的精确 SourceRef（document/source ID、SHA、byte size、MIME）和实际原文字节校验是必需项；display/provenance/财务期次字段可为null。v2 capture不透明或不存在时，只返回可见信息，不读取旧metadata桥、不推断缺失值、不因此拒绝整个pathless manifest。
- `filing_reuse`仍经过`describe_candidate`并要求财报消费所需的身份、期间和as-of条件；RF继续执行已发布的SourceRef字节/身份/期间校验。此改动不改变财报闭环规则。
- 已新增TDD合同：runtime v2关闭legacy bridge后，SourceVersionReader返回精确稀疏描述且财报复用仍blocked；SourceExport CLI用隔离合成catalog验证同一SourceRef可导出、metadata缺失字段全为null、citation span仍按原文校验，且fixture目录前后快照不变。阶段集中结果34 passed；真实IR尚未经过生产CLI导出。
- Worker语言桥现已实现：`build_batch_events`仅在manifest语言缺失时通过`SourceVersionReader.open_version(..., purpose="narrative_derivation")`打开SourceRef精确版本；复用`validate_opened_source`验证document/source ID、SHA、byte size、MIME及read-policy，再从同一已验证字节推导语言并写入event payload/input hash。manifest已有语言优先，不重新读取原文；无法可靠分类以具名错误退出，不按市场猜测、不翻译、不调用LLM。
- 新模块`narrative_language.py`支持UTF-8纯文本、既有transcript HTML/JSON抽取器及PDF前5页；只归类`zh`/`en`/`mixed`，限制读取样本大小，对无可分类字母、损坏文本、未知脚本、无效PDF与不支持MIME分别返回具名错误。PDF/文本语言检测不落临时文件。selector/verify允许当前catalog语言为空；若当前catalog提供非空语言且与event pin冲突则拒绝。
- 集中责任包：`test_narrative_batch.py`、`test_narrative_language.py`、`test_narrative_source_guard.py`及`test_narrative_batch_cli_e2e.py`共**23 passed / 41.06s**。隔离CLI/真实Worker配本地HTTP模型夹具覆盖中/英/混合TXT、英文年报PDF、缺语言与有语言metadata的IR政策跳过；验证语言不翻译、引用/摘要language一致、重复执行不再次调用模型、原始夹具字节与foreign jobs不变。另有Ruff与mypy聚焦检查通过。
- 这只关闭“稀疏SourceExport无法进入Worker”的技术缺口，不代表N4C真实批次完成。仍需S3/ET-DEADLINE收口，并通过现有admission/import流程取得可见、active且原文字节SHA匹配的IR、招股书、ET TXT SourceRef。招股书现有候选为retired，IR缺normalized metadata assertion，ET live请求返回HTTP 402；未绕过这些来源合同，也未启动生产Worker/模型或触碰生产catalog/raw。样本不就绪就保持N4C pending。


## 2026-10-03 旧 Worker 入口退役状态

CWP 已删除 public `worker/--once`、后台 daemon、worker start/resume/pause、whole-catalog normalize/summarize/run 以及 startup install CLI。对应 PS/VBS launchers 与菜单已删除；生产只读检查证明没有运行进程或已安装 startup task。保留 `worker-status`、身份绑定 `worker-stop`、startup status/removal，以处理升级窗口内的残留 PID/任务。显式 `ensure`/`close-gap` 不再依赖旧 worker paused 状态；FF 使用的兼容参数现为 no-op，直到 FF-S3 合并后一起收敛。旧 `source_catalog.worker` Python 模块暂留作未暴露库兼容；它没有公开执行入口，也不会被新有限批次 factory 调用，后续若确定没有外部调用者再与 B2/派生清理合并删除。

2026-10-04 已完成原计划的 producer/FF 汇合：`--max-download-bytes`、`--max-download-seconds`、`--max-download-cost-usd` 贯通FF→CWP→CNINFO；真实BYD FY2024年报下载为10,092,140 B，SourceRef SHA与原始PDF一致。缺失/不支持限制的Dayu请求仍在provider外发前fail closed；direct acquisition不等待后台worker锁。N4下一节点为N4C，但当前MAIN先按总计划完成G1门禁与S3虚拟化收口，再做真实资料有限批次与并行/空间测量。
