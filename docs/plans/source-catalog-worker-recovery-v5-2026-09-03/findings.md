# Worker v5 — 发现与决策

> 2026-09-06新增跨计划发现：原痛点审计证实当前回收覆盖和worker候选查询/取消/失败预算等结构风险，详见[wiki审计](../painpoint-outcome-audit-2026-09-05/wiki-audit.md)及[历史空间审计](../painpoint-outcome-audit-2026-09-05/historical-projects-audit.md)。本目录原基线/独立导入review仍只证明导入完整，不证明修复或运行安全；后续门与WP01/04/05/06/14交叉核验。

## 1. v5 创建依据

- 用户明确同意“开一个新目录放 v5”。
- 原 v4 manifest 自身 SHA-256 未变，但 48 份当前文件中 27 份与冻结 raw hash 不符。
- **17 份已证明仅 CRLF/LF 差异；10 份不能证明与原冻结字节等价**（2026-09-09 更正：本页原写 16/11，与本目录事故报告 §4 表格及独立复算不一致；权威分类见 [v5-baseline-equivalence.json](v5-baseline-equivalence.json) 与 [版本合同 §4](v5-version-contract.md)）。
- 因此用户批准的是以当前保留内容建立**新基线**，不是覆盖 v4 或伪称旧审查通过。

## 2. 并行工作树风险

安装的 pre-commit 对未提交修改执行整仓 checkout/patch 恢复；具体 hook 的文件过滤不能保护
其他任务未提交的 tracked 计划。四份相同补丁、27 个集中写入时间以及 core.autocrlf=true
高度支持其为本次漂移原因；缺少进程级写事件审计，归因不能超出证据。

.gitattributes 只防转换，不能锁文件；审查前后 hash 相同也不能排除阅读期间被替换后恢复。
新目录当前未被 Git 跟踪，可避开现有 hook 的 tracked-file checkout；日后被加入 index 则须重验。

## 3. 导入与正式冻结分开

import_manifest.v5.json 只核对 raw byte 副本、来源与原目录未被本次复制改变。
baseline 中的 schema/protocol 仍是旧版历史输入；不会直接把它们当正式 v5。
正式 plan_manifest.v5.json 必须等版本合同、检查器和三路独立审查流程闭合后才生成。

## 4. 不变边界

最新用户授权允许将唯一旧v1–v4目录移入回收站，现已完成；除此之外，计划工作仅在v5目录进行。
不修改源码/配置/数据库/主线计划/Git全局设置/hook。worker保持暂停；没有运行、恢复自启动或外发授权。

## 5. 本次导入实测

- 2026-09-03T22:37:34.3533639Z完成54份精确名单复制：48份计划输入，6份历史/来源。
- 所有源文件复制前hash=复制后hash=目标副本hash；48份中21份等于原v4冻结值、27份为已记录漂移。
- 对漂移文件使用已独立回读诊断报告记录的当前hash作复制前锚点，拒绝超出该已知状态的变动。
- 导入manifest SHA-256：`da7d116e8c692d6311411c7390bec4278b59666a771823672f53e9b0f6567e4a`。
- 只读verify_import.py通过54/54文件、精确baseline文件集合、无reparse、路径负例及历史计数检查。
- 61个当前文件路径的244项Git属性均为unset，Git tracked路径=0。这里只证明当时Git边界，
  不是永久文件锁，不授权以后把新目录随意加入共享index。
- **2026-09-09 更正**：本目录已随 R4 规划语料入库（wiki `f23ad1b`），另加 V5-1 交付文件；精确 tracked 数以
  `git ls-files` 实时查询为准（本页不写死）。「tracked=0」不再是现状；按 README 自己的约定，V5-2 必须先重验
  index/属性/并发写边界再冻结。
  同时实测**旧目录 `source-catalog-worker-recovery-2026-08-22/` 已复活**（38 文件、tracked、clean、
  mtime 2026-09-07T18:08:52Z UTC＝本地 19:08:52+01:00），与 README「已回收」表述不符——见[版本合同 §6.1](v5-version-contract.md)。

## 6. 独立导入审查完成

独立reviewer `/root/v4_test_dag_review`逐项验证54个副本及当前来源、精确文件集合、历史hash对应、
属性和未跟踪状态，并独立运行检查器，返回`IMPORT_REVIEW_PASS`。无导入范围阻断项。
保存记录的SHA-256为`baa64f7b4749c13b4f8188e4982a9e3fa907f692e776c37014f4dd2e57490e43`；
同一reviewer已回读返回`FAITHFUL`。这只关闭V5-0，不替代正式v5计划审查。

