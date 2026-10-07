# G2-12：一次请求、一次发现、一个获取事务

**当前进度（2026-10-08）：**G5三包及FF实际安装已验收发布。G2十四组实现已有证据，最后组合节点也通过：真实IR/TXT、真制度零模型和错标题业务样本，当前已提交RF/SW读一致，同run新增POST0；60责任项/8.13秒、最终E2E1项/61.65秒，42退休合同复用首轮通过。发现并修复登记层派生类别覆写原声明造成的假冲突；源码正常提交/精确CI待完成后G2收口。生产/原件/owner零修改。见[G2当前矩阵与最后节点](g2_consolidated_node_2026-10-08.md)。随后R2真实元数据/ET登记→R3正式final与消费者→R5收口；R4不迁移。旧pending/paused是历史时点，不恢复审批或重复已绿长包。

**当前验收（2026-10-07）：**目标active。G5三包已验收并线发布；G2-12实际FF→ET→CWP链与获取实现已发布。本轮G2-08 FF安装系统修复完成：工具26e0e60/指导main211a56f已推，精确CI37696236234success；集中26责任项无警告，补9/12定点验证不相加。真实安装按入口闭包显式8文件、两物理目标各6差异，共12更新，实际入口help/只读check通过、重复0写；未选配置/输出/其他文件及18个owner/生产保护SHA不变，原件删除0。RF旧strict_targets/coverage/mtime漏项经当前源码核对已在G3修复，不重做、不重冻baseline。见[G2-08正式验收](g2_ff_installation_acceptance_2026-10-07.md)。下一步为G2十四组当前证据/指导与最后A/B节点核对，只补未覆盖的当下行为；之后R2→R3→R5，R4不迁移决策保持。全部PWF尚未完成，不用安装或试点通过冒充完成；下方paused/待安装/三文件等为历史估计，当前状态以页首为准。

锁键不含TTL/hash/请求caps；同target互斥覆盖暂存到真实最终解析，不同target能并行。canonical短锁等待使用同一实际deadline，staged SHA只核一次；可恢复kill和已入库复用责任保持。CloseGap是公共ensure薄包装；FF旧scope随第一次ensure传递，临时scope文件finally删除，无二次发现/下载。内部gap诊断按实际交易终态投影，不再令已完成v2请求伪装GAP。Python3.10无add_note时保留原清理异常与失败journal，责任测试绿。以下旧“paused/尚未联调/自然年猜测”为历史施工记录。

**G4接收后的继续点：**CWP已发布df7d7ba，SID正式执行分支已发布eb8495c/adapter1.3.0；CN路由root回到v2-clean-rewrite、version1.3.0、bounded=true三个值已由MAIN定点接管，其他配置值保持。最新年/半年/季报不再要求猜fiscal_year，SID五页有限窗口只在完整时返回真实候选；discovery_incomplete/bounded_discovery_empty应保留具名GAP，不能复用旧本地文件冒充latest。127 provider/CWP消费责任已绿；本单CWP获取源码仍未提交，下一节点是实际统一ensure/FF/ET/CWP下载→入库→只下载一次/幂等复用/清理。不要重复已绿G4包，不用未提交owner代码给联调伪造成功。目标paused；恢复后先做本线。旧预算工作树/1.2和强制latest年提示是历史记录，不能作为现行接线。

状态：in_progress。MAIN独占CWP、FF接线；SW/StockQA/RF三个外包写集不参与。本单细化已有G2-12，沿用G2A/G2B两个大节点，不新建每步签收。G2-01b已发布22dcc927，精确CI37603212398全部绿。

**最新施工：**G3三卡已ready并推7f678f7，其白名单不含本线获取/CLI/FF；外线若分派，MAIN不写其维护/RF/调查文件。新增财年、原件根重叠和清理失败journal的5项真实RED（旧13pass），责任修复后18pass/3.40秒；原件根隔离、仅CN年报API必要报告年提示、成功journal在暂存清理后写入。当前仍未发布，旧责任/CLI/FF/并发集中节点尚未完成。

