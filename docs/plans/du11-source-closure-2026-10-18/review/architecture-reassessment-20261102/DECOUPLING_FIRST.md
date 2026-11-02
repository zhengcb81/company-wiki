# 先完成解耦，再按模块派发（2026-11-02）

用户最新决定：不在半解耦状态下推进外包。**本文件取代上一轮“RF/AUDIT可立即离线开工”的调度建议。** 两仓PWF保留为待激活的业务清单，暂不派发、不实施其中业务整改。ROOT集中负责跨仓解耦，内部只读调查与独立质量审查可以并行，不等于提前启动模块施工。

状态：D0–D3工程已完成。39项当前组合零跳过、三技能入口部署实测、真实原文只读与[最终独审](../decoupling-20261102/independent/review.md)通过。发布与CI以[实际记录](../decoupling-20261102/release.md)为准。下列D0–D3是原验收定义，当前唯一状态仍在 ../../CURRENT_STATUS.md/json；没有提前派发或另建目标。

## 完成的含义

解耦允许模块依赖**公开、版本化、可替换的接口**；不允许依赖对方私有目录、内部数据库、内部类型/算法和默认邻仓checkout。接口的调用不等于耦合缺陷。验收后应能各仓独立修改内部实现、独立测试、独立交付，ROOT只在组合节点验证接口和实际业务链。

不追求“模块互相不通信”，不引入微服务、共享可变数据库、第二预算库或新的庞大共享SDK。公共协议的必要身份/字节/质量语义继续；人工许可、可伪造authorization JSON与每helper签收不增加。

## D0：当前依赖与责任清单（已调查，代码未改）

| 表面 | 当前证据 | 责任与改造 |
|---|---|---|
| Raw reader部署 | RF company_wiki_source_reader_v2.py硬写CWP模块命令；其narrative reader已有可注入command；Stock raw/narrative已有argv_prefix | 配置/进程适配层统一提供公开端点，领域层只接收port。Stock已有能力复用，不能为形式统一重写 |
| FF部署 | ff_configuration检查CWP config/source_catalog.yaml；多个transport分别拼CWP命令/cwd | CWP自己验证内部配置；FF只验证连接配置，命令/配置定位收敛到adapter。默认行为兼容，不让公司业务逻辑知道目录布局 |
| Wire形状 | 多仓exact字段集与enum/内部reading树 | 列出实际业务必需字段和仅诊断扩展。稳定核心＋明确扩展区；消费者只依赖必需语义。未知核心版本/状态诚实unsupported，不能一律忽略未知字段或质量状态 |
| 采集预算 | ET/FF已传实际额度，CWP transcript import仍硬卡16MiB/25MiB；official二次顶帽；本地输入表示帽 | operation预算由请求/配置确定，按公开协议传递；各层计自己的实际资源，数据codec不增加业务许可 |
| 本仓测试 | RF isolated_lake.py构造CWP policy/prompt-review并直接写artifacts；CI还检出邻仓和注入CWP PYTHONPATH | RF本仓用独立portable export/fake port；真实湖/DB夹具由CWP或ROOT集成测试owner维护，须通过公开入口生成，不在RF复制SQL |
| 观察与业务 | 当前已有native/diagnostic分离修复 | 用跨接口反控保成功结果、unknown费用和质量状态；不新建第二执行结果真相源 |

精确位置和原始反例见boundaries.md、rectification.md及新增decoupling-ports.md/decoupling-acceptance.md。历史legacy直接import如果生产不可达，不冒充当前主链；仍须明确兼容路径并从本仓默认测试依赖中隔离。

## D1：先写接口行为与隔离测试（已执行）

先补当前违反边界的测试并记录RED，再改生产代码。代码更改全部由ROOT集中调度，不能将此阶段拆成各harness同时自行演进接口。

1. **公开端点替换**：同一SourceRef请求，端点分别指向fake命令与真实CWP CLI；替换安装路径、cwd、端口实现后，消费者领域结果保持一致。领域层不拼CWP内部配置文件，不导入CWP实现。
2. **独立安装/测试**：RF/FF/Stock/AUDIT/ET各自测试环境仅含本仓和声明的普通依赖，无CWP checkout/PYTHONPATH/生产库。明确分出跨仓integration job；不skip/delete已有断言来变绿。CWP本仓不依赖消费者实现。
3. **协议兼容**：对每个实际公共端口给当前/上一支持版本和真实错误fixture；等价JSON空白、可选diagnostic增加不影响核心结果；缺必需字段、错source/hash/身份/单位、未知核心语义仍准确报错。引用/support/context必须有语义定义，不只JSON能解析。
4. **完整预算链**：22MiB原文额度允许17MiB合法FMP原始JSON，经FF→ET真实CLI/supervisor+fakeHTTP→CWP import/writer→公开verified-open，原始JSON字节/SHA不变。TXT为提取结果。第二次复用0下载；真正超额、错身份/原文hash、deadline与子进程清理反控。
5. **账户语义明确**：下载实际网络字节记一次；下载后剩余网络余额不等于同一原件的入库上限。入库按该文件的原文额度校验，本地读取不能重复扣provider网络/费用。时间用真实剩余deadline，编码pipe资源可从原文预算推导。未知费用不猜0、不自动重POST。
6. **观察可替换**：正常结果加可选观察故障仍返回native结果并标观察不完整；source/paid pin真实冲突不能被诊断降级掩盖；源可读不等于研究已经通过。

