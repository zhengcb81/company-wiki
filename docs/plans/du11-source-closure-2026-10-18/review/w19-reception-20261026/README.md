# W19 ROOT接收与共因修复

## 2026-10-26 ROOT最终验收与主线发布

**组件实现、离线链、真实API、官方六值全部通过，已并线推送。** CWP `10def09e8fd1967e0b87434ae211d1fbaafbb090`（集成63a26230），FF `72024a8597e27607badbbfdd06c39446269d7010`（集成9758ee3）；两作者完整祖先保留。CWP精确CI40300969747、FF40301405046 completed/success，见本目录publication-ci文件；不能将此前pending记录改称当时已绿。

集中196项115.41秒、旧schema/reader/正常CI发现51项40.59秒、FF35项6.54秒；独审相关21项与这些有重叠。CWP正常pre-push154项52.43秒；FF正常完整快反馈933通过/7既有skip/+78subtests，110.87秒。pre-commit已捕获迁移测试3个无用局部变量，移除死代码、保留全部断言及明确schema1.4预期后正常提交。第一次因venv无pre_commit未执行，改用已有Conda正常hooks，没有跳过。

ROOT8个原反例、后续3个版本/覆盖反例、replay伪新观察、缺快照与legacy顺序质量及FF默认合同均有原始RED/GREEN。最终独审[实现/离线](independent/final-review2.md)和[官方六值补审](independent/supplement-official-review.md)各PASS/0 OPEN；原审查保留不重写范围。36源码/测试与两仓发布版逐LF SHA一致，见published-binding.json。

离线FF真实有界子进程→CWP→冻结原始provider字节：36/33/36期、9729源行、4049数值JSONPointer、12个返回引用直接打开、fetch_if_missing重复与只读复用各0exchange。ROOT和独立者各实际跑一条，约12秒；测试湖11,541,954B，重复原件增长0，物理空间-4,264,232B来自SQLite WAL checkpoint。原件/sidecar/config逐字节和mode=ro逻辑dump都不变；物理DB SHA不是immutable原件要求，前两版过严测试失败原样留存。每次临时根finally恢复不存在。见offline-boundary-v3.json及独立收据。

真实FF命令未patch：已有配置身份记录，中微三表/招商银行利润表，4HTTP/942986B/23.68秒/$0，二次均0HTTP，直接SourceRef可打开、六个中微API值与官方一致，生产config/catalog原字节稳定、测试根已清理。总预留8MiB/90秒，低于卡面20MB/300秒；见live-boundary-v1.json。未重复下载PDF：既有SourceRef d64c4108…aa5，9,165,875B，259页，独审逐页/定位/Decimal/三公式对照；PDF只由PdfReading读取，未走业务层SDK。行unit/scale仍None，样本CNY元数值一致不能推广成所有字段已验证单位。

旧1.2/1.3删掉财务表的反证测试仍能直接读取同一原件、DB SHA不变；财务reuse给named gap且不迁移。因此ROOT最初“版本号升级会阻断所有原件阅读”的假设未成立，没有据此改reader.py或扩权限。正常写入时唯一CatalogStore DDL链负责1.4迁移；此轮不为验收迁移生产库。

ROOT两个干净、已全并线工区已正常移除，不用force；初次删除只因Windows执行位差异拒绝，命令级core.filemode=false后正常删除，主目录模式WIP保持。全局安装因实际OS EACCES未完成且6文件未变；安装器空转已TDD/独审修复并发布FF5396bd6/CI40304350720成功，见[安装状态](INSTALLATION.md)。其余作者工区、配置、原件、无关hook模式WIP和Dayu/IQS/RF均保持。C3摘要语义/cache/RF/new holdout未签收，本节点完成后回到C3，不重跑C1/C2比较。

以下为接收/实施历史，旧IN_PROGRESS由上方当前结果统领。


状态：IN_PROGRESS，2026-10-26。作者CWP `22ab7a41`（产品`43995453`），FF `d396fe7`，两工区干净；ROOT只读接收，不把作者PASS代替当前主线集成通过。卡面与原始证据保留。

## 当前进度与用户分层要求

PDF-C2兼容窄修4c8b4642已发布，精确CI40291031425成功，不再等待。W19仍在ROOT集成，未签收/并线；FF自有短工区`cw-ff19`已接收作者分支但未提交，作者目录不变。

数表服务已改用真实SourceVersionReader引用、canonical writer字节入口、无HTTP的provider协议和统一repository查询；不读取SQL/旁车/暂存路径。PDF既有owner无需重写；在六个AUTO消费者新增针对直接SDK/私有配置绕过的AST回归及允许/禁止片段自测，配合可替换backend、共享预算与真实source/replay的既有行为测试。FF新增独立薄客户端边界测试，不能import HTTP/SQLite/CWP内部实现。测试不是新审批链。

