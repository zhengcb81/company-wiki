# 进度

## 2026-11-09 计划形成

- 读取三个 Dashboard owner handoff，共 13 项反馈。分别安排独立 agent 核对代码、Git 版本和原回执，总控归总责任、依赖及验收。
- 只读查询三个 owner 远端主线。确认本地旧 CWP master、FF 本地已并接口和 RF 候选的发布状态各不相同。
- 采用上一轮隔离验证。CWP 基础浏览三提交叠在当前主线，15 项通过。原文流式兼容性观察中，两条读取路径均按当前主线语义报告实际策略指纹。
- 记录阿里六路线与 E12 的不同故障。更正 MDB 成功报告误用失败尝试登记命令，保留成功发布所需原生证据的审计。
- CWP 本地只读探针复现 HK FY2026 原件已登记但历史市场事实为空。FF 只读代码检查定位缺键/null 分支差异，以及 Dashboard 的 reconcile 漏传非默认配置。均分派到实际责任层。
- 当前已完成规划。下一步为 CWP 基础浏览隔离候选，以及 FF/RF 各自的主线发布范围复核。此轮执行范围是只读核查与本独立计划目录。

## 2026-11-09 启动 P1

- CWP 远端核对 `5e4bc087b`。隔离 worktree 挑入 G-CWP-01 的三提交，暂为 `fcceba302`，净新增 5 个预期文件。独审核对实际 CLI、版本重开和 Dashboard 消费。
- FF owner 已核实 `bf7e1dab` 远端和 `154c292c` 的窄快进候选，复查中断和幂等绑定；RF owner 已核实 `90c562ac` 远端，开始最小公开端口移植。
- 独审复现深 stdin、深 snapshot 和无效根相对定位三个反例。CWP 用共享 JSON 及定位工具修复，保持原文实际验真在 Reader。34 项浏览与复用组合、Ruff、469 源文件 mypy 和正常提交钩子通过。精确候选为 `e2a448cc902c1e5f4e49ca02e6ba8515f25331df`。
- Dashboard 真实 adapter 的语言筛选当前发标量，CWP /1 公开合同使用列表。由 Dashboard 写域加回归并转换。该适配缺口与已知 FF 非默认 connector 恢复配置分别测试。
- FF 实测旧并发提交双绑定和半写指针永久 busy，开始用实际中断和跨进程测试收口。RF 的作业首组 33 项通过，正按主线原生捕获时间语义对齐目录夹具。
- CWP 精确候选独审 59 项通过，远端候选运行 [42607965033](https://github.com/zhengcb81/company-wiki/actions/runs/42607965033)。正常 pre-push 18 项通过。
- Dashboard 本地消费基线 `17da5241` 领先实际远端 `main ced8b88` 110 个提交。远端具基础 CWP adapter，缺 FF job adapter。两处兼容修改在单独 Dashboard 工作树提交，组合固定实际消费基线。整段 Dashboard 历史另归其发布计划。
- FF 发现 companion 重设调用截止时间，将与前一阶段复用 FF owner 同一 deadline。原七提交含机器部署记录，正式候选只取可发布代码、合同和测试。RF 检查旧 B34 对 CWP 私有文件和已移除校验函数的依赖，保留源证据真实性，转接现主线公开合同。

### 第一批 CWP 已发布

- `e2a448cc902c1e5f4e49ca02e6ba8515f25331df` 的 [候选 CI](https://github.com/zhengcb81/company-wiki/actions/runs/42607965033) 通过。独审复跑 59 项。远端 `master` 已从 `5e4bc087b` 正常快进，二次快速钩子 18 项通过。源码增量仅基础浏览接口、合同测试和原交接，两个浏览 /1 公开协议可供 D00 验收。
- Dashboard 适配器候选 `4b30e1d9` 和 `8e3231c3` 分别转换基础语言筛选列表、给 FF reconcile 传同一 connector。相邻回归 72 项通过。临时合成目录经真实 CWP 命令验证语言筛选、空结果、原件重开及 SHA。候选固定在 Dashboard 自己的本地消费基线上。
- FF 第一版最小候选 `57351d00` 的作者定向 98 项、Windows 组合 902 项、Ubuntu 51 项通过。真实 FF/CWP CLI 用临时目录验证零下载的复用及只读恢复。独审又实证 ensure 无回执被当已知零开销、未知 reconcile 无结果仍允许 retry，以及伴随采集超过实际请求 deadline。主线等待同一 FF owner 根修后的候选。
- RF Job `ff1c69e0` 已提交在独立 RF 候选，33 项协议与 2 项真实公开 CLI 端到端通过。通过受控公开来源进程执行实际 RF 源准备、计算和发布，覆盖幂等重放及同长度原件篡改拒绝。目录候选继续收口。
- CWP `master` 的同代码复跑 [42609275965](https://github.com/zhengcb81/company-wiki/actions/runs/42609275965) 也已通过。PWF 第一批发布提交为 `360d6f90e`。
- FF 和 RF 首版公开候选 [FF CI](https://github.com/zhengcb81/filing-fetch/actions/runs/42608856713) 与 [RF CI](https://github.com/zhengcb81/revenue-forecast/actions/runs/42609678121) 均通过。独审以真实双进程复现 per-job 死锁接管会使同一作业两次执行，且缺采集回执被误记为已知零费。两边保留独立候选并按 owner 收口恢复及实际费用。
- RF 独审实际退出复现报告目录锁永久 `catalog_busy`，实际短写复现 live JSONL 半行导致旧报告不可读。目录修复限定在事务机制，以进程退出释放和失败后原目录可读验收。

### FF 作业已发布

- FF 修订 `7d8392eb98c50a6d6d27d06d9d7fabee913fe484` 含 10 个 FF 文件。Windows 最终专项 80 项、Ubuntu 66 项，二轮独立复验 68 项及 6 个子测通过，精确 [候选 CI](https://github.com/zhengcb81/filing-fetch/actions/runs/42610817541) 通过。正常快进已核对远端 `main`，发布时快速检查 11 项通过。
- 真实进程复验覆盖接管锁、一份作业一次执行、复用旧作业 ID、收据丢失保持 unknown、只读核对查无原件时不重新派发，以及电话会独立获取和共同截止时间。切换正式部署前让旧 writer 完成，同一 jobs-dir 原有数据保留。
- RF 在候选追加锁内 fresh read、保留未知费用、目录 OS 锁与原子提交。修复首轮定向 23 项已通过，尚在加固 job ID 和有效零费恢复的正反例后复验。

### RF 作业和目录已发布

- 用已发布的 CWP 与 FF 实际公开命令完成隔离中断复验。一份财报，一个原始尝试，进程退出后只读核对为同 SHA 的复用。结果记录零下载，历史费用仍为 unknown。FF `main` 同代码 [CI 复跑](https://github.com/zhengcb81/filing-fetch/actions/runs/42611189773) 通过。
- RF 三提交为 `ff1c69e0`、`bdef9fd3`、`cd24976a958bc2abee841a592691268b45b117ee`，相对远端基线只涉及 38 路径。保留 D4 和原引擎，发布 v1 作业、托管目录读取和原生登记端口。
- RF 48 项定向故障回归、本机标准 735 项及 36 个子测通过。独审在精确归档复验 36 项，Windows 跳过 1 项符号链接能力用例。候选 [CI](https://github.com/zhengcb81/revenue-forecast/actions/runs/42612095973) 通过，远端 `main` 已从 `90c562ac` 快进至上述确切修订。实际并线的短钩子 12 项通过。
- RF 的目录锁和作业锁复用 owner 文件锁，提交在锁内读取并原子替换。短写保留旧报告。单件输入资源限额继续生效，目录总量独立处理。付费潜力来源缺回执时保持未知，支持只读核对及已验证的安全恢复。
- Dashboard 两处适配修订的四文件增量通过独立只读复核。组合验收使用本地消费基线 `17da5241` 加 `4b30e1d9`、`8e3231c319b0c845514d7a40036f8800795cf4f0`，按三个 owner 正式发布版本接线。

### P1 Dashboard 组合验收通过

- RF `main` 的精确代码 [CI 复跑](https://github.com/zhengcb81/revenue-forecast/actions/runs/42612362689) 通过。三个 owner 的代码 pin 分别为 CWP `e2a448cc902c1e5f4e49ca02e6ba8515f25331df`、FF `7d8392eb98c50a6d6d27d06d9d7fabee913fe484`、RF `cd24976a958bc2abee841a592691268b45b117ee`。
- 在独立临时数据根由实际 Dashboard factory 构造 owner adapters，运行真实 BFF 路由和三个 owner 的公开 CLI。CWP 使用既有双根合成财报夹具，验证语言筛选、空结果、精确版本重开及缓冲读取的原件 SHA。FF 经 Dashboard adapter 提交、复用和幂等重放。实际退出子进程使另一份作业进入 unknown，随后以同一非默认 connector 做只读 reconcile。真实 job HTTP 状态与 owner 一致，原件 SHA 相同、mtime 保留、零下载，未知费用保持。
- RF 在临时托管目录登记自己的合成合格报告夹具。实际 BFF 的报告列表、精确 ReportView 结果 SHA 和公开 Job status 均核对通过。单独的 RF 真实 CLI 测试覆盖受控来源到计算与发布。本次组合的身份及数据是控制样本，真实 MDB 入册、阿里来源和付费 RF 均留在 P2 或后续计划。
- 首轮在沙箱中未返回，已停止自有测试进程并查无遗留命名临时目录。随后用白名单环境、阶段输出及堆栈诊断在宿主运行，通过并确认测试目录已移除。组合证据限于本批接口，流式原文、canonical 证明、Range 仍按后续批次处理。
- Dashboard 两个适配器提交留在自己的消费候选，供 D00 独立接收。远端 Dashboard `main` 的依赖版本另行发布，保持 110 提交的原有历史范围与本批三仓 owner 并线分开。

## 2026-11-09 P2：跨市场和 MDB 入册

- CWP 与 FF 的 P2 隔离修改完成独立复核；阿里/B 站真实 HKEX 原件正向复用与期次/市场负例均通过。RF 初版 importer 45 项定向回归通过，独审确认 per-job 并发竞态修复、失败清理、SourceExport contract 和 public DTO 子进程测试通过。
- MDB 原始 job `rfjob-20261108-eb9f2a3ed336` 的 job/input/result strict hash 已重算匹配，关键 JSON 孤立 surrogate 数为 0；源阶段明确 reused_existing、0 download，compute/publication 成功。公开 `list-reports` 入册前返回 0 项，catalog revision `a2ae0e7179f9d76b47bc81788e1501ede2da25efb6a59946748556b87c295a3d`。
- 首次真实 RF CLI 安全拒绝且未改目录，暴露 importer 对 `source-preparation-result/1` 添加了不存在的顶层 `status=source_candidate` 先决条件。真实状态在 `filing_fetch.status`。首轮修复后回归发现 retained attempt validator 仍重复错误判断，4 项用例失败；已同时修正两个校验点，并移除 fixture 中不真实的顶层状态。
- 修复后的 RF importer 定向回归 **45 passed**，Ruff、`git diff --check` 通过；独立审查确认实际 DTO 修正、per-job 并发锁和失败清理没有 stop-ship。随后通过 RF 公共 `import-rf-job` 首次登记 MDB 成功报告，并用公开目录命令重放为 `already_registered`，两次均 `forecast_executions=0`。
- RF 公开只读回读确认 MDB listing 总数 1，报告 `validated`、作业 `complete`、attempt `succeeded`，entity/listing、源/input/result SHA 一致。回读收据为 `validation/mdb-rf-job-readback.json`。报告仍明确显示 1 条 partial 且无 locator 的 citation 和 10 条 quality gaps，因此只签收入册/可回读/哈希一致，不签“证据毫无缺口”。
- CWP/FF P2 owner 改动分别完成独立审查、定向测试及阿里/B 站真实 HKEX 原件 E2E。E2E 正例复用原件且零下载，错误市场、期次、表单、来源证券及 as-of 均拒绝；详细原件 SHA、issuer-link 证据、命令结果见 `validation/p2_cross_market_e2e_receipt.json` 和 `validation/evidence/`。生产 CWP snapshot 缺 LEI/ISIN，故通用算法完成但真实部署的跨市场自动联结覆盖仍开放。
- 清理本轮 RF pytest 临时目录及两份临时部署配置、调试日志和 `__pycache__`；保留必要的无路径回执和公开证据样本。提交前代码只在三个 owner 隔离 worktree 候选分支。
- 最终跨 owner 定向复跑：CWP 70、FF 36、RF 45 项通过。测试启动时两次临时路径设置暴露环境问题：第一轮 `--basetemp` 的父目录未创建，`tmp_path` 初始化失败；显式载入 `pytest-asyncio` 后，稍长的 basetemp 被 Windows 路径防护搬到更长的沙箱目录，CWP 文件锁相关用例因此失败。改用 41 字符短路径后同一 CWP 套件 70/70 通过；不是产品代码回归。相关临时目录已清理，项目测试目录恢复。
- 对跨市场数据根因作了额外官方源核对（只读、未改生产数据）：CWP refresh 当前不消费 HKEX ISIN 专项表；HKEX 公布 HKEX 指派和其他 NNA 指派两种证券 ISIN 表。GLEIF 公开 API 和 ISIN→LEI 文件适合做通用补强，但官方说明当前文件覆盖参与早期 NNA 的新发 ISIN、legacy 覆盖仍属后续计划，且映射列表未提供 CIK→LEI 文件。结论是只加入 HKEX ISIN / GLEIF 不足以证明 US CIK 与全部 HK/CN 挂牌贯通；P2 继续开放，下一步改由 CWP 为有官方来源证据的 issuer/listing 关系定义通用 owner 合同，FF 再消费该公开合同。详细来源及不使用名称猜测的实施边界见 `findings.md` 与 `task_plan.md`。
- 2026-11-09 收尾时的 owner 分支快照（历史记录，已由下方 2026-11-10 更新取代）：CWP `79ebd33f1064b14950ef308d1695bcebd58be676`、FF `58627a66e6c9603f836aaea20b6924a7dd8aa14d`、RF `b005a179280ee19695578bdba9427b4dd44cdd73`。当时固定 push fast-gates 通过，远端完整 CI 尚待确认。

## 2026-11-10 P2 实施更新

- CWP 候选提交 `e3b9a9219cb0c9e48ea8f73c21ff028880564463` 已推送至 `codex/dashboard-p2-cwp-market-20261109`；FF 候选 `f65e6ca75fbce0616e65870f0aea78b793ef883c` 已推送至 `codex/dashboard-p2-ff-market-20261109`。两仓只改各自 owner 范围，未并入主线。push fast-gate 分别 18、11 项通过；完整远端 CI 仍未确认。
- CWP 修复跨模块私有身份方法调用：CompanySourceIndex、SourceVersionReader、local_reconcile 现在都经 SourceResolver 的公开 `match_source_identity` 契约。独立审查先发现“只有 issuer_link_id 会错误匹配”的 fail-open；实现改为 `incomplete` 并加回归，最终复审通过。
- CWP 定向测试 127 passed；470 个源文件 mypy、Ruff、`git diff --check` 通过。SEC 20-F 的公开关系登记链路经 CanonicalSourceWriter 与 SourceCatalog 集成测试验证：登记出的 HK/US 挂牌、源 SHA 与已验证原件一致。FF 跨市场 11 项与 M3 兼容 21 项通过；FF 独立审查通过。FF 完整本地套件剩余 8 个失败已在精确基线复现，属既有失败，本次 P2 定向测试不受影响。
- CWP/FF 候选提交后，重新运行真实原件端到端脚本：阿里 FY2025 HKEX 年报 SHA `c7806bf5da28032e1b15dbe9a334011d65f5d69efe3bf11a9d212f64f07ca9b2` 与 B 站 FY2022 HKEX 年报 SHA `712e23dc04fb7efa3a4d31b839b08eaf6ff92ea1d4c89f6458ace095b8bd24cf` 均在隔离快照完成跨市场复用；来源市场、证券、报告期、文种、as-of 保持准确，provider 未启动，下载数为 0，生产安全证券快照未改。测试结束后删除了本轮临时取得的官方 PDF 和隔离目录，源公司目录原件未改。
- MDB 继续只有 1 条既有成功报告，RF 公开 list/get/run/attempt 回读一致；本次没有重跑预测、重复入册或写 RF canonical root。报告仍保留 1 条 partial citation（缺 locator）和 10 条质量缺口。
- **剩余阻塞**：正式 CWP 身份快照还缺普遍、可追溯的跨市场 issuer-link 来源数据。SEC 20-F 证明路径已进入 CWP owner 代码，但真实 E2E 使用隔离快照，不能据此宣称部署自动关联已完成。下一步先接通通用的权威关系来源/刷新流程，再用实际部署 cache-only 验阿里、B 站和歧义负例；P2 保持 `in_progress`。本节覆盖旧的 2026-11-09 候选提交状态记录。