## 7. 旧目录已可恢复退役

按用户最新要求，旧v1–v4目录的54个文件已整体移入Windows回收站，且回收站条目被确认。
53份计划/审查文件在v5有精确副本；额外1份pyc是生成缓存，未污染固定导入manifest。
独立预检从缓存缺口BLOCK，经显式例外记录与复核关闭为SAFE_TO_RECYCLE；无reparse或保留目录重叠。
删除后v5检查54/54 PASS、原调查报告hash未变。旧source路径是历史元数据，不是v5校验运行依赖。

## 8. V5-2 冻结与三路独立审查（2026-09-09）

- **冻结集 = 51**：48 份导入计划输入（`baseline/plan/**`，递归枚举）＋ 3 份 v5 自有治理件（`plan_manifest.schema.v5.json`、v5 checker 入口、`.gitattributes`）；manifest 自排除。证据工具与证据输出分别由 `evidence_tools[]`、`evidence` 绑定，不进入 normative。
- **等价性以字节复算为准**（不采信标签）：21 `v4_exact` / 17 `crlf_only` / 10 `unproven_new_baseline`；`crlf_only` 的判据是「LF 归一化后等于 v4 冻结哈希」，且经 v4 冻结 manifest 二次锚定。
- **三路审查结论**：SQL/性能、生命周期/安全、测试/DAG 各自独立复算，均 `accepted_with_findings`、**无 P0**、共 **9 条 P1**；复现配方与证据命令保存在三份 `v5-freeze-review-*.md`。
- **P1 全部关闭（V5-2.1）**：N6 逐件复算等价类别；N7 增补 v4 冻结 manifest 锚；N8 重跑默认模式逐字节比对且命令为 schema `const`；N11 取代链恰好两条且禁止形近/旧目录路径；N13 与 `V5-SET-NESTED` 递归枚举；N9 改为机器可读处置载荷 + 目录清单摘要复算；`V5-PATH-SAFETY` 恢复 v4 的 reparse/包含不变量；N10 fail-closed 覆盖 manifest 与 51 个冻结项的 Git blob。
- **自测强度**：`--self-test` 17 例 / 27 变异，每条都在「全检查」与「仅该编码」两种模式下被拒——后者排除「别的检查顺手拦住」的假阳性。
- **仍存的风险**（见记录 §6）：旧目录未删除未加锁；不可变性最终依赖 Git 提交历史；活动文档中的旧目录引用不受机器检查覆盖；`reviews/` 历史记录按合同不改字节。
- 本目录仍是 PLAN_ONLY：没有实施 worker 修复，没有触碰源码/配置/数据库/任务，没有恢复 worker 自启动。

## 9. V5-2 结论（2026-09-09，三轴复审 accepted）

- **冻结可信度来自四层**：① 51 项冻结集逐字节哈希（导入 48 + 治理件 3，manifest 自排除）；② 冻结内代码钉扎 6 份历史/来源文件（v3/v4 manifest、旧 progress/revision、事故报告、原调查报告）；③ manifest 绑定证据输出、证据工具、捕获记录、边界处置载荷；④ N10 对 manifest + 51 项做 worktree↔HEAD blob 比对（未跟踪即 red），最终账本是 Git 提交历史。
- **负例强度**：N1–N17 共 32 个变异，每条在"全检查"与"仅该编码"两种模式下都必须被拒（隔离模式排除假阳性）；另有 4 项默认模式检查与 3 项启动守卫检查。13 份独立审查/关闭记录全部保存在本目录。
- **复审发现的问题类型（值得记住）**：环境相关哈希/EOL；"只核对标签不重算"；"锚点自身可写"（v4 manifest）；"检查机制本身可被劫持"（`sys.path[0]` 影子模块，父子进程都要防）；"批量化优化引入语义退化"（HEAD→索引）；"判据只认字面路径"（改名/新建副本）。这些都是**机制**缺陷，不是笔误。
- **剩余风险（已声明，不隐藏）**：旧目录未删除未加锁；同时改名+改标记的副本、`docs/plans/` 之外的副本不在机器判据内；`frozen_at` 无法机器锚定；活动文档中的旧目录引用不受机器检查覆盖；`reviews/` 历史文件按合同不改字节。
- **下一步**：V5-3 交接（活动入口/历史索引/剩余风险/实施顺序 + 只读复核 worker 暂停与自启动入口关闭），仍不实施、不授权。
