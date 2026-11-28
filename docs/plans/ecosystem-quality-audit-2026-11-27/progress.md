# Progress Log — 全 12 模块深度审查与综合整改规划

**当前节点**　11 张止血修复已并线。FF T3 离线组合通过，正式绑定待复核。P1-00 已独审发布，FF、ET、SID、RF、MC、IR 已推实际发布线，Audit 和 StockWiki 通过独审及原生 Windows 后快进本地。CWP、Dashboard、IQS、StockQA 的运行源码已通过同版全量、独审及相关组合后并线。StockQA 的历史委托测试已通过精确双平台并推主线。StockWiki 的 Ubuntu 全量已通过，Windows 还需收口真实进程树夹具。继续逐仓收集、实跑、独审及并线。W12 业务循环仍在原检查点。

## 2026-11-27 22:54 UTC — P0-01 至 P0-11 分批派工

用户要求总控直接派 agent 执行 11 张止血卡。会话同时可运行 3 个子 agent，各卡使用独立 agent，空出席位后即派下一张。11 张卡已全部启动，使用 `C:/Temp/s6a/` 下的独立候选工区。当前记录按候选独审和发布进度更新。原 `C:/Temp/s6/` 工区及作者未提交内容仍作为只读参考。若原作者先交付，从同一发布目标核对两套候选并接受一套，保留已有测试与独审。

