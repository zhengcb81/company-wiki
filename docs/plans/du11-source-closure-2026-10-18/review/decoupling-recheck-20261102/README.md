> **历史复核快照（2026-11-02）。** 当时列出的六项 OPEN 已在 2026-11-04 按 D4 收口；当前状态与逐项结果见 [D4 closeout](../d4-closeout-20261104/README.md)。下方保留当时只读发现、原因和原始卡输入，不代表当前仍未实施。

# 解耦全面复核（2026-11-02）

**结论：解耦尚未全面完成。** 已完成的公开 reader、FF 连接和原文预算链有效，但存在 **1 项 P1、5 项 P2** 遗漏。上一轮把组件/选择集通过外推为全部业务入口解耦，完成声明过宽。本轮完成核查与计划校正，未实施以下产品修复。

这是既有 D0–D3 的完成度复核，不是新模块施工卡。D4 已整理为五张安全实现卡（当前备妥、尚未派发）；各卡负责本线 RED 测试、修复与独立审查，ROOT保留AUDIT测试归位和最终组合。RF/AUDIT业务计划暂不派发。原 D3 的版本、通过用例与发布记录保留，不把新发现倒写成此前已经验收。D4是已有解耦责任的收尾，不新增人工授权或小节点签收。

## 核查范围和方法

当前主线 CWP、RF、FF、StockWiki、ET、AUDIT 六仓。三独立审查分别负责消费者、采集链、验收/CI；ROOT 检查 CWP 内部分层并汇总。核对真实入口、配置和可达调用链，使用隔离合成样例与实际公开入口验证，不依赖单纯 import 文本扫描或旧 PASS 声明。只跑缺口相关的小探针，不重跑全部测试，不调用收费服务或改原件/生产配置。Dayu/IQS/Dashboard 不在本次实施范围。

核对版本：CWP `a591e489`，RF `ad178dbc`，FF `508aba30`，StockWiki `d8d3303`，ET `003c1c06`，AUDIT `f1ae262e`。与 D3 发布后的当前版本一致；已有 CWP hook 模式及 RF 四项 assurance WIP 保留。

临时证据在 `.planning/decoupling-recheck-20261103/`；该目录后缀是本轮分工时的命名，实际核查日期仍为 2026-11-02 UTC，不代表次日执行。稳定报告在 [consumers](consumers.md)、[acquisition](acquisition.md)、[acceptance](acceptance.md)，版本/探针摘要在 [evidence.json](evidence.json)。这些是一次审计的分工证据，不是三份额外许可。

## 必须关闭的遗漏

| ID | 优先级/责任 | 当前事实与影响 | 缺失的验收 |
|---|---|---|---|
| D4-01 | P1 StockWiki 默认业务接线 | `stockwiki/services/company.py:95,99,153` → `analysis.py:346` / `enrichment.py:200` / `document_signals.py:336` → `sources.py:139,175` 仍直接发现、读取和解析 `doc_root`。12家公司配置指向CWP物理公司目录。新的reader仅opt-in；换目录影响source ID，虚拟湖其他根不会自动出现。 | 用真实run-company/enrich/extract入口，阻止研究层访问原件路径，证明公司级query/list、原文和摘要都经过公开端口。 |
| D4-02 | P2 RF 实际摘要采用 | `scripts/source_narrative_context.py:154,171` 不传reader command；`tools/build_auditable_case.py:71`、`run_narrative_consumption_e2e.py:29`沿用固定默认模块。资料准备可替换，实际采用却不行。 | 同一独立端点从准备一直走到参数/公式/报告；无CWP package/PYTHONPATH。 |
| D4-03 | P2 CWP 内部依赖方向 | `document_normalization/document.py:17`从catalog取纯DTO，触发`source_catalog/__init__.py:16`整个service；shared engine经`observation_adapter.py:25`同样触发。仅import解析层实际载入54个catalog模块。 | 新进程屏蔽catalog runtime后，微型HTML/DOCX normalize和shared engine仍能运行；当前两者均在import失败。未发现因此打开生产DB，不能扩大结论。 |
| D4-04 | P2 CWP 电话会公开协议 | `transcript_import_cli.py:72–92`以`dataclasses.fields(cls)`精确字段集充当wire schema。内部新增默认字段即可让旧FF合法请求失效，无法独立演进。 | 固定字面公共fixture与内部模型解绑定；新增内部可选字段不改变旧wire的接收。 |
| D4-05 | P2 FF 诊断与业务分离 | `ff_process_transport.py:21–24,137–150,288–289`的64KiB stderr上限仍否决结果。合成端点先flush完整成功JSON，再写65,537B诊断，三表client变`upstream_error`。 | 真实子进程已有合法native结果+长诊断仍成功；实际deadline/不完整stdin/坏业务JSON仍准确失败。 |
| D4-06 | P2 AUDIT 测试归属 | `tests/test_du6_current_cwp_bundles.py:16–27,54–78`仍靠缺CWP_SOURCE_REPO skip，引用CWP内部和私有测试夹具。ROOT组合没有AUDIT。 | 将两真实测试归ROOT，AUDIT默认仅便携合同；本次两例实跑2P/3.57s，属覆盖遗漏，非已复现生产功能失败。 |

