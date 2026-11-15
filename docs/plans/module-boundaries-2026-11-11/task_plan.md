# 模块边界收口计划

## M3 — 当前 HEAD 边界漂移审查（2026-11-15 新增）

**状态：IN_PROGRESS — 九仓基线已记录；CWP 第一组边界漂移已按 TDD 修复并通过定向验收；其余当前版本差异仍待逐仓审查。** 原 M2/E01-E09 仍对其绑定版本有效；M3 不抹去原收据，也不把新版本自动视为已验收。

### 目标与设计原则

验证 M2 后各仓的源码变化是否仍守住公开接口、单向依赖与数据/状态 owner；只对能复现的边界缺口写 RED 测试并修复。Python 私有命名不是运行时隔离；普通模块继续用公开 package/facade、依赖方向和静态反例测试约束，只有确需隔离资源/权限的边界才使用独立进程或服务合同，不把整个系统改成微服务。

### 工作阶段

1. **冻结当前基线（完成首轮快照）**：记录九个仓 current HEAD、PWF 唯一入口、M2 接收 ref、主线/remote 状态；逐仓列出接收 ref 之后的源代码改动文件。快照和 owner 状态差异见父计划 `module-pwf-reconciliation-2026-11-14/findings.md`。历史快照不得覆盖最新 owner 状态。
2. **审查边界差异（进行中）**：每个变化映射到所属模块、公开 consumer、数据/配置/预算 owner 和方向；检查内部导入、跨仓路径/数据库操作、重复校验、循环依赖、全局可变状态及绕过公开 CLI/API 的方式。无代码差异的仓只核对合同，不强行改代码。
3. **测试先行**：每个可复现越界路径先添加最小负例并确认 RED；静态扫描覆盖显式/相对/别名/动态导入的约定范围，安装测试从构建产物验证公开入口；CWP 只维护本仓测试。不得用 grep 私有名字计数冒充完整边界验证。
4. **归属修复**：源码修复和本模块测试由对应 repo owner 完成；ROOT 维护总矩阵与 CWP 组合检查，不直接改其他模块实现。只复跑受影响合同和一次最终组合审查，避免全量测试反复运行。

### M3 完成条件

- 每条跨模块边都有唯一 producer/consumer、公开接口/schema、版本与 owner；不存在未归属的数据、预算或状态写入。
- 当前 HEAD 相对 M2 的源码差异均有明确处置：边界保持、测试补强或 owner 修复；不存在只因历史收据而跳过的新路径。
- 有针对发现的真实绕行方式的 RED→GREEN 测试；被测试范围和静态工具限制写明，不声称 Python 包内私有符号在语言层绝对不可调用。
- 受影响的 owner 合同与独立安装组合通过，最终报告绑定精确 HEAD；PWF 入口更新到同一版本。

### 2026-11-15 CWP 首轮边界漂移处理

- `eval` / `exec` / `compile` 字符串动态执行可绕过 AST 符号扫描。反例先后覆盖直接调用、`builtins` 属性/别名、`__builtins__` 字典、`builtins.__dict__`、`vars()`/`vars(builtins)`、`globals()`/`locals()` 和 `.get()` 查找；扫描器把识别出的内建命名空间访问归一到同一执行入口再拒绝。生产源码当前没有动态执行调用；这是静态边界合同，不声称 Python 运行时沙箱。
- `automation/narrative_batch.py` 曾直接导入未公开的 `NARRATIVE_SUBJECT_REF_SCHEMA`。不扩大 schema 常量的公共面；在公开值类型 `NarrativeSubjectRef` 增加 `for_official_json_projection()` 工厂，让版本常量继续由其 owner 管理。工厂测试先 RED 后 GREEN。
- pytest 默认临时根不是天然短路径：本机沙箱注入的默认基准路径为 153 字符，旧逻辑因 `basetemp is None` 跳过检查，且旧 fallback 仍放在 `%TEMP%` 下。现在按 pytest 默认命名估算实际路径；超过预算时选 checkout 与系统 temp 中较短的根，生成仓内被 `.gitignore` 屏蔽的唯一 `.cwpt-<12hex>` 目录并在退出时清理。实际运行路径为 53 字符，cleanup 收据显示目录已删除。
- 正式摘要 E2E 还暴露了 Windows 沙箱拒绝 `os.link` 的环境限制（独立复现 `WinError 5`）。对象存储层现在仅在 Windows 硬链接被拒时退回同目录、原子、无覆盖的 `os.rename`；遇到并发已存在目标仍按实际内容 hash 验真，损坏目标不覆盖。
- 最新定向结果：短路径与默认路径合同、对象存储、Subject owner、层边界合同（含上述命名空间绕行反例）、官方 JSON batch preparation 合计 **119 passed / 42.68 秒**；测试日志再次显示默认根 153 字符→仓内实际 53 字符，退出清理成功。完整空内容 CLI 摘要/发布/读取/缓存复用 E2E 在对象存储修复后 **1 passed / 40.48 秒**；受影响文件 Ruff 通过。此前首次集成失败已分别归因于长默认 temp 和硬链接被沙箱拒绝，修复后各自复验通过。
- CWP 实现与总控 PWF 已提交 `3bc4ed86a` 并推送 `origin/master`；推送 fast smoke **18 passed / 15.06 秒**。精确 CI 仍按仓库配置待 GitHub Actions 完成，不把本地快门测试称为完整 CI。
- **M3 仍 OPEN**：上述仅是 CWP 一组差异的当前版本审查，不能替代 CWP 剩余差异或 RF、StockWiki、Dashboard、RFAudit 代码变化的归因与 owner 合同测试，也不关闭父业务摘要质量任务。

