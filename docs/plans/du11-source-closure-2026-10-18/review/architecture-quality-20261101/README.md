# 全模块代码质量审查 — 2026-11-01

**以下为2026-11-01原始审查快照，保留当时的“未实施/暂停”语境；当前状态见[逐项核对](implementation-results/checklist-verification-20261102/checklist.md)和主CURRENT_STATUS。** 当前主线不能宣称“已充分解耦、充分泛化、旧门禁全部清净”。主架构方向正确，来源虚拟化和正式 v2 消费链已有效建立；薄弱点集中在阅读准入、缓存依赖、存储/查询规模耦合、旧维护入口及测试本身。

本次用户请求是审查。ROOT 联合三个独立审查 agent 检查来源阅读、存储 Worker、公开消费边界，随后核对当前源码、最小反例并合并重复项。没有启动公司循环、修改产品代码、原件/配置/数据库、调用模型、下载资料或清理历史产物。下列优先级是整改顺序，不能改写上一轮 R4 的六项 P2 和既有封存。

## 基线与覆盖

- CWP 审查 HEAD `d38613bc926e6c95c9009971576af81978a59234`，产品 runtime `7e10973e`；外来 `.githooks/pre-push` mode-only 保留。
- 当前 `src/company_wiki` **408 个 Python 文件**做 AST 语法/结构清单，零语法错误；不是 408 文件逐行功能验收。SourceCatalog 204、automation 61、document_normalization 27、document_understanding 73、parser_adapters 4、source_contract 12、包根 27。
- 详读和反例覆盖：source reader / register / export、当前 selector 和 operating assessment、摘要/版本/缓存、CAS、Worker 调度/预算、采集边界、旧工具/控制面与架构测试。FF/RF/StockWiki 只审当前 CWP adapter，不代表兄弟仓整仓审计。
- PDF/OCR 每种算法、全文检索相关性、全部 provider 和历史 writer 未逐行/逐输入证明；本轮没有真实 PDF/模型 E2E 或性能基准。几何/归属的现有未闭合事项仍在主 PWF。
- CodeGraph 帮助定位；索引含 `.planning` 历史副本，并漏掉部分当前边，不能将“无 callers”独自作为死代码证明。只把当前树源码和实际入口列为事实。
- [来源阅读报告](source-reading.md)、[存储 Worker 报告](storage-worker.md)、[消费边界报告](consumer-boundaries.md)给出逐项路径、行号、触发条件和反控。ROOT 的[可复现小探针](root_audit_probe.py)与[观察结果](root_evidence.json)只使用临时合成文件、纯函数和两个 `--help`，临时目录已删除。

## 合并后的问题清单

共 **14 项：1 个 P1、8 个 P2、5 个 P3**。P1 表示应优先修的核心召回缺口，并非已证明某家公司财务金额错误；P2 中涉及损坏/并发/库规模的项已确认代码路径，但没有伪造生产损失或性能百分比。

