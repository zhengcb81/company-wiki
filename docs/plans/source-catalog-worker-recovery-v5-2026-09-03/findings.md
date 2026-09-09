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
- **2026-09-09 更正**：本目录已随 R4 规划语料入库（wiki `f23ad1b`），`git ls-files` = 64（另 5 份 V5-1 新文件随后提交）。
  「tracked=0」不再是现状；按 README 自己的约定，V5-2 必须先重验 index/属性/并发写边界再冻结。
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
