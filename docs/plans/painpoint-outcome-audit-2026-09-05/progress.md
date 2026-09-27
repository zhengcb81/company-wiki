# 审计进度

## 2026-09-27：ensure/close-gap 进程边界 pathless opt-in 首轮完成

- CWP 隔离工作树新增 `--source-ref-v2` operation 结果投影，`ensure`/`close-gap` 输出 schema 1.0；成功 candidate 由精确 SourceRef 2.0 生成，pathless gap 带 request/gap/hash，另保留授权 close-gap 所需的 `policy_hash`。CLI projector 错误结构化返回，未带 flag 的旧输出不变。
- FF 隔离工作树 exact 无下载仍走 DB-only query；latest 和授权下载走 pathless ensure，授权 gap 后走 pathless close-gap。消费端拒绝未知版本、路径字段、SourceRef/candidate/hash 不匹配、非法事件数、非 `not_detected` review。gap request_id 绑定与授权校验保留。
- TDD/回归：CWP operation/reader/CLI/close-gap 相关 **52 passed**，FF `tests/` **385 passed、14 skipped、78 subtests**，独立 FF→CWP CLI E2E **1 passed**；FF Ruff、Mypy、`git diff --check` 与 CWP Ruff、`git diff --check` 通过；复杂度 31≤34。全量 FF 测试另有 `test_spy_log` UnicodeDecodeError warning，不作为断言通过。
- **仍非 C.local 签收**：latest provider 的实际隔离刷新、CWP 实际 close-gap CLI 下载及重试幂等、OS 级读次数、RF/StockWiki/default entrypoint/完整测试区恢复未验；这轮没有真实网络或生产写入。
- 清理异常：本轮唯一 `pytest-*` 输出根此前已按 run-id 清点且无 reparse，但访问控制仅列 SYSTEM/Administrators；递归删除与 `icacls /reset` 均 Access denied。mypy cache 和空 parent 已清除。保持所有其余隔离目录不动，后续需由本机管理员处理测试根 ACL 后删除，或在另一个可清理的短路径重跑 E2E 并验证回基线。

## 2026-09-27：最终读取回执版本化与旧收据拒绝测试

- CWP binary `source-read` receipt 单独升级为 schema `2.1`，携带原文 SHA 验证后读取到的 review snapshot；`SourceRef`/query candidate 仍为 `2.0`。RF transport 和 final record builder 严格校验 `2.1`，新增把成功回执改成旧 `2.0` 后必须拒绝的回归用例。
- 验证：CWP reader + CLI 契约 32 passed；RF transport/builder/preparation + FF→CWP→RF 真实 E2E 36 passed、1 skipped；两仓 Ruff、RF 三源码文件 Mypy、两仓 `git diff --check` 全绿。首次 pytest 默认 Temp 受沙箱拒绝；改用授权隔离 basetemp 后通过。仅验证隔离 opt-in，不等于默认入口或 StockWiki 生产路由已切。

## 2026-09-27：TDD 边界复核与单用户资料湖简化