| ID | 优先级 | 当前问题与证据 | 所属责任 / 状态 |
|---|---|---|---|
| Q01 | P1 | 陌生业务完整陈述被有限语法词表否决：`Our vessels transport...` / `本公司经营铁路运输业务。` 不准入，换成 `are transporting` 却准入 | CWP 阅读 owner；SR-01，真实纯 owner→admission 已复现 |
| Q02 | P2 | 手写阅读指纹漏 antecedent、parent composition、route signals、strategy binding；相应代码改变可不改变 decision 指纹 | CWP reading recipe；SR-02，指纹反例已复现，未证明生产 stale-cache 命中 |
| Q03 | P2 | 精确公司查询先枚举全库同文种；20,000 条时，即使已找到目标也报候选预算耗尽 | CWP 候选投影/reader；SW-01，19,999/20,000 边界纯函数确认 |
| Q04 | P2 | Worker 每轮轮询重扫共享对象树，约 0.05 秒休眠；将其他写者造成的共享库增长算到本 run | CWP 存储计量/AUTO；SW-02，调用链确认，未测吞吐损失 |
| Q05 | P2 | legacy prune 仅按非空 parser_name 即可构造全范围 DELETE，未强制退役/当前引用保护 | CWP 存储生命周期；SW-03，SQL 条件已复现，未执行删除 |
| Q06 | P2 | CAS `put` 验证现存对象时无界 `read_bytes()`，正常 `read` 却有 expected_size+1 上限 | CWP CAS；SW-04，损坏大对象路径确认，未制造 OOM |
| Q07 | P2 | 两个旧维护工具仍可直接启动：固定机器目录复制、按文件名跳过；默认“中微公司”的清理可原地写衍生文档 | CWP legacy CLI；ROOT-01，下方详述；只执行 help |
| Q08 | P2 | 架构检查依赖字符串和整文件白名单，漏 qualified/相对 import 与 `__init__`，注释反而误报；旧检查也不在当前 fast CI 执行集中 | CWP 测试 owner；CB-01 + ROOT 小探针；不是“当前 CI 跑了恒真函数” |
| Q09 | P2 | StockWiki v2 transport 全量缓冲 stdout/stderr 后才检查 stdout 上限，stderr 无上限 | **StockWiki** transport；CB-02，属于有限跨仓边界发现，不在 CWP 重写子进程服务 |
| Q10 | P3 | 纯 SourceExport 合同依赖具体 SourceVersionReader，writer 又通过高层 reader 组装返回值 | CWP contract/登记 owner；SW-05，明确反向依赖和包循环 |
| Q11 | P3 | 同次已读取的不可变 bytes 在进程内多处重新 SHA；未封装可信 owner 结果使消费者自保 | CWP verified-read 合同；SW-06，不能直接删除跨时间/跨进程的复核 |
| Q12 | P3 | `_candidates` 669 行、`_prose_reading_packages` 402 行，原文组织/关系/归属/准入/预算诊断集中，修改容易互相牵连 | CWP 阅读组合层；SR-03，维护风险而非按行数判 bug |
| Q13 | P3 | reader CLI 将缺参数、非法 hash、配置/存储故障统称 `reader_unavailable` | CWP 公开传输；CB-03，诊断分类问题，不是静默成功 |
| Q14 | P3 | 显式 v2 dry-shadow 仍需两轮零差异；旧 activation/cohort/policy CLI 与历史状态机保留在正常控制面 | CWP 兼容/迁移控制面；ROOT-02，下方详述；正常 steady 读取未被拦 |

### ROOT-01：旧工具并未全部退役，测试枚举也漏了它们

`scripts/copy_docs.py:15–16` 写死用户 Dropbox/Projects；`:49–78` 用物理公司目录名匹配、仅凭目标文件名存在跳过、直接 `shutil.copy2`，不走统一登记/hash/source manifest。这会让同名不同内容被忽略，也会制造原件的另一份未登记复制；尚未测本机实际重复规模。

`scripts/clean_watermarks.py:78–95` 默认原地 `open(..., 'w')` 改文件；`:138` 默认真实公司中微；`:147` 直接拼接 `companies/.../extracts/research`。本轮没运行清理，不把修改衍生 markdown 说成删除原始 PDF。

两者均无显式 retirement guard；宿主 Python 正常执行 `--help` 返回 0，不需 `-S`，说明不能依赖 `scripts/sitecustomize.py` 隐式加载来宣称已封闭。`tests/unit/test_writer_freeze.py:90,106` 的检测正则只识别 `.write_text/.unlink/os.replace`，恰好漏掉 `copy2` 和普通 open-write。

根修是**删除/退役不再需要的入口，确有用途则成为统一 owner 的薄调用**，而不是增加第三套环境许可。硬路径/默认公司不能进入通用产品；测试固定公司样本、配置实体别名、交易所/document-kind 规则则不应一概禁止。已有 `auto_synthesis/auto_discover` 等研究 CLI 已显式冻结，不能将其 prompt 或公司样例误报成当前研究 writer。

### ROOT-02：仍残留的旧门禁，影响范围必须说清楚

- `source_catalog/scanner.py:2108–2116` 在 `dry_run and v2_scan_shadow` 时要求 `zero_diff_rounds>=2`，且只是将调用者整数转换为若干空 diff 数组。ROOT AST 提取实际函数，在不建库/不扫描文件下确认 None/1 被拒，2 才到达 preview。它增加迁移时期的调用仪式，不能证明两个真实独立回合发生过。
- `service.py:154–170` 的全根 `scan()` 仍从旧 snapshot 决定 v2；无 snapshot/steady schema 2 返回 v1，损坏 snapshot 静默退回 v1。**当前定点 register 不走此路**（已有 `test_registration_service_uses_configured_reader_without_old_rollout_scan`），SourceVersionReader 默认 steady，所以不得报告“正常注册/复用仍等 canary”。
- `cli.py:513–555,1137–1209` 仍提供 activation epoch/cohort/policy hash/reason 和 runtime-policy apply。reviewer 已可选，不是人工许可；属于可精简的历史运维表面。迁移/回放解码可保留，当前入口应不要求用户理解 rollout 状态。
- 包根 `deployment.py/scheduler.py/proposal.py` 还保留早期 SHADOW/CANARY/签收模型；当前查到的 canonical 调用链没有用它们，不能单凭名字说正在阻断。删除前只核对真实 import/CLI/必要历史重放责任，不新增人工迁移批准。