## Goal

从当前各模块架构出发，定义有限、可验收的模块化与解耦范围；用公开接口、独立安装/隔离测试、owner 状态归属和 TDD 完成边界封装，再恢复原主线。父计划为 `../du11-source-closure-2026-10-18/`。M0原为规划；用户随后明确授权A1调查、清理和有限并线，执行结果见reconciliation.md。

## Current Phase

### Phase A1 — 各模块工作区与未并线提交核销
**Status:** complete

2026-11-11用户新增授权：逐模块调查未提交及已提交未并线改动；确认归属后可删除无用改动，尽量并入正确主线；余项必须写进原施工卡。ROOT负责所有Git/清理变更，各路审查只读。保留下载原件；已证明需保留的有效代码和正在施工内容先分类，不能用整仓reset/clean代替调查。

步骤：新鲜Git refs/worktree/dirty盘点 → PWF/commit/交接与patch-equivalence逐项归因 → 删除确认无用内容/并线有依据且可验收分支 → 余项逐卡归属/顺序/测试 → 独立核对与发布。

证据集中在review/repo_reconciliation_20261111/；新架构实现仍按五卡后续执行，本节点仅做用户新要求的仓库整理与并线。

结果：8仓390个分支/remote refs、253工区、7tag、2stash已调查并分责；FF B34与Dashboard边界修复独审/定向回归后已入main、推origin。清理确定测试目录约216MB、7个空旧工区、source-facts重复源码、已吸收stash及生成物；未接收能力/有价值WIP全部加入原五卡A0和ROOT清单。A1 complete只代表本次核销交付，不代表所有历史工区清空或M1/M2完成。

### Phase A / M0 — 当前架构、接口与完整施工图
**Status:** complete

三路只读代码调查及ROOT对账已完成。五卡和接口矩阵已通过独立方案审查（PASS），两项阻断及三项精确性建议全部修复；本轮只改计划。证据：review/cwp_architecture.md、acquisition_architecture.md、research_architecture.md、root_baseline.md。

- [x] CWP 479个src文件/7包+根35模块清单；FF/ET/SID/RF/StockWiki/Audit/Dashboard实际模块图。
- [x] 当前实现、已证明能力、确定缺口、风险和未运行验证分开；原D4/D5/P3结果限定范围保留。
- [x] architecture.md/interface责任、boundary_matrix.json和acceptance E01–E09有限出口。
- [x] 五张互斥仓库卡、worktree基线/写集合、测试先行、独审、交接格式与合流规则。
- [x] 方案独审与修复、父计划状态对齐及文档JSON/链接/工区互斥检查完成；本轮以正常Git文档提交交付，实际发布版本看Git历史。

### Phase B / M1 — 五个owner并行TDD与模块交付
**Status:** complete

五条 owner 卡均已审查并入各自主线并推送，测试和发布版本见 [progress.md](progress.md) 与 [boundary_matrix.json](boundary_matrix.json)。StockWiki C38/B03 及公开来源消费者已进入本地 `master`。M2 集中处理各仓公开接口的组合结果。

任务卡见 dispatch.md。保持现有跨仓wire，作者各自A→B→C连续实施；不是每一步等ROOT批准。