| 卡 | 新候选工区 | 候选 SHA / 当前状态 | 实施者的定向证据 |
|---|---|---|---|
| P0-01 | `C:/Temp/s6a/audit` | `c41db5ddc78506b3f665983fdae715626ff04581`，独审通过，本地 `main` 已快进（无远端） | 原 CLI 复现 `NameError`；Windows 6 项通过，审计三类回执从新进程查读，同一动作各执行一次 |
| P0-02 | `C:/Temp/s6a/et` | `2f7e03db01c9aed817811e07b7e83acddeac4ba0`，远端 `main` 已核对，[CI 通过](https://github.com/zhengcb81/earnings-transcripts/actions/runs/46082021743) | Windows 37 项定向通过，另在实际 console-subsystem Python 验证无新控制台及进程树回收 |
| P0-03 | `C:/Temp/s6a/ir` | `5edb9fb561f077d828af00b921dfbdc0926eb412`，远端 `main` 已核对，私有 CI 待查 | Windows 104 项及 11 个子测试通过；最终再验 3 项，覆盖依据渲染、模型透传、裸输出路径和独立安装 |
| P0-04 | `C:/Temp/s6a/stockwiki` | `6c75adf45c1ed76735d64f561268e951cb92c862`，独审通过，本地 `master` 已快进（无远端） | Windows 8 项定向通过，邻近回归 208 项通过，覆盖 SQLite 特殊路径、回滚和 HTTP 请求框架 |
| P0-05 | `C:/Temp/s6a/iqs` | `b4aee7fb05671b162ef7f6d8e270ef3cb2692e52`，远端 `master` 已核对，[CI 通过](https://github.com/zhengcb81/invest-quick-scan/actions/runs/46082564988) | 邻近定向 136 项通过，最终 55 项通过；实测锁竞争、冷读、并发成功不可覆盖和无窗启动 |
| P0-06 | `C:/Temp/s6a/cwp` | 远端 `master@d1987560eafe97e71753cf3e5d7e6712d661bbdd`，[CI 通过](https://github.com/zhengcb81/company-wiki/actions/runs/46083438812) | Windows 定向与独审通过。实测判定已发布的原件后再停进程，部分写入继续；合并版推送钩子 23 项通过 |
| P0-07 | `C:/Temp/s6a/ff` | watchdog `035d415b81268d1192721cfdc7b743238f674d32` 已入远端 `main`，[CI 通过](https://github.com/zhengcb81/filing-fetch/actions/runs/46083923728)。T3 `82c749464b494cf8dc9ec9e694c433adb02717e5` 也已入远端 `main` | watchdog 28 项通过，已有输出不触发新的尺寸拒绝。T3 最终 18 项与跨仓四案通过；正式绑定待验 |
| P0-08 | `C:/Temp/s6a/sid` | `8bc6e93b55142e0eff464c14adc08ebc93fb59c3`，远端 `v2-clean-rewrite` 已核对，[CI 通过](https://github.com/zhengcb81/StockInfoDownloader/actions/runs/46082044981) | Windows 102 项定向通过，实测 HTTP 截断、原 PDF 保留及占用后原子替换 |
| P0-09 | `C:/Temp/s6a/rf` | `5a28c0c88df1a8e8fb9b167dbd884eebef7d7894`，远端 `main` 已核对，[CI 通过](https://github.com/zhengcb81/revenue-forecast/actions/runs/46082671176) | Windows 170 项和 13 个子用例通过。另有 1 项既有跳过、1 项在基线也失败的历史 review 断言，交 Phase 1 更新 |
| P0-10 | `C:/Temp/s6a/mc` | `c0ec9c168d8f2c038405ab0c6cbab0438ff5ad87`，远端 `master` 已核对，[CI 通过](https://github.com/zhengcb81/MeetingConverter/actions/runs/46082052941) | Windows 137 项定向通过，真实 CLI 和 ffprobe 验证坏配置、坏音频及正常音频，新增供应商请求为零 |
| P0-11 | `C:/Temp/s6a/dash` | `de62760090c6380914b5c30c4726afe85c5234d7`，远端 `main` 已核对，私有 CI 待查 | Windows 7 项启动测试通过；邻近 55 项通过，另 1 项 M8 过期断言在 `666e2426` 同现。保留已有 RF 配置和 48766 运行 |
| P1-00 | `C:/Temp/s6a/spec` | 候选 `b11d45f457a60203bbc7ecb6e598704e4904013b` 已独审；同一工具文件发布于 CWP `7320c52a2a6daf2d424c35216fa6ed3cad88f063` | 25 项通过，实际 pytest 验证子集选择、收窄配置、合法输出选项、缺失项和合法包导入。CWP P1-01、ET P1-03、RF P1-05 已按正式基线开工；各自旧测试差异按根因处理 |

RF 的一次隔离测试把过长请求放在 Windows 命令行，启动失败后 pytest 把继承变量带进本地工具输出。现已将请求改由 stdin 传入，并在启动测试进程前白名单化测试环境。后续施工沿用环境隔离，保留 Windows 和临时夹具所必需的变量。凭据值不抄录到计划或受版本控制的证据中。

## 2026-11-28　T3 组合与 Phase 1 首批

- **P0-07 组合证据**　用真实 FF 和 CWP 进程、CN/HK/US 本地采集替身和一个损坏原件执行四案，四案通过。三个市场各 discover/fetch 一次，损坏原件零采集。同一 run 冷读与再执行的回执相同，新调用为零。CWP 提供方已发布 `1a62edf1d0d89567a5a552709d7027880ea3b857`。第一轮复验发现 FF 短请求将探针诊断落入默认目录。已用 `--jobs-dir` 接入原 DirectRun 回执及 outbox，FF 候选 `82c749464b494cf8dc9ec9e694c433adb02717e5` 经独审，18 项回归通过。固化脚本的最终组合四案再次通过，安装根 `.ff_jobs` 零残留，临时目录已回收。复跑用 [replay_t3_composition.py](review/replay_t3_composition.py)。
- **P1-01 CWP**　`C:/Temp/s6a/cwp-p1` 从发布工具版开始。Windows 31 项定向通过；全目录收集涉及历史外部依赖，在处理真实收集和运行清单。保持开发者快测。
- **P1-03 ET**　`C:/Temp/s6a/et-p1` 真实 Windows 收集 831 项，旧 CI 从未覆盖的退出及回告断言已逐一追踪。完整单跑超过 610 秒，按适用平台分片并核对执行并集。旧退出码、原作业、输出协议和本地脱敏留痕保留。Windows 收集 833 项，分为 251/297/285，六项 F4 回归通过。候选 `93c522e68917c8540138585a47200cba5d369333` 修正 GitHub 的 job/step 环境与同 SHA 采证。已推送 [ET 草案 PR](https://github.com/zhengcb81/earnings-transcripts/pull/1) 等真实双平台组合验收。
- **P1-04 SID**　`C:/Temp/s6a/sid-p1` 已按正式 `8bc6e93b` 开工，补齐真实离线测试发现以及 Windows 原生执行。
- **P1-05 RF**　`C:/Temp/s6a/rf-p1` 定向 82 项通过。移除过时的缺 review 拒绝期待，保留实际 SHA 错拒绝；查清被旧硬编码测试列表遗漏的四个收集故障，正在核对完整离线执行。

## 2026-11-28　Phase 1 首次 CI 反馈

- **CWP ↔ FF T3**　[FF 正式 CI](https://github.com/zhengcb81/filing-fetch/actions/runs/46086264095) 通过，实际 CWP 配置用四份隔离夹具完成 `open/close`，采集派发为零且临时目录清空。CWP 首次 [精确 CI](https://github.com/zhengcb81/company-wiki/actions/runs/46085744052) 的架构测试暴露按字符串动态导入。候选 `ac9ba2b3d176ddb7fe01c5a41c24d5b1bd3b6288` 只用显式 CWP 公开入口，保留原测试红转绿。独立 Windows 复验两项通过，已保留在途的暂存与未暂存差异并快进、推送 `master`。 [修复版精确 CI](https://github.com/zhengcb81/company-wiki/actions/runs/46088694086) 通过。原 FF 版本组合再跑四案均通过，冷读后重复同作业回执一致、三市场派发计数无增量。正式绑定保持独立待证。
- **P1-03 ET**　[首次双平台 CI](https://github.com/zhengcb81/earnings-transcripts/actions/runs/46086664981) 识别三类实际问题。Windows 原文比较改用文件身份，Linux 不解析 Windows 原生绑定，强停后以原作业的持久事件区分已知中断和尚未确认，费用保持 `unknown`。Windows 上六项针对用例通过，Ruff 与双平台 mypy 通过。`b0d8394ea0983d0c0c6ebc39d5be1da0151c3ffb` 已推到原草案，[六个执行分片与覆盖归集](https://github.com/zhengcb81/earnings-transcripts/actions/runs/46088338831) 全绿，独审核实所有原作业与零重发断言后已快进 `main`；[主线同版 CI](https://github.com/zhengcb81/earnings-transcripts/actions/runs/46089171631) 也通过。ET 用 CI 直接运行 `quality/source_checks.py` 达到本仓架构基线检查，后续保持这一个检查入口。
- **P1-02 FF**　从已发布 `82c749464b494cf8dc9ec9e694c433adb02717e5` 创建 `C:/Temp/s6a/ff-p1` 开工，Windows 收集基线 1,885 个节点。只在该工区改工程检查和隔离测试。主工区的财报报表施工归原 owner。
- **P1-04 SID**　把实际旧提交的 HTTP 断流和原件替换缺陷作为红证据。Windows 首次完整运行还找出请求夹具身份歧义、安全作业号的旧断言和参考工具自测的进程污染，正在消除根因。候选 `7c34f34c4be4c76f2363097b9be58ab84a3089db` 保留作定位依据，待接受版本另记。
- **P1-05 RF**　旧 CI 漏跑的身份夹具和原子写用例已按公开契约修正。候选 `fed82030b640be3633ea683f0e21377d17806677` 的 87 项 Windows 针对复验通过，完整 Windows 执行进行中。日常 12 项快测继续保留。

## 2026-11-28　共同根因与新候选

- **P1-00 公用路径归一**　[SID 首次双平台 CI](https://github.com/zhengcb81/StockInfoDownloader/actions/runs/46088974903) Ubuntu 通过，Windows 543 个 SID 用例通过及 11 个真正联网用例被隔离。参考工具把 Windows 短路径与长路径视为不同目录，误拒两项参考自测。已在公用实现统一规范化两侧路径，保留越界拒绝及原收集对照。两项复现红转绿，Windows 自测 26 项加 7 子项通过，独审通过。新参考候选 `66dc8881bc441c89918c8c306457572160d3e772`，树 `33ca2b5d7c77786416e5d436f589948785fb494b`。SID [草案](https://github.com/zhengcb81/StockInfoDownloader/pull/1) 的精确候选 `31fbefc6e75ad2f6cd80c255c19e3fcba5421432` 用同一份修复重验。其余采用者在各自候选冻结前核对同树。
- **P1-02 发现的 CWP 旧资料期次缺口**　干净目录和独立 `ac9ba2b3d` 证实，带可信标题与披露日期但缺结构化财年的旧 HK sidecar 被来源查询 `found`，路径无关候选却返回 `fiscal_year=null`。明确期次的对照返回 2024。FF 保留真实不符拒绝。总控追踪到本地匹配走标题年、公开清单只投影显式期次的语义分叉，后续由 CWP owner 先统一期次证据，不从查询输入补写，也不做公司特判。
- **P1-06 Audit**　隔离工作树 `C:/Temp/s6a/audit-p1`，候选 `17728e785c5dd0865c102985ac16f8f52c4034ff`，同一参考树。Windows 无默认 HOME 的旧收集在导入时失败，红测定位到显式安装也读取默认目录，现只在选择默认目的地时解析 HOME。强停池状态复验入测试发现，三类 F4 回告、显式安装和架构回归 15 项通过。Ruff、Python 3.12 工具 mypy 通过，完整 Windows 收集及运行在本仓执行，无远端发布。

## 2026-11-28　Phase 1 发布与托管验收

| 卡 | 正式状态 | 证据或待办 |
|---|---|---|
| P1-01 CWP | [草案 #2](https://github.com/zhengcb81/company-wiki/pull/2) | 初次汇总在 Windows 完整 Git 检出阶段遇到历史文件超过 260 字符。Linux 收集通过。Windows 本机收集 16,760 项，16,628 项适用，其余 132 项逐项有原因。正式组合测试另暴露采集替身未声明证券身份。按实际日志修托管环境和夹具后再复验。 |
| P1-02 FF | [草案 #1](https://github.com/zhengcb81/filing-fetch/pull/1) | 52 项及 7 子项、5 个采集用例、10 个电话会用例通过。首轮全 CI 暴露 Windows 缺 IANA 依赖、旧测试依赖路径拼写与生产布局，逐项由 FF 负责。 |
| P1-03 ET | 主线已发布 | `b0d8394ea0983d0c0c6ebc39d5be1da0151c3ffb`，双平台及原作业冷读独审通过。 |
| P1-04 SID | 实际发布线已发布 | `v2-clean-rewrite@9c25b42f27027a88ee2c67fe95887fbff1876e10` [双平台主线 CI](https://github.com/zhengcb81/StockInfoDownloader/actions/runs/46092801247) 全绿。统一微秒、毫秒粒度的旧预算夹具到可控时钟，三个过期时序用例无需等实钟，断流与原件保护仍用真实 HTTP 和文件系统。 |
| P1-05 RF | [草案 #1](https://github.com/zhengcb81/revenue-forecast/pull/1) | 首轮 [完整双平台 CI](https://github.com/zhengcb81/revenue-forecast/actions/runs/46091629871) Linux 27 红、Windows 28 红，各实际运行约 4,000 项。逐项归因，最快 12 项日常验证已经保留。 |
| P1-06 Audit | 本仓隔离整改 | 861 项原生 Windows 收集已证。完整串行超时且没有执行凭据。独审要求逐片实时保留结果，并补齐完整审查链、旧技能文件漂移和机器输出检查。在真实回放中另发现 finding 可用篡改过的部分字段重放，owner 正在修复。 |
| P1-07 StockWiki | 本仓隔离整改 | `d8eca90a307ef425ccb64e913204ac8b1de30d70` 收集 2,389 项，冻结的 CWP/IQS 组合 32 项通过。原生全量和 C06 独立执行仍待回执。 |
| P1-08 至 P1-12 | 按 owner 顺序接续 | 已独立核对 IQS 正式远端基线。保留正在运行的用户工区。 |

总控通过 CWP 隔离源工区复现正式查询和下载前复用的两条期次分叉。独审证实标题中的刊载日期会被旧复用解析错当财年。同步用可信披露标题统一两条入口，日期和跨年范围保持未知，可疑本地文件保留补证线索。已为旧读取指纹、旧原文 SHA 及错期复用加红绿回归。该项仍在独立接线验收，暂不记发布。

## 2026-11-28　Phase 1 执行与并线接续

- **FF P1-02**　首轮绿灯后独审发现目录锁用例借助拦截器构造 busy 结果。改为独立进程持有 CWP 实际 `SourceCatalog.operation_lock`，验证扫描得到可重试的 `catalog_locked`、原文 SHA 不变且 FF 复用零下载，释放后真实扫描成功。Windows 用例 17.17 秒通过。[精确候选 `85945fee` 的七项双平台作业](https://github.com/zhengcb81/filing-fetch/actions/runs/46095840063) 全绿，已使用常规 pre-push 的 11 项快测推入远端 `main`。[发布线同版回执](https://github.com/zhengcb81/filing-fetch/actions/runs/46096589886) 也已通过。公开 `open` 回包丢失时，原 FF CLI 实证会留下隔离 CWP 目录。已由 FF 在同一 run＋case 触发 CWP 公开幂等清理，受影响 19 项通过，独审验证清理同时失败时两个异常仍可冷读，同号返回原收据、四案零派发。`c72c3a12995dec3b5acd462d805ab344f35f2712` 已快进正式 `main`，[正式双平台及聚合](https://github.com/zhengcb81/filing-fetch/actions/runs/46105280791) 均通过。最终两仓脚本离线四案再次通过，每个市场一次下载替身，坏原件零，清理及同号冷读通过。已通过 FF 的公开连接用真实 CWP 配置尝试四次开关，全部成功且零派发；生产正式绑定和实际 T3 回执仍待验。
- **CWP P1-01**　Windows hosted 检出修正后，US、CN 的真实 RF→FF→CWP 使用 loopback 采集与复用。[组合 CI](https://github.com/zhengcb81/company-wiki/actions/runs/46095233076) 已通过。两个配置入口曾无条件解析默认用户目录，已由同一 owner 解析器仅在出现变量时读取，显式隔离配置可无 HOME 正常工作。历史期次从已捕获的披露证据解析，发布日期或跨年范围不能冒充财报期次。完整矩阵仍发现正文构造器导入冲突、Windows 依赖注册表的 MIME 推断，以及实际来源资格和原件恢复等问题，按共同根因对照失败节点逐项修复。已复现原件遗失后同 SHA 重取因可变披露日期触发 immutable provenance 冲突。源码改为在恢复原件前验证并保留既有捕获绑定，异质或畸形绑定不会产生孤立原文；新上游观测按既有日期规则处理。Windows 来源资格与采集 94 项通过。随后修复 Windows 同根路径别名和零秒读取到期，原件读取及入库边界分别 68、86 项通过。用真实中断、原身份冷读和已存回填验证缓存复原且不再付费。共享 AST 指纹先红后绿，保留已发布 3.13 指纹，独审核对及 27 个共享检查通过，IQS 已在真实 CPython 3.12.12 通过同一棵树 `c090b6e4601bd5343e25de5f108f97c0c54454b6` 的全仓基准。CWP 最新候选 `277d5326733ea1da050dab3637adf5bf900f2318` 的 [公开组合](https://github.com/zhengcb81/company-wiki/actions/runs/46103963612) 已通过，[第三轮全量](https://github.com/zhengcb81/company-wiki/actions/runs/46103963604) 验到历史 activation CLI 早已退休、运行用的 console 选项已迁到本仓启动层，以及 Linux 在强杀时空闲 Worker 可先退出而漏终态。独审在隔离 Windows Junction 验出原文会先越出根再拒绝。已改为解析并校验原件与 sidecar 路径后才写入，48 项写入回归通过；共享父进程活性判定使 Worker 停止新领取，由 watchdog 唯一写强停终态，真实冷读每个 attempt 恰一条，现存账与派发不增。默认 wiki 根跟随配置，删旧用户目录猜测。历史激活事务仍测试，退休 CLI 检验真实零写。复用了同一个测试 SQLite 生命周期修正释放，48 项版本类回归通过。已跟当前主线文档对齐，精确 `e3f7dc743f58f1629bd72a9a4cd735d1ff960625` 的 [全量双平台](https://github.com/zhengcb81/company-wiki/actions/runs/46105564129) 正在执行。
- **RF P1-05**　首轮 Windows 仅余一个并发失败时，根因落到测试共享发布登记文件。新版每个用例使用独立登记，仍走真实 CLI；stdin 替代 Windows 超长参数，子进程按所需环境构造，快测 Ruff 使用无缓存运行。Windows 55 项定向复验后，[双平台首次通过](https://github.com/zhengcb81/revenue-forecast/actions/runs/46095931282)。独审发现 Windows 路径守卫漏检并用四个反例红转绿，新稀有并发失败又证明单文件反馈的查重加追加未持同一文件锁。复用本仓 OwnerFileLock 后不同事件不丢、相同事件只写一次，冷进程可补投且再次 flush 为零，五组实际回归通过。[候选 `d147758b` 双平台](https://github.com/zhengcb81/revenue-forecast/actions/runs/46099650739) 全绿，已用 12 项快测推远端 `main`，[精确发布版 Windows 与 Ubuntu 工作流](https://github.com/zhengcb81/revenue-forecast/actions/runs/46100063790) 也已通过。
- **Audit P1-06**　独审发现共享可写源码被临时测试夹具修改、随后还原时可能污染另一分片。真实双分片红测复现已污染值，改为收集、各分片及参考测试从同一个 Git blob 集合生成各自物理副本和独立状态根。负控红转绿，恢复复用确切的已有成功回执。`f4a2d5d5f75c140bcf5bc5d6a67adbae6c93ab17` Windows 六片 869 项实跑全部通过，参考工具 26 项加 7 子例，独立复审通过并快进本地 `main`。原并行 PWF 字节未变。无远端，Linux 已配置，未实跑。
- **StockWiki P1-07**　`6cd6d7ef5ad706c1e4581e91f2c87107be112572`，Windows 精确清单和执行各 2,390 节点，零跳过，历史 C06 另 513 项原生实跑通过。独审核对测试与执行节点集合、C06 冻结依赖及测试启动器相同，确认事务回滚、SQLite URI、Windows 长路径与实际反馈。已快进本地 `master`，原 PWF 三处未提交差异逐字节保留。无远端，Linux 工作流已配置，仍未实跑。
- **IQS P1-08**　基于 `b4aee7fb` 的独立工区完成首轮收集调查，发现数个组合直接导入只存在于本机的实验仓或私有测试工具。将可移植的行为在公开协议上运行，真正依赖 owner 资产的组合仍保留精确版本及实测待办。候选 2,309 个 Windows 自足节点已收集，实际 HTTP 半截响应、冷读、锁竞争和无窗行为定向通过。[草案 #1](https://github.com/zhengcb81/invest-quick-scan/pull/1) 的 Linux 首次运行因旧发布基准的 CRLF 字节仅由 Windows 检出配置生成出现成批拒绝，基准真实发行字节已由 Git 保持且原 SHA 不变。修复 Windows CI 日志输出编码与证据上传目录，使用步骤作用域的 runner 临时目录。精确 `08a17bc` 的组合在 Windows 有 135 项失败，Ubuntu 有 264 项失败和 19 项错误。已从实际 CI 定位题库内其他发行字节与进程级反馈身份污染，IQS owner 已修复反馈调用修改进程级环境导致后续作业串号，保留 188 份发行原始字节，对历史重放按业务臂稳定排序。边界 174 项、原件和回放 236 项、事实 CLI 23 项，6 项此前依赖专用 owner 资产的代表测试实跑。[同版初次双平台](https://github.com/zhengcb81/invest-quick-scan/actions/runs/46104084859) 业务执行均绿，聚合准确识别漏标的跨仓 temporal owner 节点，已以实际 StockWiki 精确版本另跑通过。开发快测已通过 1,068 项及 391 子例。[新候选双平台](https://github.com/zhengcb81/invest-quick-scan/actions/runs/46105293396) 待验；跨仓 C06 的剩余问题由 QA 历史 fixture 转换为公开 membership 端口，保留委托流程。

- **MC P1-12**　原生 CLI 的 `--config` 以真实 WAV、实际 ffprobe、随机端口回环 HTTP 红转绿。CLI 覆盖配置选择，坏显式配置不退回或派发，200 响应断流只 POST 一次并可从新的 owner 进程按原号查回，费用未知保持。原 404 项 Windows 执行中 45 项共用失效继承句柄，汇集测试启动器后同一真实反馈集合 67 项通过。精确候选 `6955b49ad8b5ec327a2260d65401b6ed2e570c88` 的 [Windows 与 Ubuntu CI](https://github.com/zhengcb81/MeetingConverter/actions/runs/46099708180) 全绿。独审追加 21 项无窗复跑及真实含空格配置路径验证，通过后以相同 SHA 快进远端 `master`。[发布版双平台回执](https://github.com/zhengcb81/MeetingConverter/actions/runs/46101904058) 已绿。P2 仍需改进坏显式配置的错误归属文案。
- **Dashboard、StockQA、IR**　分别在本仓短路径隔离开工。Dashboard 修收集冲突和 React 真实竞态；StockQA 已用 IQS 公开导出替代私有测试导入，并用 SQLite 坏 checkpoint 复原历史回归；IR 在真实 CLI 通过本地 HTTP 研测推荐依据与报告，Dashboard 首轮 Windows 1,803 项通过、14 项失败、26 项 CWP 夹具错误，并发现 M8 路由组合根把能回取整个 catalog 的绑定方法传给了窄路由。StockQA 本机串行 900 秒触发期限，先执行 716 项、出现 68 项实际失败，证据指向旧夹具子进程入口和诊断读取方式，继续检查实际日志的可复现性。IR 精确业务 `a81cfdd` Windows 327 项及 102 子例通过，另跑 owner 比较 2 项及 14 子例；私有 PR `ef5c791` 已成功触发 [原生双平台运行](https://github.com/zhengcb81/industry-research/actions/runs/46102140560)，Ubuntu 通过，Windows 四项失败都比较了同一物理目录的 8.3 别名与长名称，改测试夹具统一根后再验。修复后的 IR `208d6a1b10bcc06e3a0ed404d5b9ddb8dd88169e` [私有精确双平台](https://github.com/zhengcb81/industry-research/actions/runs/46102700730) 全绿，Windows 327 项及 102 子例。独审用三个本地端口复验配置顺序、实际模型、完整报告和 200 截断请求只派发一次，快进远端 `main`。Dashboard 继续修 [真实双平台运行](https://github.com/zhengcb81/investment-dashboard/actions/runs/46104428365) 暴露的 OS 路径、句柄和浏览器重现问题。StockQA 独审用 13 个原生用例确认已改善部分冷恢复，发现正式快速扫描调用仍会把坏 checkpoint 当作缺失，还缺真 HTTP 搜索与重收据端到端。最新真实 CLI 已复现损坏成员让同批健康成员也得不到结果，在 StockQA 独立工区从 owner 读取契约修复。

## 2026-11-28　四路待收口与 SID 第二次发布

- **SID P1-04**　新的原生强停组合发现无 Windows 用户根时，默认状态在显式反馈路径之前解析。采用既有配置优先级，从 OUT/DIR 得到隔离状态位置，无可用用户配置时才选择系统临时根。独审用实际 CLI 验证 OUT、DIR 与临时态各只 POST 一次，DIR 硬停后按原 run/attempt 冷读，原收据字节不变。独立 12 项通过。精确版本 `33377928b928cfcb92457c2e49a57eacd8391201` 已发布至实际 `v2-clean-rewrite`，[发布 CI](https://github.com/zhengcb81/StockInfoDownloader/actions/runs/46107181725)双平台通过。
- **CWP P1-01**　旧进程内清理在 pytest 已执行完成但仍持有真实 SQLite 句柄时以 WinError 32 改写成功退出。CI 启动器拥有独占临时根，在子进程退出后统一回收，输出证据留在原目录。原生子进程用 0 和 1 两条路径验证退出码和临时数据，真实 Windows 目录联接夹具不使用慢 PowerShell。独审通过；历史直接 pytest 的回退仍沿用原生命周期，托管 CI 复现的问题已覆盖。父进程根的命名进入现有 Git 临时文件模式，完整 P4 Windows 34 项通过。候选 `f334cf33e65c9f11eeff7ce5c130f9007a87ad6c` [全量](https://github.com/zhengcb81/company-wiki/actions/runs/46108246973) 27 项和[公开组合](https://github.com/zhengcb81/company-wiki/actions/runs/46108246971)均绿。覆盖聚合核对两平台完整收集与实际执行。以精确 SHA 快进远端和本地 `master`，底层原件与目录均不在范围，所有本地暂存和未暂存差异保持原样。精确发布 [Windows、Ubuntu 完整 27 项及执行聚合](https://github.com/zhengcb81/company-wiki/actions/runs/46109776696) 和[公开联调](https://github.com/zhengcb81/company-wiki/actions/runs/46109776718)均通过。收集并核对实际执行的适用节点为 Windows 16,628、Linux 16,573。
- **IQS P1-08**　[上一版同 SHA CI](https://github.com/zhengcb81/invest-quick-scan/actions/runs/46106295054) Ubuntu 2,295 项、Windows 2,308 项及执行清单对齐。独审复现畸形公开回放错误串入外层作业，已将各解析后路径绑定显式调用上下文。准备作业在锁占用时可读已提交终态，放弃等待后仍能收录原调用的迟到结果，不重新开始。84 项定向及独审通过，`6da5e0f7e21f9e0cb84a0724707c23f55c5b2027` [精确在线矩阵](https://github.com/zhengcb81/invest-quick-scan/actions/runs/46108302262) 两平台与覆盖聚合通过。旧 C06 四案使用过时的私有 membership fixture，owner 正接新公开接口。第 5 案旧夹具手组多工具请求，首轮入参在发送前测得 259,925 超出 240,000 的预算，未进入模拟强停。保持原超限保护，按正式 owner 冻结分包重做了真实强停。Windows 正式注册与合成回环只 POST 一次，原检查点落盘后退出 86。无当前凭据或额度配置的冷进程封存全部十二题，原文件和账本不变，新增请求及费用为零。超额反例也通过。独审核对运行记录与 Git 归档字节，测试和回执纳入 `18811363957b3cc5014c21f7f79f85fe797ef71a`，[精确 CI](https://github.com/zhengcb81/invest-quick-scan/actions/runs/46111195318) Windows、Ubuntu 与覆盖聚合通过。其余四个 C06 用例也经 Windows 分批原生实跑通过，覆盖真实授权、原响应封存、全量不重发、部分题包和原模型作业硬停。较低进程优先级令初始化超过原时限，切回正常优先级后通过，原时限和限额不变。独审核对公开会员夹具及各用例收据，同一个 IQS 提交以精确 SHA 快进 `master`。[发布版 CI](https://github.com/zhengcb81/invest-quick-scan/actions/runs/46112107953) Windows、Ubuntu 与覆盖聚合均通过。
- **Dashboard P1-09**　[精确私有 CI](https://github.com/zhengcb81/investment-dashboard/actions/runs/46106571261) Ubuntu 通过。Windows 复现超过断言的句柄计数和剩余时间浮点精度。独立用原生 CPython 3.12 保存一次真实错误，确认 CLI 异常保留已结束线程和事件，HTTP 异常原因还保留已关闭流的内部上下文。已在拥有 CLI 和 HTTP 资源的调用边界生成脱敏异常链和代码位置，释放活动对象后向上抛错。实际 Windows CPython 3.12 定向 65 项通过，四种慢 HTTP 错误无句柄增长。故意留两个管道句柄的对照仍触发原限额。候选 `bdcd292d931603d73007acc3b7834fa84b17cd23` 的独审确认实测句柄与诊断正常，但[同版双平台](https://github.com/zhengcb81/investment-dashboard/actions/runs/46108967380) 暴露公开值多出内部诊断字段。现将原五个公开字段保持原样，脱敏链由 F4 私有持有。`d0f5f1331c0902a286410f01476d00e89d4f5da6` 原生 Windows 74 项通过，独立 5 项复验通过，[私有精确双平台](https://github.com/zhengcb81/investment-dashboard/actions/runs/46110656593)均绿。同一候选已快进远端 `main`。以 CWP `f334cf33` 实际打包、安装 wheel，在空 cwd 用 Dashboard `d0f5f13` 与 StockWiki `6cd6d7e` 走公开入口验证原件 SHA、摘要、证据、页/段落定位；Windows 1 项通过，172.40 秒。正式 Dashboard 服务未重启。
- **StockQA P1-10**　真 TCP 与坏原检查点两例通过独审，精确 [3871a75 双平台](https://github.com/zhengcb81/StockQAbyLLM/actions/runs/46106479728)另外发现九项。把所有校验都包成统一读取错误，丢了既有直接读取的错误，又把 owner 原绑定拒绝误作损坏。现共享同一个实际读取校验，直接读取保留原错误，恢复保留可定位的原工作和尝试号，owner 拒绝保持精确原因且不会当缺失重新派发。309 项 Windows 原生回归通过。候选 `d547e1735beabaa3baf21dc79bd35c184367d8ef` [同版双平台](https://github.com/zhengcb81/StockQAbyLLM/actions/runs/46108509964)均绿。独审另实测原作业的已存上下文或标准答案坏 JSON 仍会中止整批。归到原尝试号，由存量附件边界统一捕获，保留原字节、主检查点、原因链与明确的策略拒绝。`603a56e9102885fa9ffdff8550c48ec71b674e2e` Windows 定向 125 项和独立 10 项通过，[精确双平台](https://github.com/zhengcb81/StockQAbyLLM/actions/runs/46110536413)均绿。同一 SHA 已快进 `master`，[发布版 CI](https://github.com/zhengcb81/StockQAbyLLM/actions/runs/46112387858)双平台通过。C06 四个历史 IQS 用例已有同一冻结 `d547e17` 源码与公开 membership 夹具的原生通过证据。StockQA 委托回归也走正式 budget-managed 路径，真实本地 POST 后超时记录原费用未知；撤销后不可二次发送且回写未发送记录，独审核对测试字节。已将测试限定为三份文件收入 `75da3590522a806f09cb34c9db07161abad8a7f7`，[最终精确双平台](https://github.com/zhengcb81/StockQAbyLLM/actions/runs/46112910355)通过，以同一 SHA 快进远端 `master`。两个既有准入对照按原时限单独运行，JUnit 2/2 通过，单次启动包装在测试后格式化输出时报错，因此仅采用 JUnit 作补充见证。发布的运行代码与 `603a56e` 相同。
- **StockWiki P1-07 原生 Ubuntu 补验**　实际 3.13 完整执行 2,371 项通过、1 项跳过、2 项失败及 11 项同因浏览器错误。浏览器已装在隔离根，但正式测试启动器清理了浏览器位置设置。黄金样本 Linux 检出文本换行与原密封 SHA 不符，Windows 工作文件与冻结哈希匹配。只允许保留原冻结字节，不能更新预期哈希。真实 SourceExport 组合也因子 CWP 入口未收到所选源码环境返回 `receipt_missing`，继续核对真实输出与传递范围。修复在独立工区进行。六份样本核回同一套冻结哈希，实际 CWP 转发明确使用原始标准流和选定的 producer，Ubuntu 真 Chromium 11 项与 Node 调度验证均通过。`9605faec234c9b2798b4d1df4ef5f16dbfb42f25` 的 Ubuntu 全量 2,385/2,385，执行覆盖证明无差异。独审核对原字节和进程边界并同意候选设计。原生 Windows 同版 2,389 项通过、1 项失败，已用真实独立子进程复现为父进程退出后测试孙进程未持有预期管道。修正夹具实际句柄继承并保留原时限、预期失败、进程树和旁路进程断言。原 StockWiki 在途工作保持原样。

- **Audit P1-06**　Ubuntu 原生验证发现 mypy 不支持在平台类型中直接引用 Windows 标志，收敛到一个可移植入口。原系统测试按全局第 2 次 fsync 注入时误命中 POSIX 的冻结库目录，改为命中实际工作副本描述符。故障后子进程仍未启动，重启清除指定副本，冻结原内容保存。精确 `e0e2b0feb65d3c8650ff05afba7d7f6cebff24ea` Windows、Ubuntu 均 869/869 项通过，另每侧参考工具 26 项及 7 个子项，独审通过，已快进无远端的本地 `main`。本仓发布记录 `9a6d4a8f`。

## Phase 2 只读准备

Phase 1 的全量和独审继续执行。尚未启动 Phase 2 实施。抽查已发布入口，后续同仓统一记录器时先用真实失败固定这些缺口。

| 所属模块 | 已定位的入口与写入边界 | 第一批真实回归 |
| --- | --- | --- |
| FF | `scripts/ff_job_store.py:348` 作业事件绕过 `ff_runtime_log.py:98` 的跨进程轮转锁。两条落盘路径均失败时缺告警。Scheduled Windows 的规范化和部分参数错误发生在记录器外。真实 FF 回执 CLI 同为退出 2、机器 stdout 为空，未知参数会按原作业记录 argument_error，解析完才发现非法引用则零落盘。未接外部服务。 | 两个真实子进程向同一隔离作业记录并冷读，逐条验证原作业号。让日志及旁路均不可写，保持原 JSON 与退出码，留下安全警告。 |
| IR | `tools/feedback_owner.py:261` 的解析和 `tools/install_reporting_tools.py:45` 缺启动记录。`tools/native_feedback.py:221`、`:253` 没有同一跨进程锁，后者绕过已选日志目标。 | 从现有真实 HTTP 200 断体用例接通发布端，验证一次请求、折行凭据与 URL 用户信息脱敏、完整尾栈。两个原生进程争同一轮转文件。 |
| MC | `feedback_owner.py:319` 缺解析与冷读日志。库调用在没有 CLI handler 时直接丢事件。`transcribe.py:126` 将通用诊断送 stdout，显式配置出错文案仍固定为 config.json。 | owner 非法 stdin、阻塞双根及两个并行库调用绑定不同作业。实做 Windows 不允许删除旧日志的轮转降级，保证原回执输出和媒体账不变。 |
| IQS | `process_logs.redacted_output_lines` 实证漏了折行 Bearer / Basic、ghp_、tvly- 和 AIza。`open_dashboard` 很早的参数或配置错误发生在持久日志初始化前。 | 让真实无窗入口产生上述合成值并触发原失败，按同一身份从文件和 F4 冷读。验证配置失败时原退出码、无新增派发和日志尾栈。 |

各仓由组合根在参数解析前绑定本仓调用上下文，持久化运行轨迹和错误，沿用原业务账与原外付记录。序列化脱敏后在同一文件锁内轮转与写入。普通诊断保留在诊断通道，现有机器 stdout/stderr 不追加散文。F4 继续读取本仓公开接口。纯值计算沿用调用方上下文，无需新日志入口或许可。

Step 0 入口盘点从实际发布的安装声明、CLI 分派、HTTP 路由和调度入口求并集，再区分正式入口、兼容别名和仅测试工具。FF 当前发布树可见七个脚本入口（常规采集、财务报表、作业、反馈、定时刷新、Windows 定时、T3 回执），各入口还要核对解析后子命令是否共用调用上下文。CWP 当前 `pyproject.toml` 声明十一条控制台脚本，包内还有独立公开模块、Worker、计划任务及 F4 入口。逐条核对实际绑定与最早失败点后冻结清单，避免把同一函数的别名重复当入口覆盖，或把没有 `__main__` 的正式宿主漏掉。Audit 安装层实际有十五个按文件调用的正式 CLI 候选，待与技能和任务配置逐条匹配。已完成 CWP、FF、ET、SID 的发布树入口盘点，后续在各自实施记录引用具体入口和用例。其它仓继续逐仓核对。

- CWP `f334cf33` 的 32 个可执行模块和其他实际宿主见下方 P2-01 入口盘点。先补外层组合启动、原异常链和三表退出 0 的成员失败。Windows F4 定时任务用 `pythonw`，当前没有明确的诊断目的地。测试保留原文流、浏览和叙述的机器 stdout 或 stderr 字节。
- FF `c72c3a1` 的 7 个入口有独立直接作业、异步作业、定时槽和 T3 收据。冷读遇到损坏不能当正常缺失。4 个解析后拒绝接回同一个调用边界。原作业日志与原反馈身份保留，复用所属锁和轮转；冷读、刷新和控制错误用本地诊断，不自触发新的 F4 事项。
- ET `b0d8394e` 的 6 个主要入口加反馈和 retrieval worker。复用 `runtime_scope`、`runtime_logging` 与 `retrieval_diagnostics`，覆盖配置前失败、本机 Reader HTTP、两进程轮转和双写失败。保持原动作默认无翻译、冷读只读及既有机器输出。
- SID `33377928` 的普通下载与独立无浏览器执行器、反馈与投递是不同适配面。收敛到已有作业步骤、文件锁和诊断作用域，区分发前拒绝、身份、文档下载及已派发后状态未知，保留原 SHA、预算与错误码。错误 JSON、原生 stderr、失败下载日志都须走相同脱敏边界。
- RF `d147758b` 的 20 个 `scripts/` 可执行文件包含废弃过渡入口与探针，4 个主要回调已有失败记录。定时日跑、周跑、发布、报表、三表和 F4 逐类核对。保留原 ledger 和费用未知，优先补失败记录与部分落盘后的冷读，无需多一套发布许可。
- Audit `e0e2b0f` 的安装树有 15 个可执行脚本。角色作业、进度协调、F4 重放分别受各自原记录约束，派工和定时由外部宿主负责。统一参数解析与异常脱敏，轮转降级和失效 outbox 可诊断，维持 CLI JSON/JSONL。
- StockWiki `6cd6d7e` 的统一应用 CLI、Dashboard owner 路由、本地 HTTP 和周调度归属分别确认。保留既有限额 16 MiB 及真实错误区分。调度恢复判断要依据原子进程是否可能派发，不能仅按经过时间把费用未知作业重排。
- MeetingConverter `6955b49a` 覆盖转写、公司工具、引擎对照和 F4 owner，另有库模式。实际两个同进程调用同时进入诊断作用域时，两份日志各收到两次的同一组阶段，证实共享 logger handler 将另一调用写进本作业。改为按调用持有归属与输出，复用既有记录器和原费用。补临时目录的两个调用并发及两个独立进程争同轮转文件。

### P2-01 · CWP 入口盘点（发布源码 `f334cf33`）

| 实际入口 | 调用归属及最早失败点 |
|---|---|
| 安装声明中的 11 个控制台入口 | `source_contract.cli` 以及 `source_catalog.{announcement_cli,cli,source_reader_cli,source_query_cli,company_source_index_cli,source_export_v2_cli,identity_cli,transcript_import_cli}`、`automation.{narrative_transport_cli,narrative_batch_cli}`。均已有外层作用域。具体检查参数错误、适配器调用和已捕获异常的结案分支，重点保留 source-export、identity、transcript-import 转换前的类型和尾栈。 |
| 其他 15 个独立模块 | `automation.cli`、`runtime_trace`、`source_catalog.{dayu_sdk_cli,financial_statements.cli,local_prepare_cli,official_source_cli,processed_document_cli,public_canonical_browser_cli,public_legacy_source_link_cli,public_document_browser_cli,public_legacy_source_recovery_cli,public_source_citation_cli,public_source_readiness_cli,source_stream_cli,t3_workspace_cli}`。AUTO 现只在 plan 和 feedback-flush 内侧设作用域，status、doctor 及外层解析未覆盖。T3 工作区请求和绑定校验缺外层作用域。三表批次可能以退出 0 返回部分成员失败。trace 健康冷读保持只读，读取失败从本仓诊断恢复。 |
| 3 个兼容路径 | `source_contract.announcement_cli`、`source_catalog.narrative_transport_cli` 进入已安装入口。`source_catalog.incremental_cli` 和 catalog 的定时读命令均进入 `scheduled_reading.main`，在该组合根记录加载与解析失败，避免别名改变原作业号。 |
| 运维与子进程 | `source_catalog.{artifact_backfill,backfill_v2}` 直接调用时需要记录其配置及执行失败。`source_catalog._paragraph_worker` 由 PDF 增强父进程拉起，保留原子进程退出/协议/失败原因。AUTO Worker 的失败由原 attempt、冻结观察和 outbox 归属。 |
| F4 宿主与定时任务 | `tools.feedback_loop.{__main__,local_host,intake,hook,codex_cli,_background}`。按公开进程命令、原作业冷读和内部拉起区分。`local_host recover --save-result` 的 Windows 任务直接用 `pythonw`，现有换用 stderr 文本记录的包装依赖 `CWP_F4_ERROR_LOG`，而该任务未配置。用本仓状态路径记录已知的启动及入账错误。F4 自身故障可冷读，避免写进需要自己处理的观察队列。 |

基线原生探针在隔离目录直接调用 `python -m company_wiki.source_catalog.t3_workspace_cli`，以合成错误 schema 走真实 stdin。返回原协议 JSON、`invalid_request`、退出码 2，stderr 为空，原 run `s6-t3-malformed-fixture` 无日志。候选必须保留协议并新增同一 run/attempt 可冷读的原错误原因。

先通过真实进程锁定三类行为。第一类覆盖解析及已归类的运行失败，核对 UTF-8 事件、原因、调用位置和折行凭据脱敏。第二类覆盖一个日志目录失效、有其他归属路径时转写，以及所有落盘目的地不可写时的原退出码与合适诊断通道。第三类验证并发调用日志归属、原生跨进程轮转和 Windows 文件被读者持有时仍落盘。每条业务路径继续由所属协议决定是否拒绝，诊断不可用不改变业务结果。

## Session: 2026-11-27

### 前置审查与规划（首批实施前的历史记录）
- **Status:** complete
- **Started:** 2026-11-27 19:43 UTC
- **Completed:** 2026-11-27 20:06 UTC
- **Actions taken:**
  - 读取 `planning-with-files` 规范及项目既有总控 PWF（`PLANNING_STATUS.md`、`README.md`、`du11-source-closure-2026-10-18/CURRENT_STATUS.md`、`HANDOFF.md`、`task_plan.md`、`module-boundaries-2026-11-11/*`、`feedback-loop-2026-11-17/*`），厘清 12 个自有模块职责、历史 S1–S5 演进及最新 2026-11-27 无窗/恢复基线。
  - 核对全部 12 个仓库的本地分支、远端分支与实际运行 worktree，定位并校正了 RF（`.worktrees/f4rd@782cfd9a`）、IQS（`.planning/wi26@3094c5f7`）、Dashboard（`release-de59feed@de59feed`）、StockQA（`.worktrees/f4-runtime@86f633d8`）、IR（`.worktrees/f4-runtime@77f3c7dd5`）的真实最新代码检出。
  - 运行全量只读 Python AST/正则/Git/测试扫描脚本（覆盖 2,039 个生产 Python 文件、524,419 LOC、约 20,000+ 条测试函数），量化统计全部 12 模块的 SCC 运行时环、延迟导入、私有导入/属性/反射、`sqlite3.connect`、`sys.path`/`sys.modules`、硬编码路径/URL/模型/端口、日志覆盖、无日志 `from None`、静默吞错、最近修复提交及测试结构。
  - 并行派发四路只读深度架构与质量审查员（Cluster A: CWP/FF/ET；Cluster B: SID/RF/Audit；Cluster C: StockWiki/IQS/Dashboard；Cluster D: StockQA/IR/MC），逐文件核查源码与测试，沉淀精确 `file:line` 证据与历史缺陷回归对照表。
  - 直接只读核验 IQS `quality.yml`、Dashboard `feedback-contracts.yml`、IR `owner-contracts.yml`、RF `origin/main:quality.yml`、StockQA `origin/master:ci.yml` 及 `scripts/checks.py`，消除隐藏目录与稀疏工作树盲区。
  - 将完整审查发现与 6 阶段实施方案（Phase 0–Phase 5）写入本 PWF 包，并同步在父级总控入口登记链接（`PLAN_ONLY`，未修改任何生产代码、测试或配置）。
- **Files created/modified:**
  - `docs/plans/ecosystem-quality-audit-2026-11-27/findings.md` (created — 全 12 模块定量总表、5 大系统性根因、9 类伪解耦技巧清单与逐仓 `file:line` 详录)
  - `docs/plans/ecosystem-quality-audit-2026-11-27/anti-trick-governance.md` (created — 四层反偷懒/反伪解耦治理机制：10 类技巧黑名单 AP-01..10、12 项静态 AST/Meta 门禁 AT-01..12、4 项运行时行为证明 B-01..04、对抗式独立审查与 3-Strike 熔断协议)
  - `docs/plans/ecosystem-quality-audit-2026-11-27/module-blueprints.md` (created — 全 12 模块逐仓目标包树、单向 DAG、公开 `Protocol`、日志接线、硬编码清退与七维 E2E 施工蓝图)
  - `docs/plans/ecosystem-quality-audit-2026-11-27/task_plan.md` (updated v2 — 纳入 P1-00 防偷懒门禁前置落地、单卡强制 6 步闭环流水线、全局依赖图与全部 Phase 0–5 精细施工卡)
  - `docs/plans/ecosystem-quality-audit-2026-11-27/progress.md` (updated — 审查与计划深化日志)
  - `docs/plans/du11-source-closure-2026-10-18/CURRENT_STATUS.md` & `CURRENT_STATUS.json` & `HANDOFF.md` (updated — 正式将本计划登记为主线 `S6` / `ecosystem-quality-audit-2026-11-27`，排在 `feedback-loop-2026-11-17` S5-10/F4 收尾线之后、W12 业务摘要接续之前，状态保持 `PLAN_ONLY_QUEUED_AWAITING_USER_START`)
  - `docs/plans/feedback-loop-2026-11-17/task_plan.md` & `docs/plans/module-boundaries-2026-11-11/task_plan.md` (updated — 增补主线直接后续交接指向 `ecosystem-quality-audit-2026-11-27`)

## Test Results

| Test | Input | Expected | Actual | Status |
|---|---|---|---|---|
| 只读定量扫描 (`audit_12_modules.py` + `summarize_audit.py`) | 12 仓最新正式代码树 | 全部 12 仓 AST/硬编码/日志/Git/测试完整产出 | 12/12 仓成功扫描，0 源码改动，产出 `audit_12_modules_result.json` | PASS |
| 四路并行深度源码审查 | 12 仓真实源码与测试文件 | 4 维度精确 `file:line` 证据 + 历史缺陷矩阵 | 4/4 路完成并交叉验证 5 仓 `.github/workflows/*.yml` | PASS |
| 生产代码与配置零修改核对 | `git status --short --untracked-files=no` | 零新增生产代码或生产配置变动 | 仅新增规划文档，生产源码与 `config/source_catalog.yaml` 零修改 | PASS |

## Error Log

| Timestamp | Error | Attempt | Resolution |
|---|---|---|---|
| 2026-11-27 19:44 | PowerShell 递归扫描 `.venv`/`.planning` 耗时过长 | 1 | 取消任务，改用跳过非源码目录的定向查询。 |
| 2026-11-27 19:48 | 临时脚本 `audit_12_modules.py` 局部变量 `full` 未初始化 | 1 | 初始化 `full = ""` 并优化 `ExceptHandler` 遍历，全 12 仓顺利完成。 |
| 2026-11-27 19:52 | 稀疏工作树（RF/StockQA）无 `tests/`/`.github/` 且 `skills/` 过滤导致 Audit 统计偏低 | 1 | 用 `summarize_audit.py` 放开 Audit `skills/` 并通过 `git ls-tree`/`git show` 读取远端完整测试与 CI。 |
| 2026-11-27 20:02 | 子代理未列出隐藏目录 `.github/workflows`（IQS/Dashboard/IR） | 1 | 直接 `read_file` 读取 3 仓 workflow 文件核正，避免误报“零 CI”。 |

## 5-Question Reboot Check

| Question | Answer |
|---|---|
| Where am I? | S6 首批已派发，逐仓接收状态见下方台账。 |
| Where am I going? | P0 止血和 P1-00 并行，随后按仓接入 Phase 1，再做日志、架构、配置和组合 E2E。 |
| What's the goal? | 让全部 12 个模块达到真正架构级松耦合与封装、无硬编码高质量代码、全入口可追溯日志+历史错误回归锁定、以及高置信度跨平台端到端测试覆盖。 |
| What have I learned? | 详见 [findings.md](findings.md)：12 仓存在 11 项实时 P0 级隐患（含 Audit/ET 实时 `NameError`、IR 推荐依据静默丢数据、StockWiki 未转义 SQLite URI、IQS 80ms 锁困死等）、9 类“小技巧伪解耦”、系统性日志/stderr/stdout 缺口及 9–10 仓 CI 樱桃采摘/零 Windows CI 盲区。 |
| What have I done? | 完成基线审查；实施、接收与发布状态分别记录在后续条目。 |

## 2026-11-27 21:02 UTC — 配额中断（BLOCKED: 外部配额，非技术问题）
- Wave 1/2 共 12 个 card-implementer 因 RESOURCE_EXHAUSTED (HTTP 429, Individual quota) 全部中止；约 3h41m 后重置（约 2026-11-28 00:43 UTC）。
- 中断时 C:\Temp\s6\* 的 13 个 worktree 均无任何提交（HEAD 仍为基线 SHA），仅 mc 有 1 个未提交改动；无半成品落入主 checkout，生产配置/主 checkout 未被触碰。
- 切换模型后 send_message 续跑 P1-00 仍返回 429，确认为账号级配额。
- 恢复动作：配额重置后重新派发 P1-00 与 P0-01..P0-11（先核对各 worktree git status，mc 的未提交改动需先审视），随后按 anti-trick-governance 流程独立对抗审查。


## 2026-11-27 21:04 UTC — 换模型后重新派发
- 旧实现者会话固定在原模型上，续跑仍 429；新建的 card-implementer（继承新模型）正常运行。已为 P1-00、P0-01..P0-11 共 12 张卡重新派发全新实现者（worktree 与基线 SHA 不变，均无历史提交）。
- 原派发记录。当前按候选到达顺序接收，见下方首批交接台账。

## 首批交接台账

2026-11-27 22:36 UTC。总控只读核对 13 个工区的 HEAD、状态及发布引用。首批 12 张卡均沿用原指派，未见高于下表基线的候选提交。Audit 有两处在编，其余工区当时干净。下表是已观察到的交接状态，不能用于推断作者进程是否在线。收到候选后在对应行登记候选 SHA、关键用例、独审和集成版本，复用 owner 原记录。

| 卡 | 工区（位于 `C:/Temp/s6/`） | 派工基线 | 总控接收状态 |
|---|---|---|---|
| P0-01 Audit | audit | `9e9e980` | 等候候选；实现与测试有未提交改动 |
| P0-02 ET | et | `672ed10` | 首页故障已隔离复现，等候修复与进程回收证据 |
| P0-03 IR | ir | `77f3c7d` | 等候候选 |
| P0-04 StockWiki | stockwiki | `0fbaf7c` | 等候候选 |
| P0-05 IQS | iqs | `3094c5f` | 等候候选，保留原运行工区 |
| P0-06 CWP | cwp-p0 | `35b8b250d` | 等候候选，只接收 CWP 适配器、CLI 和定向用例 |
| P0-07 FF | ff | `4dd4e13` | 等候候选 |
| P0-08 SID | sid | `5c65605` | 等候候选 |
| P0-09 RF | rf | `782cfd9a` | 等候候选，以已验 SYSTEM 版本为运行基线 |
| P0-10 MC | mc | `7b83fe6` | 等候候选 |
| P0-11 Dashboard | dash | `de59fee` | 等候候选；集成时核验后续发布改动，见下 |
| P1-00 工具 | cwp | `35b8b250d` | 等候工具和正反例，自身可单独验收 |

`stockqa@86f633d` 是第 13 个预留工区，当前批次未派该卡。P0-12 的首轮只读清点发现 12 仓共登记 188 个 Git 工区，IQS 有 1 个被 Git 标记为 prunable；IQS 唯一标为 prunable 的记录属于 Dashboard 的独立施工项目，实际叶目录和上层工区仍存在。目前保留，等该 owner 确认有效入口与独有产物。总控已回收本轮两个用于发布的空临时工区。

**发布目标复核。** 独立核验发现，9 张卡与本地已有发布引用同版。CWP 两张卡的基线到总控 `e90a16c59` 只有两个 F4 文档提交。Dashboard 的 48766 部署记录（Dashboard 本仓 `.runtime/dashboard-m7-666e242/live-release.json`） 记载 20:20 UTC 已发布 `666e2426`，相对施工基线多 5 个提交。本地 main 与已知 origin/main 分别另有 6 和 8 个提交。在候选到达时刷新发布头，只合并故障修复，验证 `backend/dashboard/main.py` 与 `adapters/factory.py` 仍把 `rf_verified_scope_root` 传给 RF，保留已发布的作业分页。组合验收使用隔离目录与随机本地端口。

**ET 首页基线实测。** 总控从 Git 对象 `672ed1012e27685b58e501377f2548a859ff20da` 读取 reader、真实模板及其依赖，在临时目录放入空公司表与本地配置。用真实 `ReaderHandler` 监听 `127.0.0.1:0`。先 GET `/api/data` 返回 200 和空数据，再 GET `/`，客户端收到 `RemoteDisconnected`，服务端是 `NameError: _TEMPLATE_FILE`。临时目录已回收。此记录可直接作为 P0-02 的 RED；候选需让同一配置下首页返回 200，并保留其余卡内用例。