- 用户要求全面检查多余设置。本轮 CodeGraph 对 559 个 Python 文件做结构盘点，核对 83 个 `source_catalog` 文件以及 Worker/调度、全文转换、章节副本、摘要、清理与 legacy 研究入口的关键调用和读写；S1–S10 简化项、状态和待测量项已写入 [R4 实施卡](r4-data-lake-priority-rollout-2026-09-27.md#全仓结构审查后的进一步简化2026-09-27-增量)。这是结构与热点审查，未声称逐行看完全部文件。R4 主计划/测试矩阵中原来每阶段 DR→VR→AR 三次签字和每级 cohort 停审已改为关键节点一份综合结果包，局部用 TDD 与相邻合同测试；生产删除、付费联网、Worker 启动仍核实际动作。
- 额外只读审查核实 CI 在每个 Python 矩阵重复 unit/contract/full coverage/6 组 canary，`--cov ... || true` 与 CLI smoke 的 `|| true` 可掩盖真实失败；`pyproject.toml` 已有可选解析/download extras，`requirements.txt` 和 CI 却默认安装全套。StockWiki 当前 `company-wiki` provider 明确 disabled，现行 Tavily fallback 不动；将来启用 v2 后须显式选择来源模式，失效不能悄悄排 Tavily。S8 可独立减法，S9 等 C.local 激活，S10 先量安装成本；均不增加小步审核门。
- 空间基线纠正：2026-09-26 收据证明旧 46.266 GiB SQLite 主库已退役并实测同卷净释放 37.630 GiB，D0 盘点当前三自有目录 39.744 GiB；本轮主库只读 stat 3,055,800,320 B。原计划表中实施前 46 GiB 快照不可再当待删现况。保留压缩备份 5.773 GiB、退休归档 4.850 GiB、raw 23.460 GiB、derived 2.632 GiB，均需各自引用/保留关系审查后才能计可回收；重复 raw 候选理论差额仅 98,845,393 B，尚非删除资格。
- 本轮再次核对空间调查：旧库约 2720 万 span，其中 table cell/空 `raw_text` 比例在小样本中很高；目前没有全库精确表/索引占比。R4 卡已把“新 DAG 零新增全量旧式 span/MD、量每份新增字节”放在派生清理之前，并写出最终五个生产 owner。D0 的 `future_lake` 一件 545 B 原文已纠正此前“只有 README”的过时描述；它尚不构成原生第四根真实覆盖。
- 只读量测发现 3,500 个已规范化不同文档里仅 22 个有当前 prompt-injection review 收据；S7 已加入自动扫描干净的**实际将发给模型的字节**并写绑定收据，命中/异常才需人工的方案。首轮三仓 E2E 暴露 FF legacy resolve + RF final open 两次全文读取；隔离 CWP 随后新增 DB-only 候选投影、FF 显式 v2 opt-in 改走查询。FF↔CWP 真实集成 11/11 及三仓真实 E2E 已绿，坏字节仍由 RF 最终打开拒绝。旧 FF 默认行为、StockWiki 正式消费、OS 级 I/O 计数和生产路由切换留待 C.local 大节点签收。
- 候选 `prompt_injection_review` 在 query→open 间撤回的反例先红：CWP CLI 成功回执缺 `review`，RF 会沿用候选的旧状态。隔离 CWP 补验真后 review snapshot、隔离 RF 严格收据与最终状态后，CWP reader/query/真实字节 34 passed；RF 受影响 6 文件 36 passed，真实三仓 E2E 含候选后撤回审查与原文同尺寸篡改两负例均绿。Ruff、RF Mypy、两仓 diff-check 绿；仍只在隔离 opt-in，默认生产路由未切。
- 隔离跨仓回归收口：FF 全套 379 passed/13 skipped/78 subtests（1 条既有测试线程解码 warning），RF v2 定向 81 passed，CWP reader/query/真实字节 33 passed；三方 Ruff/Mypy（适用仓）/diff-check 绿。真实三仓 E2E 含根标签 false、零下载、坏源字节最终拒绝及测试文件恢复。三仓均未提交/合并；FF 的 `latest_as_of`/授权下载仍经旧 ensure/resolve，`detected_and_ignored` v2 保守 hold，C.local 结果包必须分别核这些请求型态。
- 复核新增两个 LLM 摘要负例：规范化工件被改写仍外发、旧根 active 位置遮蔽当前根同 SHA 副本；两项先红后绿。外发前现核工件实际 SHA，查询以存在当前已配置 active 副本为准；GP003 8 passed。CWP 单次 binary reader CLI 收据新增 DB-only `manifest`，先红后 5 passed，使 RF 可在一次原文读取中取得当次来源元数据。
- 再给 LLM 增加 normalized 工件 lineage 错配不外发的红测（旧实现会完成一次 LLM 调用），将 LLM/确定性摘要/章节提取统一到同一工件读取器后，GP003 9 项及直接相关五套合同合计 48 passed。旧 FC906a 夹具未按现有 review API 提供 `evidence_payload`，已改为扫描并绑定该测试真实 normalized 工件字节，4 passed。随后只读生产 catalog 发现 4,797/4,984 条旧 normalized 行缺 DB source SHA；已把安全的 frontmatter 兼容要求写入 S2，隔离实现/真实旧工件验证仍在进行，当前不宣称 S2 已可生产切换。
- S2 历史兼容 TDD 后直接相关 75 passed、unit 20 passed；主库 `immutable=1` 每种旧生成器抽一件共 11 件，8 件通过，2 件真实工件 digest 与记录不符、1 件 frontmatter 状态不符，均按预期拒绝。随后生产只读查询又发现 1,469 个文档有两条可读 normalized 工件；双工件只加工一次的 TDD 正在进行，避免 S7 扩大 review 覆盖后重复调用 LLM。
- `config_doctor.py` 原来把 directory 根写死为 Dropbox/future_lake；先红 3 项后改为通用目录根结构/可达性检查，相关 21 passed，仍拒绝重复 ID、未知变量、指向文件的根。SourceExport v2 仅 manifest 的 PDF 原来全文载入并长期保留；16 MiB 测试峰值 33,598,348 B，改为共享读取规则的 streaming `verify_version` 后 2,144,131 B，相关 76 passed、1 skipped，包含两份真实 PDF E2E。上述改动均在隔离 CWP worktree，尚未并入主树。
- 隔离 CWP worktree 的 v2 来源读取新增完整配置指纹、查询/resolve/ensure/二进制 CLI 收据；`policy_2x` 历史 hash 未改。后来跨仓审计指出把该指纹作为消费者硬门槛会让配置根搬家后的旧 SourceRef 失效，违背位置透明，因此当前只把它作为可选一致性检查与审计字段；FF/RF v2 消费者下一轮先红后绿地改为来源候选→最终消费者单次 current-policy open，旧跨仓双 hash 和两次全文读取不得成为最终合同。
- 审查发现导出曾可包装调用者任意提交的 PDF EvidenceSpan；新增伪造 PDF/TXT 红测后，v2 现在只接受对已验 UTF-8 `text/plain` 原字节的精确字符坐标引用，PDF 等仅导出 source manifest。解析器管理的 PDF normalized artifact registry 是后续叙述 G2a 的前置，不用包自身 hash 冒充引用真实性。StockWiki 新 loader 已按同一规则先红后绿，并用临时 catalog 跨进程 scan→query→export→load 真实运行，36 passed。
- 同 SHA 的完整侧车若 URL、财年、provider ID 等声明冲突，以前受 root priority 影响而静默保留胜出项；新增红测后 scanner 持续记录关键字段冲突，正式复用和导出都拒绝不明归属。B05 原有两例因旧测试收据未提供新要求的 source SHA/policy/evidence payload 而失败；只修测试夹具后 B05 16 passed，未放松产品校验。
- 用户明确裁定个人项目取消 `private/public`，全部已配置来源均允许外发。隔离 CWP v2 已用先红后绿测试移除本地 SourceExport 标签拦截、正式复用的根级 `reusable_for_filing` 拦截和 LLM 摘要入口的 `private_user` 否决；仍核来源完整性、状态、报告期、采集证据、审查收据及当前字节 SHA。RootPolicy 3.x 不再强制根标签；隔离配置删去四根的 `privacy_class`。LLM GP003 6 passed、RootPolicy 单测 12 passed；此前自动审批因授权不够明确拒绝过外发改动，用户的后续明确授权已解决该问题。
- CWP v2 reader、export、policy、LLM/B05 合同及两份真实文档 E2E 组合回归 99 passed；首次未提权运行因测试临时目录访问权限报 96 个 setup error，按环境权限重跑后全部通过，非产品失败。隔离配置由 `load_catalog_config` 成功加载四根，均走缺省兼容标签；它不再用于读取或外发决策。
- filing-fetch 隔离分支曾通过 396 passed、13 skipped，真实 FF↔CWP 临时目录 E2E 也验证了策略变化下旧 pin 拒绝/新 pin 可读；RF 隔离分支 v2 19 单测、真实 E2E 1、旧纯回归 31 和旧入口 mock 8 全绿。这些是过渡实现的局部结果，尚未并线，也不代表已达到单次读取/旧路径无关的最终合同；下一轮简化正在 TDD 进行。

## 2026-09-27：抽象读取第一切片按 TDD 推进

- v1/v2 导出、读取、相邻 B 合同及真实字节合并回归：229 passed、1 skipped；新增 v2 发布 CLI 的 3 项调用者测试先因模块不存在红，实施后 3 passed。CLI 只收临时 catalog 的精确 SourceRef 与 EvidenceSpan，不收原文路径，不扫描或下载；成功 stdout 单行 bundle，拒绝 stdout 空且 stderr 单行结构化错误。测试发现 SQLite WAL 只读连接会刷新 -shm 的 mtime；断言仍核其字节和大小、主库/WAL 的完整状态，独立临时测试树结束后恢复，不能将 -shm 时间变化误报为原文写入。
- 跨仓并行：filing-fetch 独立 worktree 的 binary read transport 先红后 13 passed，接线先红后 16 passed；既有无下载相关回归 274 passed、3 skipped，隔离真实 CLI E2E 1 passed（三方 policy_hash 一致、同 SHA 备用副本、零下载）。其 v2 目前显式 opt-in，防止 CWP 新入口未部署时破坏旧 CLI；还不是全面移除旧 resolve/path 字段。StockWiki 独立 worktree 因主树有大量未提交/未跟踪内容，仅新增 v2 独立 loader，首轮 15 failed→15 passed，尚未接旧 source-provider。
- 真实资料门槛首轮：隔离运行星环 2025 年报与三角防务 P06 定增资料，真实原件/侧车先后完整 SHA、大小、mtime、属性一致，临时测试树已恢复；2 passed。星环验证原生侧车查询、正式读取、同 SHA 备用副本回退；P06 验证预览可读但稀疏 capture 拒绝正式复用。第二根只是真实字节的隔离备份，尚不能代表 future_lake 原生接入。
- SourceExport v2 采用先红后绿：导出三例先因缺模块红、随后全绿；strict from_dict 七例先因缺 API 红、随后全绿；重复 JSON key、公共包接口、报告期字段也先红后修。期间又在组合运行中发现循环导入，修复后导出/reader/CLI/真实字节合计 33 passed。v2 目前是可调用的构建器及严格加载器，发布 CLI 与 StockWiki 实际消费仍待下一大节点。
- 查询分页红测证实 1001 条同日非匹配候选会遮住后续真匹配；补带上限的只读 SQL 分页后，新反例及旧 B02 候选测试 31 passed。正式 filing_reuse 另要求显式报告期事实，不再把公告日期当报告期：红灯曾实际打开 PDF，修复后先拒绝。
- 前一切片：跨进程二进制 read/query CLI、按业务身份的本地 query、preview 与正式 filing_reuse 分权、生产形状嵌套配置、as-of SQL 前置裁剪、待修正来源拦截均先记录红灯再补最小实现。该时点相邻合同回归为 98 passed、1 skipped；新增待修正来源红灯为 found、修复后 1 passed。ruff 通过。原有 B05 套件另有两例在未改的 prompt_injection.py 内失败，需基线核对；不能把这两例当本切片绿灯或回归。真实 E2E 与跨仓消费者的后续结果见上方，整体接线仍未完成。
- 已把 red→green→refactor 和“每层单测、相邻合同、关键节点真实 E2E”写入 R4 活动实施卡。CWP 产品修改均在独立 `codex/data-lake-reader` 工作树，不覆盖主工作树的其他未提交改动。
- 先新增 `tests/contract/test_source_version_reader.py` 四个调用者合同测试；初跑在导入 `source_reader` 时红（`ModuleNotFoundError`，0 collected）。随后最小加入路径无关精确版本查询/打开，复跑四项全绿。覆盖 ref 不含 path/root/location、精确 hash/身份、退休或撤权零原文打开、同 SHA 副本缺失/坏字节回退、配置 root 搬家无需重扫、其他版本不得替代。
- 此绿灯只表示隔离夹具的第一切片；跨进程 CLI、一般 `query_local`/preview 权限、真实多根 E2E、消费者接线、独立 B.AR 均未验收。下一步继续先写相应红测试，再实施。

## 2026-09-27：用户目标重排与 RF 主线并线完成

- RF 已签收尾项在隔离候选核对并经定向测试 22 passed、九负例 9/9、真实年报离线跨仓 E2E 5/5；原 RF pre-push 全门绿，远端 `main` 已核对为 `3a69f9c5b6516ebc949d1c95bd50965f9112b7ad`。`fcap` 留历史 `ee0a82bfd`；此前“RF 尚未并线”的段落均为时间点快照。
- 用户把持续实施顺序定为 RF 并线 → CWP 位置透明抽象层 → 叙述/Worker/空间原计划，并要求按层单元、相邻集成和关键真实 E2E 验松耦合。已更新 R4 唯一活动入口、实施卡、本计划及叙述专项当前 Next Step；历史复审 `A.AR=rejected` 仍原样保留，受影响合同做一次增量独立审查。
- CWP 主工作树有其他工位未提交代码、测试和规划文件；本轮只写本目录/叙述专项计划文本，另建独立 `data-lake-reader` 工作树准备产品实现。尚未在本轮修改 CWP 产品代码、生产 catalog/raw、Worker 或空间文件。

## 2026-09-27：本地/远端 Git 实时核对与 RF 未提交候选澄清（只读 + 规划）

- company-wiki 远端 HEAD/master `f39bd5a`、远端 fcap `8665c8c`；本地 fcap `dbe4745` 比远端 master 多 4 个提交，工作树另有 24 tracked 修改和 16 untracked 条目。RF 远端 main/fcap 同为 `ee0a82bfd`，用户澄清新的 RF 工作在本地未提交，暂停后续并线。
- 将 R4 及叙述专项的“等待 RF Git merge”技术前置改为“由 RF owner 固定可复现的候选快照或支线提交、版本化接口合同及当前 dirty 冲突面”；A/B 通用设计可准备，RF 的 C.local 正向 E2E 在候选未冻结时 hold。company-wiki 产品代码和 Worker 仍暂停，不因为远端已有旧 merge 自动恢复。
- 仅执行 Git 只读查询与规划文档修改；未 fetch/pull/merge/push、切分支、修改产品代码或生产资料。具体 SHA 与差异见本目录 findings 顶部。

## 2026-09-27：位置透明优先线路细化（仅计划）

- 用户要求 RF 非主线改动并入后优先实施抽象分层；本轮新增 [R4 优先实施卡](r4-data-lake-priority-rollout-2026-09-27.md)，同步 R4 实施入口/测试矩阵与叙述专项：G0 复用 A 合同审查，C.local 先验基础来源 reader，W5 后 G2a 增验 selected package。所有跨仓消费者业务代码都应从上游原文路径操作迁到版本化 `SourceRef`/`EvidenceRef` 与受控读取；StockWiki SourceExport v1 的路径与 export/evidence ID、标题耦合单列迁移，full sync 不借 C.local 放行。
- 只读调查得到三角防务定增、星环科技年报、微软 10-K、拓尔思招股书等跨根真实样本与完整 catalog SHA；这些尚未由本轮重新哈希，正式隔离复制后必须核原字节、sidecar 和独立 locator。真实修订对/future_lake 原生根仍有明确缺口。
- **未运行**新产品 E2E，未改产品代码/生产 DB/原文/Worker；现存其他未提交产品文件并非本次规划改动。A/B/C.local 仍需当前输入、授权与独立结果，不用历史收据自动签收。
- 独立只读复核纠正四个假放行风险：StockWiki 旧 `--source-root` dry-run 不能证明新 reader；RF `not_reviewed` 拒绝不能替代正向 RevenueSourceRecord；StockWiki 新 evidence ID/标题/候选状态也必须跨路径稳定；基础 C.local 不得等待 W5/G2a。已同步 R4 与叙述计划，旧 v1 兼容和新 SourceExport v2 分名。规划文档链接/尾随空白及已跟踪文件 `git diff --check` 均通过；这不是产品验收。

## 2026-09-12 上午：R4 阶段 A 收口为 v0.4.2、阶段 B 设计三轮复审、A06 首个真实基线

- **阶段 A（合同/基线）**：A07（A.VR）**`accepted_with_findings`**（6×P1/3×P2/2×P3；交付 **22 条负例 VR-N01–N22** + **五值错误模型** `not_found/not_indexed/unavailable/blocked/ambiguous`）；A08（A.AR）**`rejected`**（**117 行逐行映射已产出**：98 行可直连、6 行经 AC 桥接、**13 行无法指派**）；A.DR rev3 `accepted_with_findings`。三份复审**独立命中同一 P0**：
  - **`policy_2x.py` 并非"整体无生产调用者"**：无调用者的只有 **loader**；**`export_policy_2x` 在产**（`cli.py:835 _policy_export_payload` → `:849-851`，由 `:811` ensure / `:831` policy-export / `:1182` **resolve** 调用），其 payload 是 filing-fetch **FC-501 containment / ZR-405 policy_hash 的唯一来源**（`filing_contracts.py:450/461-497`）。
  - → owner 裁定 **R-3 的适用范围收窄为"仅准入 loader"**；导出路径**保持现状**（若要一并收敛，属新裁定 + 跨仓 policy_hash 迁移）。
  - 另两条更正：**`reusable_for_filing` 有"三处活实现"**（`resolver.py` fail-open / `policy.py:67-72` fail-closed / `policy_2x.py:308-312` 经在产导出）；**owner R-4 在现网是惰性的**（四个 root 全部显式声明 `privacy_class: public` → 受影响集合 = 0，其验收只能靠合成配置）；`read_only` 亦为**假保证字段候选**（写轴实由 `kind == 'company_raw'` 决定）。
  - 合同已就地更正为 **v0.4.2**；`boundary-audit` 增加第四类开库者（见下）。
- **阶段 B（位置透明索引/读取）**：设计 **v0.1** → `B.DR` **rejected**（1×P0+7×P1+9×P2+3×P3）→ **v0.1.1** → `B.DR-rev2` **rejected**（round-1 的 20 条中 **7 条闭环**、新增 15 条）→ **v0.1.2**（B05 改为"停止销毁落选值、provenance 存进既有 `metadata_json` 列、无需 `store.py`"；`_handle` 的合格清单入参写死；B06 承载 = `ResolutionEnvelope` 新增 `qualification` 字段；B07 划分"B 可签/不可签"；补读取预算与取消；新增 `B-payload-hash` 必测项；checkpoint 生成器强制 `--reviewed-commit` + 完整性断言）→ **`B.DR-rev3` 复审中**。**产品代码未改动**，实施仍需 owner 批准文件范围。
- **A06 首个真实基线（机制层 D0）**：CI 等价命令实跑 —— **unit 787 passed / 37.5 s**；**contract 1748 passed / 7 skipped / 0 failed / 0 errors / 11 min 47 s**（junit 逐例证据入 run 目录）。7 个 skip 的原文原因已记录，其中一条重要：`test_dbx05_symlink_escape_rejected` 因 **`symlinks not supported on this host`** 跳过 → **symlink 逃逸控制在本机从未执行**（与 owner R-1、A07/L05 负例直接相关）。
- **边界新发现（本目录相关）**：**本机跑"CI 等价测试套件"会打开生产 catalog（只读）** —— `tests/contract/test_lt_uj_real_e2e.py` 硬编码生产路径（`:36/39/40`），其模块级 skipif 在**收集阶段**即连接（`:70-73`），且**不在 CI 的 8 个 `--ignore` 之列**（`.github/workflows/ci.yml:51-59`）。→ **开库者清单第四类**（前三类：22:00 每日任务、推送前 gate、未推送的手动 gate）；`-shm` 在 08:11:45 / 08:13:46 的两次前移即由本次基线运行造成。主库与 `-wal` 全程未变（无逻辑写入）。
- **CI**：revenue #145/#146/#147 全 success（对应提交 `1b4bab4`…`8e3396b`）；wiki #103 success。
- **FC-705 门**：预计 **2026-09-12 22:00** 运行后转 true（last-two = P10（24:00:05）+ P11，均 ≥24h 且零 hit）。GP-009：Daily 6/7（今晚后 7/7）、Weekly 0/2（下次 09-13 04:30）、Monthly 1/1。

## 2026-09-11 夜：R4 阶段 A 首轮设计审查（A.DR **rejected** → v0.2 更正完成）

- **运行目录**：`revenue-forecast/assurance/runs/2026-09-11_r4-phase-a/`（在审计证据目录**之外**，符合 handbook §2.5/§3）。
- **owner 三项批准**：① A 阶段精确 DEV/数据读取许可；② `--help`-only command manifest；③ VR reviewer 指派。据此执行 **52 次 `--help` 探针**（全部 rc=0），把 CLI 表面积从"源码 grep 的 47"更正为 **41 顶层 + 10 嵌套 = 51 节点 / 47 叶子**。**未**越界：产品写入、`--dry-run`、真实数据命令、网络、删除、worker 恢复均未发生。
- **A01–A04 草案 v0.1 送 A.DR** → 独立复审（非作者会话）**verdict = rejected**：**8×P1 / 5×P2 / 3×P3**。复审确认的正向事实：12/12 输入哈希与字节数、三仓 HEAD、root 配置表、51 节点 CLI 结构、checkpoint 产物哈希、跨仓 spawn 引用、仓库/目录边界隔离。记录见 revenue 侧 `reviews/A.DR.json`。
- **P1 实质问题（均已就地更正为 v0.2）**：
  1. `symlink_policy` 被当作"已强制 fail-closed"——实际**只解析、从不读取**（全库 `is_symlink|reparse` 命中 0）＝**假保证字段**；
  2. 冻结的复用链 `reusable_root_kinds → is_canonical → priority` **不存在**：复用只看 `root.kind`（`resolver.py:782-786/933-940`），**显式 `reusable_for_filing: false` 无法关闭复用（fail-open）**；所谓 `priority` 分支其实是字符串字面量（`resolver.py:531`），真实排序在 SQL（`service.py:329/527`、`:643-653`）；
  3. `canonical_write_target` 的"无校验"结论**错误**：校验存在于 `policy_2x.py:49/121-131`，但**该 loader 无生产调用者**，而现行 `config.py` 直接**拒绝该字段** → **两套分叉的 root 准入实现**；
  4. `identify` 被列入只读面——`--refresh` 实为**网络 + 本地写**（`cli.py:1080-1087`、`security_identity.py:1007/348`）；
  5. 命令清单**漏 7 个叶子**（`worker-status/start/resume/pause/stop`、`derived-audit`、`import-portfolio`）——其中 `worker-pause` 正是该契约规则 R3 点名要防的动作；
  6. A01 的子进程面被**严重低估**（真实为 **7 模块 / 12 个 spawn 点**，含 `dayu_cli_adapter`/`adapter_process` 的**外部 provider 边界**），且 F-A01-2 引用了 `company_wiki_source.py` 的 **docstring 文本**当代码证据（已删）；
  7. A04 规则 R4（路径不入身份）与现行 `is_canonical` 选择键（含 `priority`/`root_id`/`relative_path`）**相矛盾** → R4 重述为**目标**并点名残留；
  8. 边界声明被文件系统证据挑战：生产库 `catalog.sqlite3-shm` 在 run 窗口内被写入（21:18:15）——**已归因**（v0.2 定案）：本会话**推送前的强制 gate**（revenue `tools/pre_push_gate.py` 的 real-data 套件对生产 catalog 只读跑 pytest）在 21:18:15 / 21:26:47 / 22:05:03 / 22:10:11 四处开库，另 22:00:02/18 两处为 22:00 每日任务；主库与 `-wal` 全程未变（无逻辑写入）。逐条证据见 revenue 侧 `assurance/runs/2026-09-11_r4-phase-a/boundary-audit.md` §1–§3。v0.1 的"零副作用"快照**未覆盖 `-shm`/`-wal`** → 覆盖盲区已修复；"独立边界观测"仍登记为**操作员动作**（作者不代签）。**同时更正**：v0.1 中"本会话未运行任何会打开 catalog 的代码路径"的更强说法**已撤回**——push 协议本身就会（只读）打开它。
- **v0.2 新增产物**：`inputs.json`（依赖/lockfile 哈希 + schema 常量）、`boundary-audit.md`（shm 证据/受控实验/归因限制）、被动观测脚本与产物（**不开库、不执行 CLI**）、快照覆盖扩展后的 manifest 证据。
- **阻塞项（需 owner/操作员）**：① ~~6 项 owner 裁定~~ → **2026-09-11 当夜已裁定（G2）**：owner 回"按你建议办"，六条全部按建议定案（`symlink_policy` 按假保证字段处置、`reusable_for_filing: false` 必须生效、两套准入实现收敛到生效的 `config.py`、`privacy_class` 缺省改为默认不外发、A04 R6 指派 `identity-enrichment`+`security_identity`、A04 R4 保持目标并登记 9 处整改）→ **A02 据此封版为 root-contract v0.4**；裁定只定方向与登记，未改产品代码。逐条见 revenue 侧 `assurance/runs/2026-09-11_r4-phase-a/owner-rulings-2026-09-11.md`。② 独立边界观测与 reviewer 身份戳记（需操作员）。③ A05/A06 的样本清单与**隔离副本**（生产 catalog **49,677,344,768 B**，禁止行为探针）。
- **边界**：本轮只写文档 + `--help` 探针；未运行产品测试、未改产品代码/配置/DB/任务/worker，未下载/LLM/删除；R4 整体仍 **NOT_IMPLEMENTATION_AUTHORIZED**。

## 2026-09-09 深夜：并发状态核对（V5 完成 / FC-705 门 / R9 批 3 范围修正）

- **Worker v5 独立轨道全部完成**（同仓 `docs/plans/source-catalog-worker-recovery-v5-2026-09-03/`，提交 `6559075`）：V5-0/V5-R/V5-1/V5-2/V5-3 全部 completed；正式冻结 51 项（48 导入 + 3 治理件）+ 三轴独立审查 `accepted`（SQL/性能、生命周期/安全、测试/DAG，共 13 份审查/关闭记录）；四轮整改关闭 **14 条 P1 + 3 条 P2**；`--verify-manifest` 9188 通过、`--self-test` 17 例/32 变异 + 4 默认模式 + 3 守卫全拒。**仍 PLAN_ONLY，不构成实施授权，不改变 R4 的 WP 授权状态。**
- **FC-705 门**：09-09 22:00 daily 触发成功（`20260909T210001Z`、ok=true、`legacy_hits=[]`），权威账本开 **period 9**（hits=0）；last-two = P7（23:59:41 ✗）+ P8（24:00:11 ✓）→ 仍 `close_gate_allowed=false`，**预计 2026-09-10 22:00 运行后**转 true。
- **R9 批 3 范围修正（本目录相关）**：09-02 口径「无生产读者 backfill/promoter」已失真——~~实测仅 `artifact_backfill.py` 零生产读者~~ 🔴 **2026-09-10 再更正：这一条也错了**。`artifact_backfill.py` 实为**自带运维 CLI**（`--mode dry-run|apply`）、被 3 个契约测试导入、FC-906 卡片标注「FC-901 工具，**不改**」、冻结 v5 基线有 ZR1005-C1~C4 验收行 → **当前没有任何候选满足"零读者 + 无冻结约束"的机械删除条件**；owner 2026-09-10 的"执行 3a"指令因前提证伪而**暂停**，随后 owner **同日正式撤销 3a**（`artifact_backfill.py` 定性为受 FC-906 卡片保护的运维工具），**未删除任何文件**。其余候选（`backfill_v2`/`portfolio_promoter`/`_scan_root_v1`/`legacy_bridge_enabled`）均有活跃调用者。批 3 自此**只剩 3b/3c**，需技术门 + owner 政策门并先给出替代路径与回滚。清单见 revenue 侧 [r9_batch3_checklist.md](../../../../revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/r9_batch3_checklist.md)。对 R4 的影响：`r4-unit-remediation-map.md` 中 CA-304/ZR-1009 的"R9 批3（已批准待 FC-705 门）"应理解为**尚需 owner 重新确认范围**，不能按旧清单机械执行。
- **GP-009 累积**：Daily **5/7**（09-06~09-10）、Weekly 0/2（下次 09-13 04:30）、Monthly 1/1、drill 1/1。
- **本轮边界**：只写文档 + 只读核对；未运行产品测试、未改产品代码/配置/DB/任务/worker，未下载/LLM/删除。详见 [current-delta-2026-09-09.md](current-delta-2026-09-09.md)。

## 2026-09-09：Phase 7 收尾（117 逐行映射 + 独立复核）

- 交付 [r4-unit-remediation-map.md](r4-unit-remediation-map.md)：117 行＝25 CA + 92 ZR，逐行给出原痛点/原审计结论/域/旧WP/R4归属/R4步骤/验收路由/当前结果（全为待取证）；生成后由父 agent 机械交叉核验（117=117、第2/3列 0 处不一致、0 断链、实施子步骤 88 条唯一）。
- 独立复核（非作者 agent）产出 [r4-remediation-detail-review.md](r4-remediation-detail-review.md)：结论 **accepted_with_findings**，P0=0/P1=0/P2=2。C1 定义层 104 条唯一子步骤、0 重复（88 实施 + 16 CL/AC 映射行）；C2 117 行一一对应、第3列 0 处不一致、当前结果列全待取证；C3 16 条相对链接 0 断链；C4 两份核心文档 SHA-256 未变（E0DCCD11…896467 / B90EF4D0…380F49）；C5 无产品文件改动，revenue R9 批1+2 删除属实。
- 两处 P2 已按建议修正：F1（map 中 ZR-301–306 的组级引用落为 W04.01–.06/W06.01–.06/H01.01–.09）、F2（本目录 steps 路线表裸域标签改为「H01 风险控制（组）」「FC903 资格修复（线）」）；计数口径在 map 规则6写明（88 实施子步骤 + 16 映射行 = 104 编号项）。
- 本轮只写文档：未运行产品测试、未改产品代码/配置/DB/任务/worker，未下载/LLM/删除；PLAN_ONLY 边界不变。

## 2026-09-08：六类痛点实施细化（本轮进行中）

- 依planning-with-files选定既有审计目录，主agent独占共享三文件；协作者仅写117逐项映射，另一非作者独立审查两份新文档。
- 新增r4-remediation-steps.md初稿：88子步骤；H01硬禁用/可信归档/恢复/回收资格分栏，WP02–10实际consumer与真实测试、FC903原对象查找/unknown/新revision、117子条款执行规则、9泄漏/7验收、完整E2E和旧95门退出。
- 初步结构核验88唯一子步骤，原R4计划和矩阵SHA与历史review相同；尚未签本轮独立复核，产品测试未执行。
- README新增当前阅读入口；旧冻结计划/收据/95门原文件与产品配置/数据/worker不动。

## 2026-09-06至09-07：后续文档同步与实施细化完成

- 用户新增授权是同步其他planning文档及细化步骤；保护产品、冻结历史、生产状态不改的边界仍有效。活动23份文档已插入/精确更新状态，修改清单与hash见document-sync-validation.json；旧根三件套/冻结日期包不重写，由PLANNING_STATUS/CURRENT_STATUS覆盖解释。
- 两路手册agent在用量限制中断前已保存完整execution-data-plane/model-plane；9/7恢复由独立reviewer完整读回，不把中断算完成review。主agent完成handbook/control-plane、机器DAG和只读validator。
- 15包共160个编号小步骤（数据70、模型48、控制42）；每包G0–G5独立review，另5个安全签收门。真实来源/真实进程、独立oracle/来源→参数→输出、费用/文件/DB前后对账、失败停止/回滚分别细化，mock只可作为诊断不能关闭真实E2E。
- 独立计划review提出WP06.G3与S06自等、WP09依赖后续WP13来源两个问题；R3明确受控隔离进程协议和本包独立建立manifest，复核accepted_for_planning，7份输入hash绑定。没有实施或运行级PASS。
- 9/7发现其他任务提交：wiki d92f8bf、revenue6682ecf；旧closure删除、daily失败与ledger改路径均写current-delta覆盖，而非继续复述9/6“未删除/ok=true”。35旧选定hash中5漂移、30未变；本审计未作这些代码/运行动作，相关旧反证须新HEAD复验。
- 验证：46冻结唯一输入hash匹配；v5 import 54/54通过；静态DAG95门/15包及cycle/unknown/empty三个负例通过；23活动文档+审计Markdown合计251链接无缺。旧verify_sync快照不能用于强迫合法新状态回退，未改旧库存hash。
- 未实施真实E2E、生产SQL、下载/LLM、worker/任务、自启动、删除、push或安装。后续先精确DEV与G0/G1；其他运行动作各自批准。

## 2026-09-05 启动

## 2026-09-07至09-08 R4规划交付（当前接班点）

- 用户要求按数据湖减法调整planning。继续使用planning-with-files，在既有独立审计目录增加R4执行、真实测试矩阵、迁移表、独立审查与文档验证记录；只调整规划，没有新建另一套竞争实施目录。
- 形成A合同/B位置透明/C瘦消费者与唯一生产/D安全运维+独立M；44一级步骤，每步输入/产物/检查点/停止；DR/VR/AR独立审查及高风险动作、1→3→7批次审查保留，取消旧95门共同编排。36组测试（12L+8P+8O+8M）继续继承全部非同义原反例和真实层级。
- 独立审查提出VR/AR互等、C本地混入worker、broker目标误挂M；已修并获accepted_for_planning_delta。D.SAFE不授运行、snapshot写须独立动作、真实网络/自然期不作自身VR前置。报告绑定两核心文档hash；主agent审查迁移表但不冒称作者独立自签。
- 三仓PLANNING_STATUS、旧R3总计划/手册、GP六页与CI协议、filing E2E、v5衔接、诊断/审计入口已更新。旧手册状态头变更会改变当前hash，历史签署不被重写或解释成签新文件；旧DAG/verifier不用于R4。
- 文档核验：23页150本地链接零缺失；44步唯一、WP00–14完整、36测试ID唯一；两核心hash匹配review；46个冻结唯一输入SHA及v5 54份SHA/size均匹配。随后CI路由和收尾日志另作本地链接检查。详见r4-document-validation.json。检查不是产品测试，未逐117项复跑。
- 过程中PowerShell brace/猜错ci_root_fix子目录失败均无写；使用rg精确文件修正。测试组40为算术错误、全页正则39包含引用行，均改为定义表36；没有删case凑数。
- 本轮未改产品源码/配置/库/raw/任务/worker状态，未下载/LLM/启动/真实E2E/删除。其他任务可能继续变化，9/7代码快照不代表此刻HEAD；未来从A01重锁输入。本次文档任务完成，停在等待精确实施授权，不自动实施。

## 以下为历史阶段日志

- 用户明确将任务改为实际效果审计，允许写新审计目录，不允许修改既有目录内容。
- 已读取 skill、原始 P01–P11、ZR 92 项；CA 合并输出截断，待补全。
- 已发现旧入口页自相矛盾/状态滞后线索；不就地修改。
- 尚未执行产品测试、启动 worker、网络请求、数据库写入或任务变更。
- 接续：建立 CA/ZR/GP 逐项账本，按真实生产路径审计并记录反证，最后详细规划修复。
- 已完整补读 CA 25 项。CodeGraph 宽泛上下文命中不精确，改用具体 closure/scenario 符号及文件。
- 已启动三个有明确只读范围的独立代码探索，输出限定本目录的 wiki/filing/revenue 审计文件。
- 全仓 AGENTS 枚举遇13个 sibling临时目录和本仓pytest缓存拒绝访问；不绕过权限，不把这些临时目录当生产源码审计完成。
- 三仓git均提示全局ignore读权限不足；使用命令级safe.directory只读查询成功，未修改全局配置。
- 新运行记录表明源码/调度正在别的任务推进，本审计以文件hash/观测时间为证据，旧线索均重新核对。

## 2026-09-06 恢复

- 上轮三名独立审计均被服务用量限制中断；保留的是阶段发现，不是完整审计结论。现已从各自落盘断点续查。
- 本审计AST探针首次运行根路径parents层数错误，导致FileNotFoundError；无产品调用或写入。错误输出误存为probe-results.json，已安排本轮修正脚本路径并用有效JSON替换（仅新目录）。
- 重新核对所有当前运行证据；不沿用9/5前旧GP008参数错误结论。
- AST负例已成功，未来时间/缺tier证据/部分skip/空stdout/权限误分类全部复现。先前同patch delete+add同一路径被工具拒绝，改为Update；有效JSON已落盘。
- 117项完整receipt库存stdout超过工具返回上限；未把截断数据当完整库存。改为有明确excerpt标志的紧凑元数据，并按批次读取原证据。
- 117项逐项索引完成，初始汇总53 CONTRADICTED、58 PARTIAL、6 HISTORICAL_ONLY（这是原完整目标判定，不是53个模块全部错误）。GP10与历史空间/section/portfolio/v5项目另列。
- 独立复核确认A02/A04/A05/CA206，已吸收P2证据层级建议：machine_valid不等于实际state/CI放行，原select stub负例由真实schema+hash内存联合probe补强。
- 新增H01自动prune风险：生产worker调用apply=True，空旧归档目录足以触发全retired删除；已有测试反而断言此行为。未运行任何删除/数据库命令。
- v5阈值已完整阅读；它是历史v4导入最低标准，不是本轮授权或正式v5冻结。后续计划不得降格为“先修SQL就恢复”。

## 2026-09-06 审计与计划交付

- 完成三仓117项登记目标、GP10、历史继承与空间治理的限定只读审计；动态未验证范围在README和各分报告明示，没有运行全量生产测试。
- H01独立复核完成。编写15包修复计划，每个G0–G5有独立agent审查、负例、停止与授权门；原目录/主线/v5均不动。
- 计划R1独立审查提出2项P1/4类P2；R2补精确gate依赖、12a/12b/12c、作用域安全门、授权subtype、稳定归档snapshot/clock、恢复对象和缺失RED。独立复核verdict accepted_for_planning_delta；绑定rawSHA `07a0741d1ebe8a7ac82798efc9f0e33fcc77dd20d8119a703d9a097be24f562d`，未将计划通过算产品通过。
- 最终检查：5个JSON解析成功；coverage只输出摘要重新核实117/missing=[]（此前完整stdout超长截断，不据截断部分推断）；35个选定源码/证据SHA全部与快照相同；三仓HEAD及tracked dirty路径与既有记录相符。未对49GB生产数据库作hash/查询。
- 新增README作为交付入口；task_plan四阶段完成仅代表本轮审计和计划。未改产品代码、旧计划、配置、DB、任务/启动项，未恢复worker/网络/LLM/删除。其他线程既有修改保持原样。
- 19:54:40 UTC最终链接检查：146处同目录Markdown/JSON/Python产物链接无缺失；总计划SHA与独立R2签收完全一致。该检查不覆盖外部URL或所有历史源码行号。
- 后续必须先取得精确DEV批准，再做WP00/01设计与独立门；运行/外发/调度/自启动分别授权。无需继续无界审计来假装推进，当前交付结束。