实际施工：8项初始TDD为6RED/2pass，分层初版7pass/旧CloseGap1RED。93项扩展责任88pass/5fail尚待合同同步与真实反例补齐。整体替换CloseGap曾被自动审批拒绝且未执行，用户随后明确授权核心重写；这属于本次工具审批记录，不在项目中增加授权文件门。集中补充预算异常传播、target暂存安全清理、一次失败journal、共享budget有界重试、跨进程与真实最终读取后才发布。

## 基线与保护

- CWP master9946117；发卡时owner `config/source_acquisition.yaml` dirty，SHA3609e707；G4已验证仅三个CN字段并替代，其他字段未变，现配置已提交。该SHA为历史保护基线；测试仍不得写穿生产配置。
- FF main758e8f4c116ef9760c657433e4ccbfbd10652029；仅owner未跟踪`config/FMP_API_KEY.txt`，不读取密钥正文、不stage。MAIN用自己的FF工作树，先核已有目录归属/clean，再复用或新建，不能覆盖其他任务。
- Dayu/IQS零写；StockInfoDLSimple只调用现有已交付预算接口，不修改其owner文件。测试fake/loopback资料只在独立根，结束恢复absent；生产raw和17事实表保持，网络/供应商费用0。

## 实读问题

1. `AcquisitionCoordinator.resolve_or_stage`对latest无条件返回GAP；即使明确allow_download，也不会下载。
2. `CloseGapTransaction.execute`另走runtime snapshot→policy hash→gap hash→TTL授权→发现→锁内再发现→exact再发现→fetch/import/finalize。TTL参与mutex键；两个范围相同但TTL不同的调用可以重复fetch。
3. exact服务没有覆盖发现/下载/提交的同一target single-flight；writer只在入库阶段短锁和SHA去重，无法阻止重复provider读取。
4. GapPlan是对照诊断，不是无歧义target选择器：同year可能多个候选，旧close-gap任意取首条；不能把清理门禁变成任选一份PDF。
5. latest发现当前一律推as-of年减一，包括US/HK和季度，需按真实provider支持核语义。不可默认这些市场都是12月年结，不能把unsupported包装成已是最新。

## 各层唯一责任与接口

| 层 | 输入/输出 | 唯一责任 |
|---|---|---|
| 请求/FF | 既有SourceRequest+filing_intent+acquisition_limits | 一次明确操作意图、身份/期间/as-of、资源上限；不生成授权收据或路径 |
| Coordinator选源 | request+同一AcquisitionBudget→本地复用/缺口/歧义/已选DownloadCandidate | 一次有界metadata发现、验证身份/期间/公开cutoff、唯一target；无写/无fetch |
| Coordinator暂存 | 原已选candidate+request+同一budget→验真staged receipt/并发已入库复用 | 不再discover；读取中实际计量/当前deadline/暂存字节SHA/长度/类型/包含 |
| AcquisitionService | 上述组件+现有writer/journal | target single-flight覆盖锁内本地再查→fetch→canonical import→真实最终解析，唯一事务编排 |
| CanonicalSourceWriter | 同一request/candidate/receipt | 原件不可变、同SHA去重、单文件/sidecar登记和入库SHA；不发现、不签收 |
| CloseGap兼容 | 既有请求/可选旧binding | 薄转发同服务；旧hash/TTL/snapshot不决定许可；显式provider/accession范围及较低资源上限仍生效 |

查询候选与获取事务复用同一来源层，不复制另套latest算法到FF。若需要内部selected状态/prepare方法，仅为编排分阶段；不让它成为外部已完成结果，不增加权限DTO或第二任务库。SourceRef/SourceExport v2形状保持。

## 顺序与实施细则

