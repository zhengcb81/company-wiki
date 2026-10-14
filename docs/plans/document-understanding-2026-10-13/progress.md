## ROOT 冻结发布节点 — 2026-10-14

三 DU3 已全部实收，DEPENDENCIES 补交 282aee36/ef59a574 已纳入暂存、138 PASS，作者树只读不变。SOURCE STOP 已覆盖所有 ROOT 子线；正常发布工程节点，正式默认仍0.8，真实质量尚未达标。

源码因果版本：pipeline1.7、business-policy/5、table-purpose/3、source-script-match/1；唯一经营指标facet1.4同步源record与编译runtime，没有第二registry。简繁只作用于匹配，原文/ID/locator不改；混合表只保留实际经营行与必要上下文。264相关PASS＋新55/20Kcase共56PASS。实测同20K用例38.668→15.95s；2000 facts结果SHA逐项不变，宽正则seed快路是主因，固定配置词4096条/256字符有界缓存为次因，原文不缓存。

正式模型由已冻 scalar reading_model_projection=reading-model-input/1选择一个语义视图；仅missing表示legacy，present-null/未知不能误降级。旧0.8及旧unfinished原指令/输入保持，new generation因果不同，same/cross0POST；真实暂停竞态统一作为paused正常控制处理。相关111PASS、最后恢复16PASS、静态检查通过。保存真实MiMo输入重构136913→52618字节（策略111932→27543），96证据/64组引用和公开全context原样；尚未测新真实tokens或摘要质量，不能按字节降幅宣布质量提高。

ROOT因果＋生产选择42PASS；夹具真实HTML必须显式mime_type，不能用PDF默认或伪造frontend使partial假绿。CLI Python/native fd1诊断归stderr，JSON-only stdout18PASS。新正式离线CWP→FF→RF CLI联调PASS：0.8成为LATEST后精确历史0.9 Ref，完整body/context/spans/summary/sourceRef保持，same/cross0新增POST、两负例0预留，临时目录恢复，0真实供应商调用。

真实源码冻结回放原三25/25；新三9/12（SMIC4/5、ANTA1/3、Apple4/4）。精确漏项是分红计划、品牌组合、周转天数；安踏已保留Amer Sports最大股东与独立上市身份，不得把参股关系和周转天数的支持结果说反。分红属于用户业务阅读范围争议，旧12分母保持。仅Apple原文字面引号按独立验证修订，旧金标与5/12失败保留。第一份真实MiMo摘要仍7完整1部分2漏及4引用不足；母账480782tokens，新增11535µUSD只是预算代理。默认切换与三家真实供应商质量、母G2/G4/G5仍开放。

紧凑证据：[冻结节点与未完成范围](common-root-quality-evidence/finalization.json)、[23份实际测试/独审/回放收据](common-root-quality-evidence/final-receipts.zip)，另[前节点31份证据](common-root-quality-evidence/acceptance.json)保存原失败和第一次真实费用。RF aed581ac精确CI38609253663 success；CWP本节点正常commit/push后核精确CI，不跳hooks、不改他人WIP。

## 当前节点 — 2026-10-14 真实摘要之后

三 DU3 已交付。QUALITY dcde9aae 与 GEOMETRY a8cc604d 的全部改动已收到；DEPENDENCIES ef59a574 的补交 282aee36/ef59a574 已实收暂存，ROOT 138 PASS。它们修复同一依赖文件被重复扣字节预算的问题；完整 cache 仍由正式 AUTO 链验收。ROOT 未修改三个作者工作树。

本节点源码：business-policy/4 具名分部归属 161 PASS；唯一 operating-table-purpose/2 按实际经营行筛选、保留建设期/混合表经营行 286 PASS；其版本已进入决策依赖，因果测试 41 PASS；冻结代默认升级恢复 9 PASS（真实 selector 0.8→0.9 与 PDF parser 0.1.0→0.1.1）。旧升级测试实际未运行 bootstrap 的问题已纠正，不把基线失败直接当可删的断言。全部零真实 POST，独立临时目录与配置/原件约束保持。

真实开发回归原文选择 CN 10/10、HK 7/7、US 8/8；换公司开发泛化 SMIC 3/5、ANTA 0/3、Apple 2/4，共 5/12。它们不是未见 holdout；不修改 gold 或隐藏范围边界来提高分数。HK 实际路由是 hkex/annual，不能凭市场 metadata 猜错路由；简繁 matching、品牌/股东关系及混合经营指标仍需根因整改。两次只读 observer 的后置测试工具故障保留，不能签为真实 window 观测通过。