首8项真实RED→GREEN；分层/PDF54项通过、W19+旧writer+分层158项90.70秒通过、FF24项8.52秒通过。之后独审发现A→B→A回退、同秒排序和PIT未来覆盖3个反例，再先RED修在repository：同一catalog中只在内容转换时追加小型版本观察，不复制原件/数值行，重复未变刷新不增观察；schema1.4通过单DDL链兼容1.3并回填已知capture，不捏造旧观察顺序。历史查询仅计当时可知期间，不能保存过去覆盖声明时返回`historical_coverage_unverifiable`/partial，不借后来范围。新27项通过；正常CI已纳入精简公共回归（从同一测试实现引用，未复制oracle），42项34.89秒通过；Linux388源码mypy和Ruff通过。计数有重叠，不能相加成单次总数。

仍待：当前最终代码独审（前一审查agent在完成3反例后capacity失败，由另一独立agent续审）；所有改动完成后一次集中相关回归；官方6项对照、FF真实薄传输→CWP离线三表→直接SourceRef→0HTTP复用/空间/恢复；安装定点同步、主线并线推送/精确CI。没有新外部模型调用或真实下载，原件/生产配置与库不写。C3仍OPEN。

## 隔离与顺序

- ROOT主线`4c8b4642`已发布PDF worker Linux类型窄修；Linux完整379源码mypy通过、独审PASS，精确CI另行观察。原PDF重模型/五页比较不重跑。
- CWP ROOT独占短稀疏工区`company-wiki/cw-w19`，分支`codex/w19-root-integration-20261026`，从`4c8b4642`开始，W19已无冲突暂存合并但未提交。仅该工区实现与测试；作者、生产配置/库/原件不写。初始稀疏检出/index与Windows模式差异已定位，只在自有工区用命令级`core.filemode=false`核对/合并，不改全局配置、不跳过hooks。
- 先CWP数据/公共查询根修与验收，再FF集成/必要薄层修复、安装定点同步及一次跨仓复用；不在当前质量问题未闭合时发布W19主线。不造第二provider、身份库或状态库。

## 已独立发现的共用根因

1. **来源身份没有沿用现有reader DTO。** 手拼SourceRef且`byte_size=None`；作者测试先重新query_ref再读，绕过真实调用缺陷。改为直接使用来源owner给的完整SourceRef，对外返回的引用必须可直接open_version；每源只组装一次，不逐科目重复证明。
2. **两条查询路径的覆盖与版本语义分化。** reuse_only忽略coverage，有记录就complete；PIT仅贴false仍返回未来数据；current_snapshot可能多修订混排。统一既有repository查询/范围覆盖决策，按请求选当前或as-of可知版本，未知范围partial、缺历史时点named gap；reuse_only零网络/零写。不要新加人工门禁。
3. **业务幂等晚于raw持久化，且旧版本引用可变。** 时间戳变化先保存新原件，再把旧版本source重指但保留旧capture。先比较规范业务指纹；未变化复用已有原件/版本，只更新观测；变化保留新快照，旧source/captured_at不可改。规范化失败仍保存可重放原字节。
4. **范围包络复用规则不对称。** from有界/to无界同请求每次1HTTP。将穷尽/请求包络的包含关系集中计算，fetch_if_missing同请求0HTTP；更宽请求按真实覆盖补抓，refresh才明确重查。覆盖不与权限混用。
5. **独立官方财务对照留证不足。** 作者仅2/1/1项且未保留官方SourceRef/SHA。补利润/资产负债/现金流各2项的逐值、币种、单位、期间、合并口径及原定位；优先只读既有原件，确缺时才用既有正规下载工具到独占测试根，结束恢复初态。

## TDD与验收大节点（不加小节点签收）

A. 在隔离工区新增ROOT回归：完整返回引用直接读取；窄/partial采集→宽reuse_only仍partial且0HTTP；真实两个捕获时间/修订的PIT与当前版本隔离；timestamp-only refresh原件数/字节/版本不增长、旧绑定不变；有界from/无界to同请求0HTTP。先保存真实RED和作者证据SHA。

B. 统一查询、覆盖、不可变发布接缝，从根因修复，复用唯一canonical writer与SourceVersionReader。集中运行新回归、W19全97项和迁移/writer旧消费者；完整Linux/Windows源码静态检查。原作者与基线失败如实区分，不改断言换绿。

C. ROOT自建短目录跑FF→CWP→原件/数表→公共查询→直接SourceRef读取→二次0HTTP，增加修订/PIT/覆盖负例；核每表2项官方值、增量空间≤16MiB和重复零增长。请求、字节、时间/费用同一资源对象，保留紧凑收据；测试后恢复不存在，原件/生产配置和库SHA不变。不做完整备份恢复。

最终独审绑定实际新源码及收据，问题闭合后保留作者提交祖先并入主线、正常提交/推送、精确CI与PWF更新。C3正式摘要/cache/RF仍单列；新浪结构化三表不进入叙述切片链。