StockWiki的P1是架构目标主要缺口，不表示已证实数据损坏。路径与source ID的关系只在合成样例复现。旧StockWiki施工卡明确opt-in/default unchanged，不能据此认定原作者未按卡完成；应纠正总控的范围合并。

## 已完成且有效的部分

- RF raw/preparation与StockWiki opt-in raw/narrative reader可替换，无须推倒重做。
- FF六操作确实经统一连接，旧目录知识集中在兼容adapter；未发现当前FF导入CWP实现或直接SQLite访问。
- ET正式tool/worker/provider与CWP无反向依赖；原语言原件获取、CWP入库/字节/身份校验职责方向正确。
- 新浪下载、清洗、专表写入都在CWP；FF只走公开JSON，不跨层抓网页或写库。
- 原D3的39例组合是真实进程链，假HTTP未替换ET worker、CWP importer/verified-open；三个已安装入口及原件只读证据有效。它们没有覆盖本轮全部入口，不能充当全系统证明。
- 原文SHA/来源身份/as-of、真实资源约束、unknown费用是必要事实或资源边界；本轮不把它们机械当成多余权限。

## 需要明确、但不扩成新的阻塞

1. **FF三表stdout容量**：32MiB是未暴露配置口的传输分配，33MiB合成结果被拒；没有证据表明实际新浪三表超限。后续明确response资源owner，不把网络max_bytes直接当本地JSON大小，也不为消除限制允许无限内存。
2. **扩展兼容范围**：raw/narrative接收extensions；local_prepare目前没有该公开约定，精确字段集会拒绝增加extensions。它是协议演进缺口，不是现行producer已输出非法包。当前文档应限定到已覆盖端口；需要扩展时在对应版本集中定义。
3. **Sina provider泛化**：`financial_statements/provider_contracts.py:23–31`仍直接调用Sina normalize，service/replay认Sina原始格式。当前单Sina需求可用，不能宣称任意provider可替换；将来第二provider由adapter拥有decode/replay，不强加无价值provider。
4. **组合CI触发**：仅integration/runner/workflow路径自动触发，公开接口源码改动依赖ROOT手工大节点组合。原计划允许这种方式，本轮不虚报当前D3未跑。可加窄公共接口路径触发，不能变成每commit全仓多仓跑；未配置remote的Stock/AUDIT不伪造远端覆盖。

## 之前为什么没发现

主要根因是验收矩阵从“已改模块”出发，而未从“每个真实用户入口”反向追到存储/解析owner。静态无跨仓import漏掉物理目录耦合；prepare成功漏掉consume；patch整个reader与同名package stub隐藏端点漏传。StockWiki110项只覆盖四个reader/process/CLI套件，AUDIT43项只覆盖两个代表文件，均不等于整个仓库独立。三项应改进验收设计，不增加人工审批或再跑更多无关用例。

## D4 集中收尾顺序与接口细则