第一次实际配置 MiMo 摘要已生成、公开回开 verified、96 spans，67004 tokens（输入64804/输出2200），预算代理费用11535µUSD，非发票。母累计480782 tokens/已知345998µUSD＋FX hold2764；剩余1519218 tokens/$19.651238，旧 unknown 仍照账，不重记 reasoning。真实摘要独审为7完整/1部分/2遗漏（关键4/7完整），4 claims 引文范围不足，混合 actual/planned 需修。原文10/10不能替代摘要忠实度。

实际请求暴露 reading_strategy 115003 字节，包含 matcher/UUID/未读诊断等程序信息；模型端应使用一个语义投影，公开完整上下文和来源身份保留。旧/新 prompt/generation 必须因果区分。随后同 run 恢复完成且0新增POST，但第三方 PDF 提示污染 JSON stdout，整体 runner FAIL；修 CLI 操作边界，不能在 harness 剥掉提示或把失败当模型失败。

RF main/origin main 已到 aed581ac（源512e85bb精确CI38563752875 success）；正常push416 PASS＋36子测试。reading_context 消费完整，定点同步两物理安装副本完成；旧 assurance/output WIP 保留。CWP 8f1c607b 与 d240871d 待本节点正常提交/推送，默认仍0.8。

## Next Step

先关闭 CLI JSON stdout 与模型语义投影/引用和阶段覆盖共同根因；并修真实泛化的语言与业务关系准入。集中测试、正常提交推送后，沿同一账本继续配置供应商的真实同资料摘要和独立复审；没有关键漏读再切默认。A in_progress，B工程能力已通过但本次效率/恢复整改 in_progress，C in_progress 未达质量。真实供应商失败、旧金标、缺真实类型均保留；不增加人工签收/小节点门禁。

## 最新 ROOT 节点 — 原生范围、公平覆盖、正式恢复和跨仓消费（2026-10-14）

正式源层新增 native-pdf-range/1：仅从已读取、明确版本的 native page view 取真实子串，原始 unit/span ID 不变；范围保存原文成员/locator/hash，不持久化全页副本。混合语言连接按实际字符边界解释，英文词和数字单位不拼造。reading_plan/3 在同价值层比较真实主题访次，未知标签也记录实际访次；旧 /1、/2 与 legacy 的 4,000 个结果及诊断逐项不变，不增加 96/48K/2M 上限。

源层 142 PASS；畸形范围绑定 4 RED 后 36 PASS，独审 8/8 PASS。连续意义/语言边界 62 PASS，公平覆盖集中 119 PASS、独审 6/6 PASS；ROOT 公有接口/原文回开/缓存/批次恢复集中 **89 PASS / 80.38s**，生产原件、配置与独立 Temp 恢复，0 外部 POST。这些工程结果不代替真实摘要质量。

冻结真实三原件各 parse/select 一次，canonical closed_group_support 验原文闭包：CN **9/10**（SiC 8英寸产品进展仍漏），HK actual mixed **7/7**，US en **7/8**（Azure 所属业务归属仍漏）；此前失败和 gold 字面修正证据保持。正在只读诊断两个共用根因，未花费新模型预算，不能默认切换。