| Owner | 本轮有限任务 | 独立验收 |
|---|---|---|
| CWP | CWP-01协议外OCR配置、02隐藏预算、03类型导入、04实际安装、05根/状态/模型边界分类 | 七责任逐项说明，公开替身/安装/恢复/原件保护 |
| FF | FF-01六operation及job/三表隔离，02command/config组装 | 真subprocess+无邻仓环境；已满足允许NO_CHANGE |
| RF | RF-01 旧越层工具分发、02 core/report 依赖、03 历史 profile 与默认隔离及 B37 公开合同 | MB-RF 已并入，证明范围以该卡收据为准 |
| ET | ET-01纯合同/进程与provider分离，02固定表示限额复现根修 | worker CLI成功/错误/unknown/预算/取消 |
| SID | SID-01typed错误贯通，02metadata反向依赖 | 纯API、稳定wire/过滤语义、staging-only |

ROOT 已在 StockWiki 和 Dashboard 各自工区接收对应接口。Audit 的公开资料包读取在 D4 被重新验证，五卡原作者工区已回收。

### Phase C / M2 — ROOT组合与整个架构阶段关闭
**Status:** complete

1. 锁各模块交付commit和正式runtime形态；选择真实本地样本/已有报告/三表快照并冻结必需点。
2. 核对Dashboard选用release代码根与数据根，不把缓存remote、main或旧配置当现行部署事实。既有owner处理必需release并线。
3. CWP卡交付后ROOT才改组合runner，按acceptance E01–E09一次运行。已有D4/D5/reader替换证明按用例复用；不重复收费全文测试。
4. 集中独审，不通过的格交给对应owner修复并复跑受影响部分。无必需skip；可选诊断不作许可，真实失败不改成PASS。
5. 各正确主线/remote对齐、当前自有测试目录恢复、交接证据完整、PWF CLOSED；立刻回父计划R4/T4→新版摘要→真实缓存→RF实际采用→公司循环。

此阶段不等待未来所有研究问题消失；其验收范围在矩阵里。新业务质量问题进入父计划，不无限延长解耦阶段。

## Next Step

E01–E09 已通过，范围限定见 [ROOT 组合记录](review/root_composition_20261114.md) 和 [E01–E09 矩阵](boundary_matrix.json)。当前唯一架构下一步是完成本计划 M3：复核其余 CWP 后续代码差异，并把 RF、StockWiki、Dashboard、RFAudit 在 M2 接收 ref 之后的产品代码改动按 owner 逐项归属；只为可复现越界先写测试并修复，提交时绑定最终版本。M3 没有关闭前，不声称全项目当前版本已完全解耦，也不把旧收据外推到新代码。M3 有限范围完成后，再回 [父计划](../du11-source-closure-2026-10-18/task_plan.md) 的 P1 真实摘要任务；公司循环继续按原 PWF 保持暂停。

## Decisions

- 主线质量问题与模块边界分别记账；不以全文摘要/研究质量作为架构阶段永远延后的出口。
- 不新增人工许可、逐步签收或 Python 运行时防反射沙箱。
- 保留原件、现有配置和外部 harness 工作区。
- 采集审查最初建议只派FF/SID最小卡；ROOT依据用户“每模块设计解耦”要求，将已确认ET协议反向依赖和SID下层导入上层纳入本轮，形成五卡。没有确认缺陷的StockWiki/Audit仍先验证，避免强制改写。
- 同理RF core/report职责纳入同一RF作者，历史B34兼容不全面迁移。Sina只在CWP owner，金融数值不转回PDF抽取。

## Errors Encountered

| 观察 | 原因与处理 |
|---|---|
| 外仓Git普通沙箱status报work-tree/Permission denied | ROOT宿主只读重查成功，记录真实WIP；不是源码缺陷 |
| installed PWF resolver按旧PWF_PLAN_ROOT=docs/plans静默无结果 | 当前脚本变量语义不同，改用显式-PlanRoot与PLAN_ID，已正确解析本目录；不改技能/不增加许可 |
| CodeGraph部分当前文件不在索引 | 记录覆盖限制，用文件列表与已定位文件读补齐；未运行init/重建索引 |


## 2026-11-13 — 五条 owner 卡并线收尾

- [x] MB-CWP、MB-FF、MB-RF、MB-ET、MB-SID 均已独立审查并进入各自主线。
- [x] 五条线的最终集成测试、异常基线和独审状态已回写 boundary_matrix.json。
- [x] 本地/远端引用均核对；各仓 ROOT PWF 收据已推送。
- [x] ROOT 接收 StockWiki C38/B03 及安装态来源读取。
- [x] Dashboard 移除 CWP 私有读取依赖，公开流及摘要通过独立安装测试。
- [x] 2026-11-14 按矩阵收口 E01–E09，复验并线版本和回收自有工区。见 [ROOT 组合记录](review/root_composition_20261114.md)。