这些是普通工程验收，不是新增运行许可。测试命令和fixture路径在D1依据当前实际入口落定，不用占位命令冒已运行；跨仓私有依赖清单必须覆盖生产入口、CLI、测试、CI、技能部署入口。

## D2：集中实施顺序

### D2.1 连接适配与职责收敛

沿现有reader_command/argv_prefix模式，让各消费者的连接配置统一落在本仓adapter；保原默认CLI模式和已配置路径。业务代码只使用逻辑请求/DTO。不强制新增网络服务或共享代码仓，不复制CWP config/schema算法到消费层。

迁移时枚举RF raw/narrative、FF filing/transcript/financial/local prepare、Stock来源预览和AUDIT实际执行入口。旧部署配置能继续用，必要变化提供明确迁移和测试。没有实际耦合的ET/invest不为凑改动而重写。

### D2.2 公共契约与资源

生产者拥有公共字段语义和便携示例；每个消费者一个适配owner，不在业务流程多次重解同一DTO。收敛表示帽/重复预算帽，完整保留原文、locator、support/context与uncertainty。可选诊断扩展与核心错误分开；接口变化需要producer/consumer同测，不靠修改全部golden把不兼容藏掉。

传输接收方复核实收字节是合法边界，不机械删SHA。实际请求额度来自用户配置/任务，不让provider自报放大。旧请求省略额度时采用公开默认；明确更大请求不能被隐藏常量压回。official与local codec按同一个责任原则处理。

### D2.3 测试和CI归位

把消费者普通测试改为只依赖公开协议与本地fake端点。CWP内部DB/生产策略夹具只留在CWP owner；ROOT跨仓集成通过公开fixture/CLI组装临时湖。不引入供生产使用的任意SQL后门。

迁移前后列出被搬迁测试与原断言一对一去向；测试职责不丢，旧的完整链仍在ROOT集成执行。CI分成本仓检查与明确跨仓集成；提交不默认跑多仓全量，接口变更与大节点跑完整相关组合。不能用环境缺依赖自动skip证明独立。

### D2.4 部署与替换

配置中的安装命令/路径只供adapter；用临时安装目录、不同cwd和新进程证明可替换。只经已有定点安装器部署完成的变更，保配置/output/原件。没有remote的仓如实本地提交，不创建未经要求的公开remote。外来WIP保留，暂不让业务harness进入同仓。

## D3：一次集中架构验收，通过才派发

| 标准 | 可观察证据 | 不算通过的替代物 |
|---|---|---|
| 无私有跨仓依赖 | 当前入口依赖清单及静态边界检查；本仓隔离进程测试 | 只grep没有import、只画分层图 |
| 可独立测试 | 各仓在无邻仓源码/DB环境的实际测试结果 | 因缺依赖skip、默认偷偷读全局技能副本 |
| 端点可替换 | 同一请求fake/真实CLI、不同安装根/cwd的结果一致 | 单纯新增一个没被调用的interface类 |
| 协议可演进 | 支持版本/可选诊断/坏核心数据正反例，producer与consumer共同fixture | 所有unknown一律接收，或每增diagnostic就全仓同步改 |
| 完整链预算与复用 | 上述大原件链走到verified-open；真实超额拒、复用0下载、计量不重复 | 只到ET worker成功或只mock import返回 |
| 数据与语义保全 | 既有真实来源只读经公开端口访问，source/hash/locator/质量状态保持；隔离根恢复 | 复制生产库、改原件、拿语义未验当已验 |

ROOT先完成有界组合测试并记录参与版本，再由未实施代码的独立agent一次集中审查代码边界、本仓隔离测试和实际组合结果；发现问题同owner修复、只补受影响增量复验，随后正常提交/推送/必要定点部署。不另加测试设计预签收，不让最终组合结果落在独审之外。记录一次参与的commit、各仓测试、集成结果和残余风险即可，不再复制多份巨型收据。

**D3通过之前，RF/AUDIT业务计划状态始终为DEFERRED_UNTIL_DECOUPLING，不能因为本仓任务看似独立就提前派发。** D3通过后才按真实接口重新校准各仓PWF并标READY；这由工程事实驱动，不另等用户逐项授权。

## 解耦后恢复的原任务

T4父链、SEM-QUAL-01、RF ghost/期间补集、AUDIT attempt/检测、真实摘要/恢复/RF采用、固定公司loop全部保留。它们不应全被塞入“架构解耦完成”的定义，避免前置无限膨胀；但解耦测试不能把已知语义缺口签成解决。

后续ROOT保跨仓接口/集成/发布与真实公司循环，各仓各一writer、自己的PWF/单元集成测试/交付前独审。通过解耦后的字段/端口定义重新发施工包，上一版卡不直接激活。Dayu、IQS、Dashboard继续不动。