## 解耦与泛化：应如何判断

已经做对：物理根主要封在 CWP；RF 正式来源准备和 StockWiki v2 使用 pathless ID/hash；FF v2 通过统一 owner；PDF 前端、类型策略与共享阅读引擎有责任分工；prepared assessment 已被多个消费者共享。

尚未充分解耦：底层 DU 指纹知道 automation/source_catalog 细节，SourceExport 合同绑定具体 reader；Worker 做共享存储全树计量；旧工具自己懂物理目录和删除规则。**目录拆分不等于职责拆分**，应让每个事实/状态只有一个决策 owner，其他模块消费结果和诊断。

尚未充分泛化：本轮未在所审当前共享引擎发现“某 ticker/某页必须选”的分支；真正可复现的问题是以有限行业/语法词表否决陌生业务。修法不能只补 vessels、铁路、clinicians，也不能用放宽所有内容、增加配额掩盖。原文可读资格与事件/数字/主体事实证明需要独立表达：未知事实类型仍可保留原话，不可伪升级为收入证据。

## 门禁与检查的具体处置

| 措施 | 建议 | 原因 |
|---|---|---|
| private/public、逐资料/provider 人工授权、prompt 人工签收 | 保持已取消 | 所审主链未发现恢复此类人工限制；不按旧字段名重新发许可 |
| 旧 dry-shadow 两轮、activation/cohort 普通入口、无效检查 helper | 移出正常流程/清理 | 当前 steady 不依赖；恒真 helper 没调用价值；保留必要历史格式解码即可 |
| 重复全树空间扫描、同次可信字节重复 hash、重复事实判定 | 合并到所属 owner | 消除重复工作和错误归属；跨边界校验不一起删除 |
| 按有限词典拒绝正常陌生业务描述 | 从准入否决中移除这一条件 | 已有反例；保留模板、问题句、财务碎片及引用归属边界 |
| source ID/hash、真实原件字节、单位/期间/as-of、引用定位 | 保留，各层只做自己那部分 | 防止错公司、错期、数字幻觉和虚假引用，不是权限 |
| 原件不可变、写入幂等、租约/fencing、原子提交、崩溃恢复 | 保留 | 防重下载/重复付费/丢工作，尤其并发场景 |
| 预算/超时/字节上限 | 保留，修归属和执行位置 | 配置已有授权；成本真实计量，不靠每次新批准 |
| 不同进程的接收字节 hash；稍后重新打开源文件的 SHA | 保留 | 与同进程同一次 bytes 重算不同，保护传输与时序变化 |
| 各小步骤人工签收/整仓全量复跑 | 不增加 | 改为责任层正反例、受影响集成与现有大节点真实 E2E/独审 |

## 下一步与完成标准

详细实施顺序见 [implementation.md](implementation.md)。这是原主 PWF 质量收尾的补充，不是新公司循环或外包计划；审查完成不等于修复完成。Q01/Q02 与既有 R4 来源遗漏/归属工作一起优先根修；查询/空间/CAS/维护生命周期在原 owner 内并行概念拆分、顺序集成；纯 P3 清理不应阻挡有价值的真实验收。

本轮只交付审查与细则、正常文档提交推送。主线产品实施继续等待用户恢复；既有八家公司、三家 clean、经济验证与历史未完成事项保持。文档核对不冒用旧 CI 绿作为本次未实施修复通过。

交接前由消费边界审查 agent 独立核对本汇总、细则和主 PWF：14项归并/未实施状态一致，旧入口范围无扩大。其发现一处探针标签将“未列入禁止表的模块”误称 qualified-import 漏检；已更名并重跑保留观察，真正禁止模块 `scripts.auto_synthesis` 的限定导入漏检另有独立反例。JSON、ID计数、文档链接、脚本语法及diff whitespace核对通过；未运行产品回归。