RF 消费者仅新增有界 reading_context 合同，真实 public Bundle 的 claim/versions 没有臆造新字段。独立作者 153 PASS / 2既有SKIP、ROOT 8/8独审；并 main/push **512e85bb**，正常 pre-push 416 PASS＋36 subtests，精确 [CI38563752875](https://github.com/zhengcb81/revenue-forecast/actions/runs/38563752875) success。单文件 LF SHA ca878e4d1b5cfa254ec1db2734596eab36c7d542d49b3b28b5a95097d5cfa10a 已同步 .agents/.codex 两物理副本（.claude 是前者 junction）；check selected/unselected均0。旧三 assurance文件和 output 未动。

完整离线真实 CLI CWP→FF→RF **PASS / 41.293s**：两初次 POST 仅本机假服务，0 外部调用；0.8 成为 LATEST 后 pin 历史 0.9 Ref，消费者四项实际材料逐字精确一致；same/cross-run 均0新增 POST，两负例0 reservation/POST，三个独立 Temp finally 删除。原失败 RF reading_context 收据保留，不删字段凑通过。

## ROOT真实漏读共因与DU3接收 — 2026-10-14（历史节点）

实际form贯通family/strategy/unit scope/decision inventory，新增准入algorithm版本reading-business-policy/2；通用计费、分部变更、业务驱动、合同转化关系只进入0.9。旧0.8 detector与真实TXT指纹不改。相关439PASS/11SKIP、经营295PASS/45.76s；独立7个反例PASS/0.99s，无新增架构/跨parent/旧兼容阻断。源码本轮仍在统一收尾，未将未完成真实质量标绿。

微软同源/SHA/gold且parse/select各一次：当前87spans/47880chars，8业务金标保留7，旧4/8及初新1/8保持。唯一计费候选入选前闭包1span/681chars，被character_budget拒绝；实际136候选、所有87selected仍priority2/section unknown。原HTML无h标签、标准Item编号以paragraph表示且续页重复；不能将TOC的BUSINESS当body标题，也不能先抬cap补此公司。正在修通用编号/续页策略绑定，再判预算根因。

ROOT首joint receipt的字符cap字段误写50000，实际函数默认及真实planner observer均为48000，没有提高上限；原收据保留，correction明确记录。后续脚本从真实常量取cap，不凭手填。

GEOMETRY作者final a8cc604d干净，三个排他提交本地接7e023a15/c6224a1a/ef69957a；ROOT集中89PASS/13SKIP/12.25s。首sandbox TEMP哨兵无法写是环境错误、未进入测试，真实独立TEMP重跑并恢复；失败空目录已不存在。生产配置保持，0supplier/模型/费用。正在接同一个TextPage的真实dict/WORDS和既有find_tables结果，不另开parser、不复制全页到持久层。其余两作者树WIP保持，未提前接最新施工。

正式默认仍0.8；真实模型、跨run缓存与母G2/G4/G5仍开放。已发布工程CI success保持。下一步标准编号共因→同gold回放→统一A/B集中发布→DU3剩余接收/真实C。

## ROOT生产接线工程验收 — 2026-10-14（已发布节点）

实现d3c57b31＋fixture修复fc2a4513已正常推master；正常pre-push4379PASS/17SKIP/381.75s，精确CI38540579403 success（官方REST只读核，gh不可用不冒称未查）。[发布收据](production-wiring-evidence/publication.json)。ROOT继续下一批真实意义/策略绑定根因，不暂停。三外包树已有commits/handoff，但仍有收尾WIP，未修改/提前签最新交付。

已完成显式0.9 request→正式select→实际策略与唯一原文→同事务final CAS→配置model→Bundle/Artifact/public read；v5旧AUTO先只读history再由唯一Store additive升级，旧费用/结果不重签。QA真实roles/记录/parent边界、HK实际family、结构化SEC form不依赖诊断文案、20K有界planner与多行经营表已修。

集中UNIT1149PASS/17SKIP/3历史factory失败保留；旧版本改为静态已冻结generation，受影响51里50PASS/1新测试遗漏显式selector参数，补正确参数后18PASS。旧11E2E全绿；新7节点集中6绿/1计数observer错接，下沉统一byte owner后该case绿，tamper失败/0新POST/旧账不变断言未放宽。最终独立只读review无新A/B阻断，unknown语言重复读P2；Ruff/mypy通过。详[验收/原证据](production-wiring-evidence/acceptance.json)。

真实whole native三市场同原件对照已跑，源SHA/mtime/size保持。US冻结8业务事实仅1/8新保留（旧4/8），是实际family policy没绑定、经营解释准入和机制预算分配共因，不是拆句；新通用RED先在owned recall-root留证，下一批TDD修，默认仍0.8。真实模型/跨run缓存/DU3几何及母G2/G4/G5均未假签完成。

下一步：正常commit/push本批已完成工程代码/PWF，继续root真实业务覆盖共因；三个外包目录零写，旧他人scratch/Dayu/IQS不动。

正常pre-commit捕获一条新负例用了Windows绝对路径字面量；改为独立tmp_path构造同义路径，13受影响断言全绿/2.06s。没有加基线例外或跳hook；本轮工程失败和自动检查修复一起留节点收据。

本地代码已正常commit d3c57b31。首次正常pre-push扩大到202相关文件/3809items，3795PASS/11SKIP/3旧夹具FAIL（407.94s）阻止远端更新。两例无列名SQL INSERT及一例写死迁移版本；同类盘点后改具名列/当前版本范围，保deep一次、COMMIT前、rollback/unknown accounting等断言，受影响30PASS/8.08s与Ruff绿。详[推送修复](production-wiring-evidence/push-repair.json)。正常补充commit/push中，不重复把旧失败称远端CI。

## ROOT当前实施与并行拆分 — 2026-10-14（此前记录）

主线实际开始Phase A：19项新阅读budget反例RED/2旧回放PASS后扩既有planner为reading_plan/1，共享依赖unique成本/主题多样性/完整闭包/字符与工作上限；旧默认和selector0.8.0不改。独审发现嵌套signature工作漏计、闭包实际扫描漏计、签名metadata未限、低预算误诊及依赖中已发value未记主题/签名，均按根因统一修复；最终38/38独立probe通过。尚未把ReadingPlan接正式生产，不标Phase A/B/C全部完成。

受影响首轮87PASS/1sandbox tmp setup error，独立真实Temp88PASS并恢复；追加回归一项短fixture不足旧hint12-token门槛，实际只有8tokens/self-repeat=false，改为17tokens且加complete/min12前置断言，原失败保存，没有改旧算法或降低选择断言。类型检查与ruff通过；最终集中节点结果按随提交证据记录。

三张新DU3卡READY_NOT_STARTED：真实质量benchmark、纯决策依赖manifest、真实版面快照投影，排他目录/独立worktree/DU3/1接口。ROOT继续source_catalog/DU选择和正式AUTO接线；两种fingerprint与几何实际消费缝留给ROOT，不让worker各建权威路由/布局/数据库。只在A/B/C大节点验收；原件/配置保持，0model/provider/network费用。下方历史不作为当前调度。

## ROOT当前收尾推进 — 2026-10-13

用户要求完成共享引擎＋多份文档阅读策略并合入PWF。已将研究、DU/DU2接收和剩余生产工作统一成根task_plan＋completion_implementation；母跨市场与叙述计划只引用这一执行表。

两个独立agent只读核入口、选择断点、缓存因果与现有factory/reuse/outbox/recovery测试。发现并纠正“旧最终HTTP重复全文”推断；明确select决策依赖不同于最终提示指纹，冻结两阶段CAS顺序以避免重复parse/select。

此次是计划合并与施工细则完成，未运行新代码/模型；A待先RED，B/C保持pending，生产默认和真实研究未宣称完工。已完成模块证据仍引用DU2 receipt，不重复验收。以下旧进度为历史。

## 当前执行入口 — 2026-10-13 DU2 接收

[DU2候选模块验收/发布](du2-reception/acceptance.md)：三新包与共享ROOT修复已接收，1135联合离线PASS、四PDF658原文span验真、同源10Q六项PASS；唯一24/14运行catalog、层级策略与有界layout/原文上下文已实际消费。已并 master 并推送 `deb7eb7d`，[精确CI](https://github.com/zhengcb81/company-wiki/actions/runs/38476678472) success；发布收据见du2-reception/evidence/publication.json。生产默认模型尚未切换；粗几何/实际0列保持partial，旧MSFT4/8与B8/B10–11/C12–15、母G2/G4/G5开放。下面旧状态为历史。

## 当前发布状态 — 2026-10-13

旧 DU 三包接收与 ROOT 共同修复已并 master、推送 `9e9907cd7c013ecf0a6787dd0f591ba242eb223a`，[精确 CI](https://github.com/zhengcb81/company-wiki/actions/runs/38462668903) success；[接收结果](reception/acceptance.md) / [下一步](reception/task_plan.md)。首次 push 抓到共享 Windows 同目标 rename 争用，已 TDD 根治并实际1000写入零失败，未跳过测试。新 DU2 三卡仍独立施工，生产模型摘要与真实业务漏读/G2/G4/G5保持开放。下方“发布中”是历史。

## 2026-10-13 旧三 DU 包 ROOT 接收

最新 profile e74b9dcb / structure f8f456a3 / benchmark b891cf74 / ROOT 4b6a8599 全部整合；接收修复分别 7fa6dee2 / ead4aab6，ROOT e9af9ae9 / 1c5784cb / observer 8a5721db。一次联合491 PASS / 四原件11 PASS，追加 seam5 PASS，独立最终审查通过。来源/配置/测试恢复通过，0模型0费用。
修复真正的策略消费、最终预算断链和自证式评测；gold 全保留。微软真实 baseline 4/8 关键业务漏读如实 FAIL，生产与母计划未完成。
新 DU2 三卡用户已分发，独占目录零写。当前发布与精确 CI 记录见 [reception](reception/task_plan.md)，后续统一集成由 ROOT 承担。

# 进度

## 2026-10-14 12:15 UTC — 原件回归结果与范围载体

三份最终实际parse/select各一次，来源SHA/mtime/size保持：HK原单span判定7/7；独立共同oracle改正HTML document定位后US8/8。CN同原件/新gold为2/10，原strict0/10和保守oracle1/10均留历史receipt。96原生碎片仅3339字，核心候选大多已识别但budget_full；下一步不是给样本加boost，而是原生source range进入同一planner。

实施细则已补具名native page view、原始range绑定/回开、历史0.8兼容、唯一carrier字符/槽费用与因果版本，来源/候选/RF/ROOT排他。源view只在内存共享，输出不保存页全文；不存在新的审批/签收/任务库。RF36新DTO TDD绿，旧相关集中验收中，尚未并线。

## 2026-10-14 11:50 UTC — 连续性收尾与真实跨仓缺陷

a117fafc已正常推送；精确CI38554334091 success。连续性作者最终STOP：43正式＋10原独审53 PASS（真实exit0）；ROOT独立重跑原10probe10 PASS/1.93s/SHA一致。旧相关257 PASS/39.06s，记录wrapper编码失败与真实后续exit0，未将前者改签PASS。经营表筛页使用唯一catalog可选bool强信号；小真实PDF经营矩阵及新span原解析器回开2 PASS，0.8保持。因果inventory纳入连续性FEATURE，18 PASS。

同原件cn-h1/hk-annual/us-10k原生最终回放已启动，每份parse/select一次，无模型费用。CN金标已独立确认p18原文无“已于2022”首字，仅明确修正字面quote；旧金标压缩与十事实分母/原FAIL保留。跨块quote oracle独立校验中，不用同页全集提高召回。

C runner真实离线CLI：新旧摘要各1本机POST，CWP Store/public read/same-run/cross-run及FF复用通过；RF新Bundle被旧消费者精确字段集合拒绝，保留原失败材料。RF独立worktree进行完整DTO/引用/投影兼容TDD，ROOT负责接收并线；不触碰RF已存在assurance/runs和output。正式模型仍0调用，默认仍0.8，A/B/C未全部完成。

## 2026-10-13 深化复审

已做三份独立只读审查、三组ROOT纯函数复现和一份独立真实HTML反证。新增 [review](review/README.md) 的报告/矩阵/ROOT细则及三张目录排他的卡；保留原DU/1和四个旧工作树。实现缺陷尚待ROOT按新优先级修复，不把本次文档交付写成生产升级完成。新包准备与发布记录在review/progress。

## 2026-10-13 用户确认共享引擎与策略配置

- 将用户明确同意的架构写入design和当前计划；三张已分发施工卡及DU/1接口继续有效。
- 纠正README、task_plan、implementation中“尚未分发/等待W08”的过时当前指令。W08已完成，三DU包施工中，生产接线与真实G2/G4/G5仍待完成。
- 本次仅更新ROOT共享计划；没有改三个独立工作目录、冻结接口、施工卡或生产代码/配置，0下载、0模型调用、0原件写入。文档变更检查沿用git diff --check，不增加业务测试节点。

## 2026-10-13 并行实施位置

- 用户确认三包已分发；ROOT没有写三个工作目录或独占模块。
- W08剩余RF/Audit已验收并主线，RF精确CI38367459762绿；Audit两个安装副本已6fresh CLI实测。详母W08接收汇总。
- 下一步ROOT主线准备G2真实批次/预算与DU接口整合；等待的是独立交付结果，不创建逐小节点批准。

## 2026-10-13 ROOT

- 按用户要求启动设计调查；读取 PWF/PDF 技能和现有路由。
- 本轮0下载、0外部LLM调用、0原件写入。当前只增加本子计划；生产代码未改。
- 下一步：原件抽样与架构实证。

## 2026-10-13 调查完成

- 20文档原生扫描/重点抽读，4页图像目视；3文档真实parser0.1.1/selector0.8.0回放共21.956秒；恒锋同parse类型/预算对照确认仅调cap不能解决建设期漏选。
- 完成design.md、INTERFACES.md、implementation.md与三独立卡。保留当前存储/来源/Worker/配置模型责任；新增结构和profile，不加权限/签收。
- 原件0复制/改动，LLM0调用；四PNG已删除，原始观察压缩后删除自有JSON副本，摘要与压缩证据留本子计划。
- 当前只写文档/调查脚本；无生产代码、配置和其他仓库改动。尚未分发或启动任何harness。

## 分包准备与发布

- 调查/设计已正常commit `7f6f7cbd5c438ecfd06f6ffb1241442f26ff43b8`，静态hooks通过/无适用代码检查；21文件1068行含两份紧凑压缩证据。
- 三个稀疏worktree已在README路径准备，分别codex/du-profiles-20261013、codex/du-structure-20261013、codex/du-benchmark-20261013，共同base7f6f7cbd，干净；每份约20MiB代码/测试，原件不复制。
- 文件链接/JSON/压缩回读检查通过；母PWF仅14行导航新增，原正文按HEAD字节保留。此轮无需运行完整业务测试套件，已有3份诊断用来验证设计问题，未声称修复。

## Phase A预算组件节点

纯planner104集中PASS/38独立probe PASS，mypy/ruff通过；原RED、环境失败、测试fixture纠正及独审中间失败留证：[小归档](phase-a-budget-evidence/receipts.zip)/[组件收据](phase-a-budget-evidence/acceptance.json)。只签纯planner，生产ReadingPlan/候选/最终模型输入仍待接线；旧默认与原件/配置保持，0付费。

## 2026-10-14 正常发布

实现195aba20与工作树清单36f15dd0已推master，精确CI38522896889 success；正常pre-push3268PASS/11SKIP（204.59秒）。104集中/38独立收据逐字节归档后清本次owned scratch，失败sandbox Temp已无残留。三harness树保留READY_NOT_STARTED，其他历史scratch不动；纯planner不冒称Phase A整体完成。精确发布见phase-a-budget-evidence/publication.json。
# ROOT 正式接线实施 — 2026-10-14

已读选定PWF并核对master4204180a tracked clean；三DU3作者树基线未变化，仅只读查看。ROOT分工互不写外包owned目录：生产选择TDD与结构经营表、正式wire后接planner效率、AUTO Store/factory后接独立生产E2E；ROOT统管源桥/trace producer/发布接线和PWF。

TDD真实失败：生产首轮5FAIL/10PASS；追加sharedcontext字符1PASS；独审脚注/拒绝包/work停止4RED后20PASS；跨原件同文同locator1RED→1PASS；decision inventory3RED→3PASS。新transport首轮7RED/14PASS→30新PASS/246相关PASS；Store16有效RED→143相关PASS。临时SyntaxError、mypy lambda联合类型错误和fake fixture未加新optional字段均留记录后修，不能算业务缺陷已验收。脚注/拒绝包/work停止/父身份为真实代码缺陷已修。

真实原件只读窄页probe：恒锋增发真实project anchor可用；名创p12经营表漏读实证新增计划；没有调用供应商、写原件或生产配置。长文20K负例基线只选2个且late漏读，context1.09MiB；优化后待集中复核。4新正式production loopback端到端PASS/65.91s，same-run恢复和付费后待activation不重复POST；真实供应商与完整decision-cache仍未签收。

根任务继续，不暂停、不标升级完成。下一节点：长文/经营表及新trace界面集中验收→正常commit/push；然后作者组件接收和真实同预算质量/消费者泛化。ROOT scratch均在.planning/shared-reading-production，最后压缩留证并恢复；外包与历史scratch保持。
# 2026-10-14 ROOT — 真实价值准入、预算排序与细几何接线

正常commit `a117fafc` 已完成（48文件，源码/测试与63,593B压缩节点证据）；正常push测试进行中，尚不声称远端已发布。pre-commit host-assumption拦了一个负例夹具的固定C:/路径，改用tmp_path保留“不迁移物理路径”断言，定点1PASS后全部hooks通过。三载体真实CLI跨run缓存强制complete并且0新增reservation/POST，集中143PASS/37.83s；A/H周期用途统一source信号修复195PASS/2.14s。

随后正常push完成：master fc2a4513→a117fafc，prepush4771PASS/24SKIP/410.16s；[精确CI38554334091](https://github.com/zhengcb81/company-wiki/actions/runs/38554334091)于11:10:15UTC仍in_progress，不能提前称success。正式外包三线均已并线推送；下一节点开工解除的是测试冻结窗口，不是材料/权限批准。新native矩阵筛页真PDF反例RED1FAIL（old/new均未扫描），旧0.8不动，0.9接同asset强table信号正在施工。

后续官方GitHub只读API回收该精确head的CI结果为completed/success，见publication收据；不是借其他提交的CI绿色。ROOT另独立只读原件p18核“于2022年推出”存在、“已于2022年推出”不存在，与agent视觉核对一致，下一冻结gold版本须显式修订并重算双算法，不抹旧FAIL。

下一节点：只读CN p13/p18表明8类关键句跨2–4真实native blocks（甚至字断裂），background非first成员没有anchor机会，所有43已承认meaningful fact其实都入选，故不是加预算。有限连续上下文与配置经营表筛页接口已写INTERFACES。独审发现GAN金标多“已”字，原件视觉确无；保留冻结gold与FAIL，不悄改分母/重要性。正式摘要0外部调用，预算母账不变。

金标字面修正已显式执行：[修订收据](gold-literal-revision/receipt.json)与旧字节gzip。cn-h1新gold SHA10d1dc12…a335，只去GAN支持quote开头的“已”；10required/7critical及阶段/数量全部不变，必须两算法用同新版gold重新冻结比较。旧e2602c66…金标、旧0/10 FAIL不改。配置经营表筛页实际小PDF反例从1FAIL→1PASS；新增实际四行table locator回放在修正测试API参数误用后2PASS，真实旧0.8无table、新0.9发现表、原正文定位不变，既有强制目标页回放全部spanIDs验真。

真实摘要执行器的loopback中间FAIL诚实分类：Windows launcher缺main guard、向typed hash接口误传dict、误读不存在的receipt.body_sha256皆为测试执行器构造/接口误用；cross-run复用旧worker工作目录触发正确防覆盖，已纠正prep为每run独立worker-<run-id>（同catalog/AUTO不变），不改生产防覆盖。缺gold已实证0reservation/0POST，最终对照/恢复仍待执行器集中结束，不能把loopback称真实supplier质量。

微软原件/金标未变，reading_plan/2在同48000字符/96span上限取得8/8 required_business、90spans/47999字符（parse2.75s、select6.19s、各一次）。原1/8、7/8、章节接线后2/8中间FAIL原样保留；2/8暴露纯页码/项目符号/空标题及多标签访问总和偏置，已从通用价值准入与同一heap排序修复。当前结果仅原文锚点召回，不是正式摘要语义PASS。

PDF原生前端同一次TextPage取得真实words/cells/fonts，独立36PASS、集中263PASS；真实四原件单页原unit/text/locator/旧EvidenceSpan保持。共享layout_hints1.2.0实际消费fine geometry，集中143PASS（143不是整仓），新模块类型检查绿，旧整包既存26项类型诊断未新增。ROOT新增compact native_frontend coverage，有效RED2FAIL/1PASS→31定点PASS（含28 cache tests），不把细坐标partial误标正文未读，诊断保完整计数及128样本，不持久化细metadata。

真实港股whole-PDF新fine回放仍0/7、96spans/13786字符（parse7.23s、select12.75s），尚未通过。新oracle收紧为实际物理页和同一真实闭包组内AND，未调整金标或原件；定位第12页各层遗漏原因后再继续。A股cn-h1回放进行中。0付费/0下载；摘要与默认切换未验收。

DU3三树最新均干净，QUALITY本地接收四commit至804dfbb7、ROOT217PASS/7SKIP；DEPENDENCIES正常接收六commit至d6e91356，排他owned目录核对，未覆盖外包WIP。PDF/projector因果版本独审有遗漏，作者在补实际used proof与独立projector版本（HTML不受影响），不凭MIME伪造实际使用。