1. **先RED**：新steady无snapshot、allow latest一次发现一次fetch、canonical一次，第二请求只metadata复核一次但fetch0。readonly latest仍GAP/无raw写。无意图、歧义、错公司/期间/provider/accession、未来公开、provider unavailable均fetch0，不能报最新。
2. **抽出prepare和stage**：保留旧staging-only接口兼容；生产ensure/旧close-gap共用新服务。exact本地命中零provider；latest发现有截止时间的metadata，每个candidate做责任校验后唯一选择。排名必须来自期间/真实公开日/明确amendment；同rank不同身份返回歧义，不拿字符串第一条或accession字典序猜。本地metadata再查可以多次，provider metadata正常一次。
3. **统一事务single-flight**：锁键由canonical目标（公司/市场/kind/provider/accession/期间）生成，不含签收hash/TTL/字节上限，不依赖全repo HEAD。锁内本地精确再解析，已入库者fetch0；同target的exact/latest/旧close-gap共用键，不同target可并行。等待吃同一budget剩余时间，不重建deadline/cost/bytes。锁外准备/计算，canonical writer保留现有短库锁。锁异常、fetch/验真/import/final resolve异常均journal失败、不得completed。
4. **退休CloseGap旧协议**：去除snapshot/plan/policy/expiry的许可校验及authorize构造；CLI的binding-file变可选，help说明操作/上限。旧binding是请求范围提示：显式provider/accessions与更低max_bytes/max_items保留；旧request/hash/TTL不是新意图签名。无binding的close-gap命令自身是明确的获取操作，不要求第二授权文件；FF的reuse_only不因此变为下载。包装器无独立fetch/重试/入库实现，结果仍用真实resolution/envelope。
5. **FF独立接线**：确认v2 fetch_if_missing已把allow+三个limits贯穿CWP一次ensure；latest不要再因GAP分叉到旧receipt签收、不要重置第二进程预算。v1历史模式也薄转发同服务；同步SKILL/reference/help及安装副本时保留用户配置。电话会companion继续走既有ET/CWP原语言TXT链，不翻译、不写Dayu。
6. **集中责任/联调后发布**：修正只测试退休签收的旧期待，保留实际来源/公开cutoff/SHA/资源/并发/恢复/失败可见性反例。正常commit/push、精确CI收据和PWF，外线交接独立接收。不重复已绿01b或13，不加入日常联网/长E2E。

## 集中测试包与真实边界

- CWP新`tests/contract/test_single_intent_latest_acquisition.py`：真实SQLite/唯一writer/fake bounded provider；metadata/fetch/canonical计数、无snapshot、旧hash/TTL不阻、当前资源和目标范围。
- 复用现有acquisition、gap_plan、close_gap FC801/FC804、canonical_writer、adapter_process、ensure_paused、source_operation_v2责任测试；签收本身的expired/stale期待按新合同调整，坏资料和实际资源期待不降低。
- 跨进程同target exact/latest/不同旧TTL：最多一次provider fetch/一次canonical写；首进程死于暂存/提交前后，下一请求真实再查恢复，不能靠伪成功。独立target可同时持锁；等待超时零fetch，usage不返还/重置。
- G2B：真实离线subprocess FF v1/v2→ET→CWP，初始缺件→获取→索引→SourceRef真实字节读取→再次零fetch；stdout/receipt/source/hash/身份/期次/as-of/语言/预算一致，超限与歧义zero ingress，测试资料都在独立根并恢复。
- 真实PDF/TXT只读复制至少一份，证明正式CLI/入库/重用路径；provider和metadata为明确隔离fixture，不冒称真实供应商成功/生产metadata。供应商权益/外部API无需本节点再花钱验证。

## 完成条件

当前ensure和close-gap/FF不再存在第二人工签收流程；同一个下载意图+同一实际budget完成有界、唯一target事务；所有完成结果有实际最终来源读取证明。旧wire可读不等于旧门继续执行；G2-12绿不代表整G2/PWF完成。生产准备仍在其后的R2。