已将五条实现责任拆为[互斥写域施工卡](harness_lanes/D4_PACKAGES.md)。D4-01让同一线负责CWP公司来源清单和StockWiki消费者，避免跨线争论来源接口；D4-02/03/04/05分别独占RF摘要采用、CWP解析纯层、CWP电话会wire、FF子进程诊断目录。AUDIT测试迁移和最终组合不安全外包，归[ROOT收尾任务](harness_lanes/ROOT-D4-final-integration.md)。目前仅备卡，未派发。每卡均要求独立review agent先审、问题全部修后方可交接。

### A. 各实现线冻结本线行为，先见失败；ROOT只冻结组合边界

各卡按自己的交接边界先写RED测试并固定真实入口→port→owner→测试映射；D4-06再由ROOT组织跨线组合。直接保留本轮反例为测试素材，先补未覆盖行为，不用词面扫描代行为测试。

Stock公司来源需求使用已有CWP公开query/export与ref发现能力，补齐所需的分页/期间/文种/质量表达；结果为逻辑source ID、版本、locator和提取状态，不能给研究域物理目录。先确认已有接口能否满足，不能另造第二catalog数据库。

### B. 按责任层修复，保兼容

1. **RF**：transport/orchestration取得已验证immutable context；纯消费只将它绑定到claim/parameter/formula。兼容consume入口可转发同一个reader配置，两公开工具同步。不得上层重复拼CWP命令，不因记录完整而重新读取/POST。
2. **StockWiki**：正常业务接入公司级来源适配器，复用已有raw/narrative reader。研究层不再自行遍历/解析CWP原件；保留Stock自己的研究状态。旧doc_root如保留，只作为明确上游登记/导入适配输入；保留旧证据ID引用映射，不迁删真实资料。跨两物理根、根迁移、同路径新版本、撤销/缺失状态均有测试。
3. **CWP纯层**：将DocumentStructure/NarrativeUnit等纯DTO及通用turn结构放到中性合同/结构owner；旧catalog路径重导出同一类对象，保证isinstance和序列化兼容。catalog门面按需导出，不能只是lazy掩盖错误依赖归属；不大搬整个catalog、不加共享SDK。解析/理解仍由CWP负责。
4. **CWP wire**：定义明确的versioned import字段和默认值，再映射到SourceRequest/DownloadCandidate。内部字段变更不改变wire；不可因此静默接受错误source/hash/核心版本。保留现有FF字面fixture，不随内部model自动重生成。
5. **FF诊断**：shared transport把native payload和可选日志分开。对日志限留/排空/流式记录应可观察，不据固定日志大小把已有成功变失败；仍执行真实时间/进程树/输入完整性/有效业务JSON约束。实际stdout容量属于显式transport资源，不与原文或provider网络预算重复记账。
6. **AUDIT**：将两真producer测试及断言迁入ROOT受控节点，新增显式audit-root；默认AUDIT用portable v2/v3与fake port。在无remote时ROOT本地组合必须声明参与，远端如未参与就如实标范围。不能以skip把它算通过。

### C. 一个集中验收节点

- 各owner只跑新增失败/相邻测试，变更后再跑受影响域；不反复跑已通过的整仓。
- ROOT离线组合从正常公司入口贯穿query→read/summary→RF实际采用→AUDIT导入；用新临时根和独立端点，消费者进程看不到CWP实现/原件路径。保原件SHA、身份和真实资源反控；含正常结果+诊断故障。
- 底层解析/理解独立新进程测试屏蔽catalog runtime，验证真实小文档行为；不是仅断言import字符串不在文件中。
- 未实施代码的agent集中审完整度和质量，发现问题同owner修复，仅复验新增影响。全部满足后正常提交/推送/必要定点部署，修正当前状态；不是每helper审批。
- 本次隔离合成测试不能替代后续真实摘要/缓存/RF研究采用。D4关闭后再回T4/SEM与原真实业务顺序，固定公司loop责任不丢。

## 本轮操作与边界

产品修改0，生产原件/配置/库修改0，模型/外部provider调用0；合成测试临时根已删除，精简报告/探针证据保留。不存在因测试通过而删除原历史失败、删原件或清理外来WIP。部分CodeGraph索引缺失/滞后已用定位后的当前文件核对；未把空caller当无调用。只读Git与AUDIT测试遇沙箱权限限制时使用同一获准宿主操作，未改ACL。调查中的文件名/夹具定位错误已更正，不记为产品缺陷。
