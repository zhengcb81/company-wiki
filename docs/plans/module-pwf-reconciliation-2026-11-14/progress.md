# 进度

## 2026-11-15 16:51 UTC — FF weekly T3 根因诊断完成

- 对 RF 20261115T084227Z 的失败按冻结三仓 ref 查明：FF 1dfd818 的四个下载 E2E fixture 在 allow_download=True 时未提供 acquisition_limits，FF 因而没向 CWP 传入 bytes/time/cost 三项参数。CWP 在 provider 启动前按预算合同退出，原始错误明确为 bounded provider access requires --max-download-bytes, --max-download-seconds, and --max-download-cost-usd，所以本轮 downloads=0。
- CWP 已有测试要求显式完整限额，保持不变。FF owner 应修正 fixture/公开请求并重跑 opt-in T3；RF owner 仍需同步记录该周跑；ROOT 只负责记录证据并保持外仓只读。
- 在 FF main@d694d11 与本地 tracking ref origin/main@1dfd818 间看到 FF1 envelope lane 的产品差异，未触碰。该周跑仍绑定旧 1dfd818。FF 当前 git status 异常，不能判断 tracked dirty/clean。
- 无 provider 的缺预算反例已复现；带限额正向 smoke 超过 60 秒后中断，不计通过。完整证据见 [FF budget root cause](../module-boundaries-2026-11-11/review/ff-weekly-budget-root-cause-20261115.md)。

### 17:02 UTC 定向确认 CWP 预算合同

- 运行 tests/contract/test_source_catalog_adapter_process.py 中缺失/完整预算两条用例：2 passed / 3.49 秒。没有 provider 调用；这只确认 CWP 现有预算合同仍按设计工作，不替代 FF 请求修复或真实 T3 复验。

### 17:06 UTC PWF 发布收据

- 根因记录和 PWF 对齐提交为 476cb4a79a7aa97080baa5a6a256052403d89596。Git push 服务端确认 d46357c12..476cb4a79 推到 master；push fixed smoke 为 18/18、9.26 秒。
- 推送后本地 HEAD 与 origin/master tracking ref 均为 476cb4a79。额外 fresh ls-remote 因本地 Git 报 getaddrinfo() thread failed to start 而未完成；不将 push 响应之外的证据写成独立远端读取。完整 GitHub CI 尚未核验。

## 2026-11-15 15:42 UTC — CWP lambda 闭包边界盲区修复并推送

- 独立架构复核指出边界扫描器的 lambda visitor 只查默认参数，未检查表达式结果；`return lambda: du` 可将导入的外部模块对象藏在闭包里，绕过普通 `return du` 的模块对象逃逸规则。先添加 RED 用例确认失败，再在 `_local_body` 检查 lambda 结果，同时保留参数遮蔽控制例 `lambda du: du`。
- 修复限于 `tests/support/layer_boundary_scan.py` 与 `tests/contract/test_layer_public_boundaries.py`，未改生产模块代码。最终定向合同文件 **66 passed / 6.47s**；独立审查 agent 对最终修复单独复跑同命令也是 **66 passed / 6.47s**；受影响 Ruff 通过。
- 同次独立复核检查 `worker_process` 与 OCR 的动态 factory 入口，确认当前生产构造由所属模块组装并指向 owner-local 实现，未找到具体跨包穿透。任意运行时模块字符串无法由静态 AST 扫描完整证明；记录为方法限制，不当成已发现生产缺陷或开展无边界重构。
- 代码提交 `07d48118022e660d65e3218594bfb02085710caf` 已通过正常 `git push origin master` 推到 `origin/master`；push 前 fast smoke **18 passed / 45.23s**，GitHub Actions 完整 CI 仍以该精确 HEAD 的远端运行结果为准。PWF 随后按此 ref 对齐并另行提交推送。
- M3 仍未关闭：StockWiki 根 canonical PWF、RF 两项 weekly runtime 结果仍由各自 owner 对齐；ROOT 之后绑定九模块确切 refs 出具最终报告。其余外仓只读。

## 2026-11-15 — M3 当前 HEAD 与 PWF 第二轮核对

- 将旧的 post-M2 路径筛选按源码/测试/计划重新分类，修正“Dashboard 缺 final receipt”的过期判断：Dashboard START_HERE 与 receipt carrier 已在 `3f83bb5` 收口；本地缓存 `origin/main` 同为 3f83。Owner 记录含此前 fresh remote 验证，本轮没有另发网络查询。
- 当前版本表与 I10–I12 三条接口已写入 `module-boundaries-2026-11-11/task_plan.md`、`interfaces.md`、`boundary_matrix.json`。I10 已有 IQS active package 生成 53 题 envelope 并在隔离 StockWiki workspace publish/readback 的互操作证据；C06 真实历史覆盖仍 OPEN，属于 owner 业务数据项。I11 已由 StockWiki CLI 版本字段测试及 IQS 当前 C38/C5 120 passed、固定核心组合 296 passed 覆盖，不再要求重复回放。I12 是 CWP 内部 DU public façade 与 SourceCatalog 的边界合同，当前 119 项通过；CodeGraph 未解析到调用边，按其 best-effort 限制记录为未知消费关系，而不是判作无调用。
- IQS 当前 `master@3d9243c=origin/master`；活动 `codex/iqs-manifest-delivery-01@ecb4a5d` 只有 PWF/状态/证据改动、无产品源变化，因此不改变 I10/I11 当前代码证据。StockWiki `master@0450506` tracked clean、无 remote；其根 PWF 的阶段/提交状态差异仍由 owner 对齐。
- StockWiki `master@0450506` 的公司评估 lineage 与 membership 边界代码均已在当前主线；两个 11-14 子计划记录了 owner 测试与部分独审，但根 canonical PWF 日期停在 11-08，且子计划仍写“未提交/待 review”。按 StockWiki 活动 owner 隔离原则不写其工作区，登记为 owner reconciliation，不把代码/证据删掉或误称未交付。
- FF `main/origin@1dfd818`、RF `main/origin@f2215959` 当前状态核对完成；RF 两个 weekly run 文件仍 tracked dirty，保留给 owner。Dashboard 与 RFAudit 的当前代码差异均保持各自模块边界；RF 变化仅落在其 report renderer/test，FF 无产品源变化，Audit 无新增产品源码。
- CWP 目前 `master@origin/master=91137e257`，tracked clean；未跟踪仍为 23,334 个文件且与既有分类一致。本轮仅整理 PWF，不修改其他仓库，不对这批历史/运行资料做无差别清理。
- Dashboard owner 的续核卡另行分类：C01 已由 `c8939e5` 吸收；B-real 预览适配未执行，必须基于 Dashboard `main@3f83bb5` 重做候选差异；B03 旧独审收据仍 incomplete。它们不属于 CWP M3 的完成门槛，也不改变跨仓只读约定。
- M3 仍 IN_PROGRESS：需要 StockWiki owner 对齐根 canonical PWF、RF owner 记录两项 tracked weekly run 结果，并由 ROOT 把九模块当前 refs、CWP 24 个产品路径复核及 I10–I12 证据绑定到最终报告。I11 不再安排重复回放；未发现的边界缺口不通过扩大测试或新增审批流程制造工作。父 P1 业务摘要仍排在 M3 后，固定公司循环继续暂停。

## 2026-11-15 — M3 CWP 首组边界修复完成

- 补充动态执行边界负例后，`eval/exec/compile`（含 `builtins` 属性/直接别名、`__builtins__`/`builtins.__dict__`、`vars()`/`vars(builtins)`、`globals()`/`locals()` 和 `.get()` 查找）不能绕过 AST 合同；每轮新增反例先 RED 后转 GREEN，生产代码未发现对应动态调用。
- 修复层边界合同发现的内部 schema 常量穿透：新增 `NarrativeSubjectRef.for_official_json_projection()`，由 public value owner 管理 schema，automation 调用工厂。
- 修复 pytest 的重复长路径根因：默认 `%TEMP%` 路径（实测估算 153 字符）现在也进入长度预算；自动选择 checkout/系统临时根中更短的一处，落到唯一 `.cwpt-<12hex>` 目录（实测 53 字符），退出时清理。短路径测试保持显式、短输入，不再依赖主机 `%TEMP%`。
- CLI E2E 暴露 Win32 沙箱拒绝 `os.link` 的另一项环境差异（独立探针 `WinError 5`）。对象存储为 Windows 提供同目录原子 `os.rename` 无覆盖 fallback；同内容并发目标仍验 hash，损坏目标不覆盖。
- 最新定向测试 **119 passed / 42.68 秒**；运行日志复核默认临时根 153 字符被自动切换为仓内 53 字符短根且退出清理成功。官方 JSON 空内容 CLI 摘要、发布、读取和跨 run 缓存复用在存储修复后 **1 passed / 40.48 秒**；受影响 Ruff checks 通过。两次首轮失败分别以默认 pytest 路径预算修复和 Windows rename fallback 修复；本轮没有重跑全量 suite。
- CWP 实现 commit `3bc4ed86a` 已推送；之后 PWF-only receipt carrier `f175e6c37` 也已推送。代码推送 fast smoke **18 passed / 15.06 秒**；最终本地 `master` 与 `origin/master` 已核对一致，完整 GitHub CI 仍以远端结果为准。
- 总控 CWP PWF 和 module-boundaries PWF 已补记该结果。M3 仍 IN_PROGRESS：其他 CWP 差异及 RF、StockWiki、Dashboard、RFAudit 当前源码路径尚未完成逐项审查；FF/ RF/ Dashboard 的 canonical PWF 局部状态差异仍由各仓 owner 更新。父业务摘要任务继续按其 PWF 排队，不因这组测试自动恢复公司循环。

## 2026-11-15 — 九模块 PWF 对齐与边界复核启动时快照（历史）

- M2 接收版本后的真实代码变化集中在 CWP narrative/document-understanding（21 个产品文件，5 个相关提交）、RF 的公开 FF client/三表源适配（3 个产品文件）、StockWiki 的 company assessment/quick-scan owner store（3 个产品文件），以及 Dashboard forecast scope/synthetic adapter。RFAudit 的变化在计划脚本；FF/ET/SID 当前比较差异以文档/测试为主。尚无新越界缺陷被确认。
- 已用 TDD 确认 CWP 边界扫描器遗漏动态字符串执行：新反例首次失败，补入 eval/exec/compile 检测后专用反例通过。完整边界合同结果 63 passed / 1 failed，暴露 `automation/narrative_batch.py:17` 引用未公开的 `narrative_subject.NARRATIVE_SUBJECT_REF_SCHEMA`；当前转入归属调查和最小公开契约修复，不调整断言。第一次整文件测试调用未返回可见 exit code，第二次以完整进程结果复跑确认上述结论。
- 根因已定位：Automation 只需构造由 `narrative_subject` owner 管理的紧凑投影 ref，却直接依赖其内部 schema 常量；公开的 `NarrativeSubjectRef` 值类型被正确用于其他路径。计划由类型 owner 增加窄工厂，并让 automation 改用工厂；不扩大常量导出。
- CodeGraph 首轮结构结果显示：RF 的 filing client 有明确 `resolve_filing` public subprocess entry；Dashboard 的 CWP adapter 经 owner CLI/source adapter；StockWiki quick-scan store 自己持有本仓 SQLite。由于索引覆盖/解析有限，接下来检查具体 import/adapter 与现有边界测试，不把一次搜索无结果判为安全证明。
- 本轮有两次只读脚本/补丁上下文错误，均没有误写代码或其他仓；已改用正确的 Git exit-code 检查和实际文件标题完成操作。`git diff --check` 通过（仅 Git 行尾转换提示）。
- 只读核对了九个主模块的 canonical PWF 和 Git 主线状态。发现 CWP 总计划、Dashboard START_HERE、RF 状态快照之间存在日期/交付收据差异；FF F-08 与“无未结产品 lane”措辞相冲；StockWiki C06 仍缺完整组合验收。细节已写入 `findings.md`。
- 模块边界 M2/E01-E09 的登记验收保持 CLOSED；此结论限于其明确范围，不把 owner 业务任务或一般摘要质量等同于解耦失败，也不把静态测试当运行时封锁。
- 本次没有改动其他仓或运行产品测试。下一步：完成 owner PWF 对齐（先处理非活动仓；StockWiki/IQS 只依据 owner 允许的状态入口处理），随后按新的 M3 当前 HEAD 架构审查计划建立可复现的边界反例测试；任何产品代码修复先在其所属模块测试中 RED，再由该模块 owner 修改。
- M2 后源码路径差异的初筛已记录；一次 PowerShell 只读脚本曾因错误的括号表达式失败，未写文件，改为单独检查 `$LASTEXITCODE` 后完成。一次补丁因使用了错误的标题上下文未匹配 module-boundaries 文件；现已按实测标题单独插入 M3 说明。`git diff --check` 无空白错误，仅出现 Git 的 LF→CRLF 提示；未改变仓库行尾策略。
- 代码图谱核对已发现索引覆盖不完整（ET 无索引，RF 个别模块符号未检出）；不据此下“无跨层调用”的结论。已定位到最新版本中 CWP、RF、StockWiki、Dashboard 的有限源码差异，下一步按具体文件和公开入口检查依赖方向，并为确证的绕行路径先写负例。

## 2026-11-15 — 一周界线临时目录清理（部分完成）

- 按用户要求以 **2026-11-08 00:00** 为保留分界，并逐目录检查后代文件/目录的最新修改时间；不能只看父目录时间。11-08 之后有活动的目录保留。
- 已用各自主仓的 `git worktree remove --force` 移除 7 个超过一周、所有分支提交都已是对应主线祖先的旧施工工区：`_merge_mc`、`MeetingConverter-ci-fast-gate`、`MeetingConverter-output-integrity`、`_merge_ir`、`industry-research-report-generation`、`_merge_qa`、`QAbyLLM-rag-safe-rebuild`。删除前核过提交 ancestry、dirty 项；仅测试生成的 `.mc-merge-tmp/`、`.qa-merge-tmp/`、`.coverage`/`coverage.xml` 属于旧工区。Git worktree 注册已同步移除，七个目录都不存在。清理后 CWP/RF/ET/SID/Dashboard 状态未触碰；MeetingConverter 主仓另观察到 `M .coverage`（文件时间 2026-07-09），本次未改该主仓文件。
- 另一批 **28 个无 Git 元数据的旧测试/临时目录**共 19,746 文件、518,410,131 字节。首轮删除因包含 PWF 引用的 `cwp-temp` 和 IQS 测试/审查资料，被平台自动审批要求先归档或确认；随后按该安全路径在本机生成 `Projects/retired-temp-archive-2026-11-15.zip`，包含原路径结构及逐文件长度/SHA-256 清单。重验源目录与压缩包全部 19,746 个文件 SHA 一致后，通过正常 PowerShell 操作删除全部 28 个原目录，逐一确认路径消失。归档为 65,318,184 B，SHA-256 `26a450d81299bb7c3fbaf8dca8a78d5407c99e194530d98a6cc050796d6a1546`；这批原目录逻辑净释放约 453,091,947 B。准确清单为 `_c1-review-runs`、`_ffjf_final`、`_ffjf_v1`–`_ffjf_v4`、`_tmp`、`.ruff_cache`、`cwp-temp`、`.iqs-deleg18-test-20261018a`、`.iqs-owner18-contract-a1`、`.iqs-owner18-observers-a1/a2/a3/portable`、`.iqs-owner18-phase-a1`、`.iqs-owner18-runtime-a1/a2`、`.iqs-owner18-test-a1`–`a5`、`.iqs-owner18-test-exact-final`、`.iqs-owner18-test-final`、`w18-holdout-scratch`、`w18-review-scratch-gold`、`w18-review-scratch-replay`。归档留在 Projects 根目录作为可恢复历史资料，不在任何 Git 仓库内。
- 明确保留近期目录：`.iqs-deleg18-test-20261018b` 和 `.iqs-scan18-test-20261018a` 内的 `attestations/` 最新时间为 11-13；Projects 根 `.pytest_cache` 最新时间 11-13；空目录 `_g3`、`_g4` 自身时间为 11-14、11-12。也保留有 PWF/独有材料关联的 `_du6tmp`（FF真实回放证据及原件副本）、`.du10-deps`、`_w20-runs`、`_fin-csc-02-external`、`_primary-csc-03-external`，以及 CWP/StockWiki/IQS/Dashboard 的活动或证据工区。
- 删除旧注册工区和 28 个 no-Git 临时目录后，Projects 顶层目录实测为 167 个；C 盘可用空间从归档前约 76.76 GB 到删除后约 77.21 GB。旧 11-14 目录清单数字不再作为实时数量。按一周界线识别出的临时目录批次已清理；其它更老但属于活动/未并线代码、原件或独有证据的目录仍按原因保留。

## 2026-11-15 — Projects 外包目录清理复查（进行中）

- 按用户最新指示把盘点扩展到 `Projects` 的全部 204 个顶层目录；发现原 `projects_directory_inventory.md` 的 63 个候选清单没有覆盖全部 `dashboard-owner-*`、IQS/RF lab 等目录，需补成完整当前清单后再退役目录。
- 已移除 CWP 内空的 `.worktrees/dashboard-p2-market-20261109`，以及 Projects 顶层 6 个经复查完全空、无 Git 元数据的目录（`_g5`、`_merge_checks`、`_r3a`、`_r3b`、`cwp-lanes-20261006`、`cwp-lanes-20261007`）；均为 0 文件 / 0 字节。
- 已清掉已完成且非 StockWiki/IQS 活动工区中的 1,267 个根级可再生 Ruff/Pytest/Mypy 缓存文件，合计 **38,610,263 B**。目标为 FF、RF、ET 容器、SID 容器和 Dashboard 的精确缓存目录；CWP 本轮相关缓存原本不存在，StockWiki 缓存因 owner 活动保留。
- 两处缓存无法由当前进程读取：`Projects/filing-fetch/.pytest_cache` 与 `%LOCALAPPDATA%/Temp/rf-merge-review-20260927/.pytest_cache`（PWF 旧测约 33 MB）。均收到 Windows `Access Denied`；未改 ACL、未用强制绕过、未删。
- 只读主仓现场与上次 PWF 有所不同：CWP `master@ac8841c55cb4` / `origin/master` 相等、tracked clean，但仍有 23,334 个未跟踪文件（约 347,518,173 B，集中于 `.mimosa`、`.planning`、`docs` 和 WorkBuddy）；RF 当前 2 个 tracked 变化是 2026-11-15 周度 T3 失败结果（`weekly_alert.jsonl`/`weekly_manifest.json`），应保留作诊断证据；StockWiki/IQS 当前仍分别有 28/13 个注册工区及大量 owner 状态数据，保持活动隔离。
- 初次扩展盘点时尚未删除含文件的外包施工目录；随后的一周界线清理结果见本页上方新增记录。已确认 SID 的 `cwp-cninfo-bounded-budget` 含 6 份真实 PDF 和运行日志、SID lineage backup 有唯一回滚材料，均按其交接保留。仍须逐目录对照 owner PWF、Git 并线、dirty/untracked 与独有证据，不能把该初查状态误读为当前完成状态。

## 2026-11-15 — CWP 正常推送恢复

- `git push origin master` 通过正常路径成功，GitHub 响应为 `7361aad82..0e741063f master -> master`，即当时本地 8 个待发提交全部进入远端。推送 delta 共 13 个路径，限于本计划文档/交接审查文件与一次性脚本删除，没有产品源码变更。
- 本仓 push fast feedback 识别出 9 个固定目标，实际 fixed smoke **18 passed in 6.58s**；输出说明更大的完整验证仍由 CI 执行。没有跳过 hook。
- 随后独立 `git ls-remote origin refs/heads/master` 因 `getaddrinfo() thread failed to start` 失败。发布结论依据 GitHub push 成功响应；不把失败的读取尝试写成 fresh remote 核验。该读取限制后来已记录在 docs-only PWF carrier `f58011ddd` 并通过普通 push 发布。
- 2026-11-14 的三次 Mimosa L3 拦截是准确的历史记录；2026-11-15 这次普通推送未被拦截。现有证据只能说明此次放行，不能说明 209/39/6 的告警已清零或平台规则已变。

## 2026-11-15 — PWF 状态载体完成发布

- 五份状态文档/交接记录已另作 docs-only commit，普通 push 返回 `0e741063f..f58011ddd master -> master`；推送后 `git rev-parse HEAD` 与本地 `git rev-parse origin/master` 均为 `f58011ddd`。
- 本次 docs-only carrier 按 push-hook 配置未运行产品测试；独立 review、`git diff --check`、11 个相对链接与 CWP/RFAudit 两个 handoff JSON 均已核验通过。跟踪文件工作区干净。
- 23,334 个 untracked 项按 `.mimosa`、`.planning`、`docs` 与 `.workbuddy-ai` 分类保留；没有批量清除运行/审查记录或用户资料。

## 2026-11-15 — Dashboard 最终收据及总控 PWF 对齐

- Dashboard 最终 receipt-only 独立审查 PASS，精确绑定此前已推送的 `8cd2d9477b60a6391dc5b1a4e3d0c94fb66dc6d0`；审查报告追加作为单文件 docs-only commit `3f83bb518ca782cb1bff495f7119fda7f3154097` 推送。fresh `ls-remote` 与 Dashboard 本地 HEAD 均为 `3f83bb5`，tracked worktree clean；仅保留 `.workbuddy-ai/` 和用户暂停的 E14 handoff。没有重跑产品测试或改产品代码。
- RF 最终收据审查见 [RF closeout review](review/rf-closeout-review.md)；RFAudit 的最终本地收口与无 remote 结论见 [handoff](review/rfaudit-closeout-handoff.md)、[review](review/rfaudit-closeout-review.md)。
- 已将 Dashboard 最终 HEAD、最终审查绑定和保留项写回本总控 `task_plan.md`，并明确其 owner lane 已完成；StockWiki/IQS 仍因各自 PWF 显示活动施工而只读隔离。
- 复读 StockWiki/IQS canonical PWF 后确认 OPEN 项仍在；本次 Git 元数据刷新均因 `Permission denied` 失败，未写入。11-14 的 HEAD/worktree 数仅保留为 last-known snapshot，dispatch 与 task plan 已明确这一限制。
- CWP 总控收尾变更仅限本计划的 `dispatch.md`、`task_plan.md`、`progress.md`、`findings.md`、已确认无引用的一次性 `.tmp-build-registry.py` 删除，以及 4 份 RF/RFAudit 审查/交接收据。`git status` 中其余大量 `.planning`、`.mimosa` 等未跟踪材料已逐类说明并保留，不做批量清理。
- CWP 总控 PWF/收据已按独审通过的九路径范围提交到本地 `master`（内容提交 `3b8fd0e8`；本条为后续 docs-only 状态载体）。标准 commit hooks 完成，产品源码类检查因本次无代码文件而跳过。平台远端最近成功观察仍是 `7361aad82`，此前 Mimosa L3 三次拦截正常 push，当前无门禁/扫描变化，不重复绕过尝试。父业务实施 goal 继续 paused。

## 2026-11-14 — RF / Dashboard 最终候选复核

- **RF**：当前 `main@f2215959d33abc76778342a95d39a8e38191da75` 与 `origin/main` 已核对一致。内容提交 `3ca6192` 只含 PWF、交接/运行证据及两份原字节 ledger，没有产品源码；从两条大幅分歧支线选择性纳入资料，没有将未完成实现整支并入。37 项 + 45 项责任测试通过；保留两条分歧 refs 与六组 `EVIDENCE_KEEP`。外部 `%LOCALAPPDATA%\Temp\rf-merge-review-20260927\.pytest_cache` 报 `Access Denied`，仍在原位，未改 ACL。`3ca6192` 独审 PASS，绑定内容提交；receipt-only carrier `f221595` 追加审查报告并更新 handoff/README 指针，其精确四文件范围、原报告字节前缀、JSON/指针和远端绑定也独审 PASS。Ruff/12 项 smoke hook 通过记录属于 carrier 推送检查及较早的 `1ea5008` 发布链，不作为 `3ca6192` 的测试收据。
- **Dashboard**：首次独立复核绑定 `9cb67502c8943a4857e48c50d8c2022049ce2a65`，结论 CHANGES_REQUIRED，列 7 项并均已修复。产品修复 commit `e8eaa85`，内容/PWF候选 `4d2def1`，独审发现 final pin / fixed schema 两处收据问题后分别由 `e58dc97`、`fc6dbe7` 修正；全量最终独审 PASS@fc6dbe7。`2e8320e` 推送后独审发现 status/delivery 仍 PUSH_PENDING、final.remote_head 仍旧；docs-only carrier `8cd2d9477b60a6391dc5b1a4e3d0c94fb66dc6d0` 已正常推送，fresh `ls-remote` 与本地 HEAD 一致，正等待该 carrier 的最终 receipt-only 复核。12/12 frontend、13/13 M3、1/1 synthetic GUI-2 E2E、typecheck/build、`uv lock --check`、`uv sync --extra test --locked` 通过，固定 E2E 目录 2 文件/17,286 B 按 SHA 恢复原样。E14 标为 `PAUSED_BY_USER`，连同 `.workbuddy-ai` 一并保留；本次未重跑产品测试。
- **总控 CWP**：新增 RF/Dashboard 状态仍属本次未提交 PWF 收口；尚未暂存或提交。RF、Dashboard 的内容与收据载体独审均通过，Dashboard 主线已推送。更新总表、运行文档/JSON/link 检查后由总控集中提交。CWP 早前 closeout 的正常远端 push 仍受 Mimosa L3 阻断，未尝试绕行。

## 2026-11-14 — 全模块收尾续办启动

- 用户要求再次逐模块对齐 PWF、清理未提交项、并入本仓主线、清掉确认无用的临时文件。按互斥写集并行启动 FF/ET、RF/RFAudit、SID/Dashboard 三条 owner lane；ROOT 负责 CWP。
- StockWiki 与 IQS 的实时 PWF 显示多条在途施工。已核对 StockWiki 有多个注册 owner worktree，IQS 的 11-14 进度仍有 OPEN 线；保留只读隔离，等其 owner 收尾后再处理，不覆盖活动改动。
- CWP tracked 源码目前无已知产品改动（仅本次删除一个一次性临时辅助脚本）；untracked 共 23,337 项：Mimosa hook 状态 10,010、`.planning` 执行记录 13,180、`docs/` PWF/审查证据 146、AI memory 1，不能按 untracked 一律回滚或删除。CWP 当前 PWF 记录 live remote 最近成功观测 `7361aad82`，Mimosa L3 曾阻断三次正常推送。
- 已将 CWP 根下 37 个旧的空测试/临时目录安全删除：逐一验证在仓库根内、不是注册 worktree、mtime 早于 2026-11-01、无任何文件后再删除；合计 0 文件/0 字节。根目录剩余临时输出与 docs/.planning 证据继续按引用关系分类。
- 清理另外 7 个无引用的旧 `.tmp_*.json` 诊断输出（16,301 B）、2 个 11-02 集成测试遗留 `tmp/osred/**/race.json`（20 B），以及一次性 `.tmp-build-registry.py` catalog 检查脚本（1,019 B，未发现生产调用）。小计释放 17,340 B；后者原先作为 tracked 临时文件，旧审计因当时清理范围不含它而留存，本次按用户明确的全模块临时产物清理要求移除。`git diff --check`/提交检查待本节点收口。
- 尚未处理的 CWP untracked 包含约 13k `.planning` 项与 10k `.mimosa` hook-state 项、143 份 du11 review 文件及本计划交接收据。它们包含大量唯一 PWF/运行/审查证据或当前 hook 状态，不按目录整体删除；需要先筛出可复现缓存/重复历史，再逐项留收据或清理。

## 2026-11-14 — CWP 可重建缓存收尾

- 清理仓库根下可重建的 `.mypy_cache`、`.pytest_cache`、`.ruff_cache`、`__pycache__` 共 1,682 个文件、36,929,089 字节；删除空 `tmp/pdfs` 与 `tmp` 两级目录。按精确仓库内路径核验后移除，复查均不存在。
- 保留 `.codegraph`（5 个索引文件，222,092,273 字节）与 `.venv`，前者是当前代码结构索引、后者是项目环境；不以“可重建”作为删除它们的充分理由。保留 `.mimosa` 活动 hook 状态、`.planning` 执行数据、PWF/审查材料、原始资料与 WorkBuddy 记忆。
- 文档检查：`git diff --check` 通过；`python -I docs/plans/module-pwf-reconciliation-2026-11-14/review/check_links_closeout.py` 检查 11 个既有 handoff 链接，0 个断链。当前未跑产品测试，因为本轮 CWP 变更只有 PWF/临时脚本删除/缓存清理。

## 2026-11-14 — FF/ET owner lane 收尾

- **filing-fetch** canonical `PLANNING_STATUS.md` 已更新；`main@1dfd81836794ec3bf73b41014a98714e97299ae8` 与 `origin/main` 相同。删除 12 个已结案、clean、提交均为 main 祖先的完成工区（DU10/DU11/DU6/DU67/DU8 集成与矩阵/R1 boundary 与 local/S3/SourceRef-v2/W19/W20）；移除 9,902 个派生工作副本文件、138,465,789 B。只移除了 worktree，不删除分支 ref 或 Git 共享对象。保留剩余 23 个活动/证据/非 FF owner 工区、3 条证据分支、`.ff_jobs`、Mimosa/WorkBuddy 状态及 API key 文件。
- FF 提交 `1dfd818` 已推送；正常 push hook 执行 daily Ruff 和 11 项 fast tests，全部通过。PWF `git diff --check` 通过。
- **earnings-transcripts** canonical `task_plan.md`/`progress.md`/`findings.md` 已更新；`main@50d91900df2436a06ff01985d2984cb048ea4d08` 与 `origin/main` 相同。删除 47 个可重建 Python/test 缓存文件、815,153 B；保留 8 个当前 Mimosa/WorkBuddy 未跟踪项。提交 `50d9190` 已推送，PWF diff-check 通过；本轮无源码变化，不重跑产品测试。既有 `transcript_audit --write-receipts` 冲突退出码缺陷如实保留为后续事项。
- FF/ET 的对应本仓 PWF 和 Git 状态已由各自 owner 核验；没有把非祖先证据 refs 或仍有 owner 的工区误并入。

## 2026-11-14 — RFAudit closeout 交付

- RFAudit `main@50d8ab6fa99db8920358c97f63be4afff8299243` tracked clean、无 remote；21 个本地 refs 均为 main 祖先，18 个注册 worktree 收敛为主仓 1 个。已按 owner 收据删除 17 个结案工区，4,264 个文件/67,449,856 B；W08 唯一未跟踪审查包已先归档、校验再移除工区，分支 refs 均保留。
- canonical PWF 唯一入口为 `docs/plans/company-pool-cycle-2026-10-09/task_plan.md`。RFAudit owner 交付的 [handoff](review/rfaudit-closeout-handoff.md)、[JSON](review/rfaudit-closeout-handoff.json) 与[独立审查](review/rfaudit-closeout-review.md)均绑定最终 HEAD，PASS；JSON/link/diff-check 通过。本仓无 remote，未尝试创建或推送。
- 本 lane 已结束；后续业务唯一下一步仍由 RFAudit canonical PWF 指向 `r4-owner-closure-20261102`，不由本清理任务自动启动。

## 2026-11-14 — StockWiki/IQS 在途工区只读复核

- **StockWiki**：实时 `master@0450506fc94adbfecd33001c244221a42ba0a00d`；当前未配置 remote；28 个注册 worktree、39 个本地 branch。主仓 `git status --porcelain -uall` 有 41 个 untracked 项（`.test-runs` 34、`data` 4、`runs` 2、`logs` 1）。根 `task_plan.md`/`progress.md` 记录 SW-1/SW-2、Dashboard 与其他并行交付仍有开放的数据/owner 检查；没有清理或合并这些活动 refs/worktrees，也没有写入此仓。
- **IQS**：实时 `master@dab872478902fea2a17496091d4871149ba9f2b2` = `origin/master`；13 个注册 worktree、13 个 local branch。主仓有 22,658 个 untracked 状态项，主要是 `.mimosa` 16,267、`docs` 4,200、运行中/历史 `.tmp-*` 目录与 `.worktrees` 内容。PWF 最新明确写出的 producer push 为 `a8df5b99`，live main/remote 随后的 `dab872` 尚未在其同一进度记录对账；同时 canonical PWF 仍列多条模块实施和组合验收 OPEN。未清理/合并任何这些在途工区、文件或 refs，也没有写入此仓。
- 这两仓不是“已收尾”：保持只读是因为其 owner PWF 与实际隔离 worktree 仍显示并行施工；待各 owner 交最终 HEAD、测试与独立复核后，再按本卡续做清理与并线。上面的 HEAD/count 是当前复核快照，不把未跟踪项直接判为临时垃圾。

## 2026-11-14 — CWP 历史运行数据二次只读审计

- 独立 reviewer 对 `.planning` 文件类型、目录、mtime、PWF引用与生成物做第二轮只读审计：没有找到一批值得删除且同时能证明可重建、无当前/历史 PWF 依赖的文件。未发现可批删的 `.pyc`、标准缓存目录或 OS 临时碎片；空 scratch 为 0 字节。
- `.planning/r1-w09-root-integration-20261023/v3/outputs` 的 4 个 JSON/3,495,374 B 被现有 hygiene review 明确要求保留；`.planning/du8-ff41-root-20261016/**/artifacts` 的 205 个文件/约462,525 B 在精确收据确认前保留；`shared-reading-production`（5,638 文件/69,932,837 B）包含当前运行状态、SQLite/WAL 与恢复数据，不能按历史产物清除。
- 因此本轮仅清理已确认可重建的根缓存与明确旧 `.tmp` 文件；CWP 剩余 `.planning` / `.mimosa` 大体积是未归因运行/审查材料，不宣称已逐项清空，后续须由对应 owner 按收据继续核实。

## 2026-11-14 — 初始化

- 建立总控计划，目标是统一各模块 PWF 入口、未提交/未并线状态、Projects 临时工区处置以及后续主线责任。
- 确认当前长期 `du11-source-closure-2026-10-18` goal 为 paused；不恢复其代码实施。
- 沿用最新 owner 边界：每个模块 owner 只在本仓清理、测试、提交、并线、推送；ROOT 不跨仓写代码或操作 Git。
- StockWiki 标记为并行施工隔离，暂不检查/修改其代码、计划和工区。
- 下一项：对不冲突模块进行只读 PWF/仓库/工区盘点，并在 findings 中补齐唯一入口与确切状态。

## 2026-11-14 — 模块快照与 owner 卡

- 只读盘点 CWP、FF、RF、ET、SID、Dashboard 和 RFAudit；StockWiki 与 IQS 因在途任务列为暂缓，不访问 StockWiki 工作区。
- 找到 63 个与模块名前缀匹配的 Projects 顶层目录。该计数不是全 Projects 目录普查，所有候选路径仍待其 owner 按 PWF/Git/config/data 逐项分类。
- 发现主要 PWF 过期/冲突：FF 根入口仍指旧 fcap，RF MB-RF handoff自相矛盾，ET根计划引用旧RF状态，SID G4保留陈旧路由待办，Dashboard D00快照落后10天，RFAudit主循环多段Next Step互相覆盖。
- 新建七张互斥 owner 卡；写集分别为 CWP、FF、RF、ET、SID、Dashboard、RFAudit。每卡要求模块 owner 更新本仓PWF、处理本仓 branch/worktree、清理本仓已核实临时目录、规划后续主线，并交一次独立最终审查。
- 独立初审发现 PWF 清单路径拼写、三卡不够自包含、CWP两个worktree物理位于Dashboard目录且dirty不能等同仍活动。ROOT已修正链接，补齐RF/ET/RFAudit目录路径，CWP标为`UNCLASSIFIED_HOLD`并禁止操作Dashboard物理路径；最终复审又要求将ET目录数从6改为7并补齐未知路径分类，全部修复后最终复审PASS，记录见 [审查报告](review/owner_cards_review_20261114.md)。
- 本阶段未改任何外仓文件或Git状态，未删除Projects目录、未并线，也未运行产品测试。当前父业务目标仍 paused。

## 2026-11-14 — 单卡独立交接复核

- 按用户要求逐张检查七张可执行卡是否能脱离总派发表独立交给 harness。发现原卡虽有范围、快照、步骤和验收，但 canonical PWF 起点、hand-off 文件落点、处置状态词义以及独立 reviewer 是否必须为另一 agent 不够明确。
- 已把这些上下文补进每张卡，分别写明目标仓、PWF 入口、固定 handoff 与 review 文件名、状态分类、以实时目标主线为准，以及由未参与实施的 agent 按最终已发布 HEAD 审查、问题修复后复核。
- 只读确认了所引用的 PWF 入口在七个目标仓均存在；本仓 `git diff --check` 通过。未访问 StockWiki/IQS 工区，未改外仓、未跑产品测试、未提交或推送。
- 首轮独立复核指出 ET、RF、SID、RFAudit 仍让执行者选择唯一状态入口；已将四处固定到具体现存文件，并明确旧入口回链。独立 reviewer 对更新后的七卡复核 PASS；ROOT 另只读确认所列 PWF 入口存在。各 lane 实施完成时仍必须按卡要求对最终提交做独立最终审查。

## 2026-11-14 — CWP lane 收口（cwp_closeout 卡执行）

- 实时重核基线：`master@7361aad82` = `origin/master`（卡面快照 `1f9f3dcf3` 之后的 2 个 docs 提交已计入）；tracked clean；8 个注册 worktree、13 个非祖先 refs、1 个 stash（`18ac0d0562`）与卡面计数一致。
- 13 个非祖先 refs 全部归因：11 个 `ABSORBED`（T-READ/T-CANON/T-B33/T-B34/T-N4/T-CONFIG 能力已由 [MB-CWP 卡](../mb11-cwp-2026-11-11/handoff.md) 移植进 master，T-W13 历史文档已补回；master 路径逐一实测存在），2 个 `UNCLASSIFIED_HOLD`（`codex/d00-return5-cwp-audit`、`codex/dashboard-cwp-b34-prospectus`，按卡步骤 2 不得推断；工区物理位于 Dashboard 目录）。ABSORBED refs 一律保留：其提交携带主线没有的历史 handoff 文档，删除会使独有历史不可达。
- 8 个 worktree 全部归因：主仓 `ACTIVE_KEEP`；4 个 CWP 侧工区 `EVIDENCE_KEEP`（唯一 .planning 审计材料、已归因未归档的 M3/W04 WIP、clean-filter 伪差量 + R1 resume 证据）；2 个 Dashboard 物理工区 `UNCLASSIFIED_HOLD`（只读记录 branch/HEAD/dirty）。
- 四个额外 Projects 顶层目录全部 `EVIDENCE_KEEP`：et-live-20261004（1 文件验收记录）、gates（9,700 文件/262,499,631 B 观测产物，可重建性未证实）、r1-local-observation（即注册工区）、storage-audit-20261003（26 文件审计原始扫描）。
- 本轮清理为零（0 路径/0 文件/0 字节）：无一项同时满足"owner 已完成+源码在主线+无唯一证据+工区 clean"四个移除条件；历史清理收据已在 module-boundaries review 目录，不重复执行。
- 文档-only 校验：`git diff --check`、handoff JSON 可解析、相对链接核验（check_links_closeout.py）全部通过。
- CWP 唯一下一步：du11 P1 业务摘要质量修正（66 条 claim 展示、26 个冗余任务、披露载体/承诺人混用），通过后复验缓存恢复与 RF 采用；父计划公司循环保持 paused。
- 交接：[cwp-closeout-handoff.md](review/cwp-closeout-handoff.md) / [cwp-closeout-handoff.json](review/cwp-closeout-handoff.json)；独立审查结论见 [review 目录](review/)，绑定候选 HEAD。FF/RF/ET/SID/Dashboard/RFAudit 各 lane 仍等其 owner 按对应卡执行。

## 2026-11-14 — 七条施工卡 ROOT 查收与修复

- 独立 reviewer 对七条 handoff、最终分支、审查/测试证据及远端状态做只读查收。结果：FF、RF、ET、SID、Dashboard 的 owner 内容已在各自主线上且远端 SHA 对齐；RFAudit 在 main 收口、按卡无 remote；CWP 内容审查 PASS，但 `master` 的本地收尾提交仍未推送。
- 收据修复：RF handoff 的 `final.head/remote_head` 原错停在 base `ec5ba004`，report §7.4 又把已提交 C4 写成 pending。已改为内容 tip `b88818da`，将过期语句标成历史并补 §8；提交 `b082a129`、`1ea50082` 已推送至 `origin/main`。独立复核 `b88818da..1ea50082` PASS。推送 hook 自动运行 ruff 和局部 smoke，结果 `12 passed`。
- 收据修复：SID JSON `independent_review.reviewed_head` 原仍指首轮 `2fd2294`（CHANGES REQUIRED）；改为最终 checklist PASS 的 `99a32bda`，保留内容 tip `73f4369` 与 carrier 区分。提交 `a31ae376`、`85f39ec` 已推送至 `origin/v2-clean-rewrite`；JSON 与 diff-check PASS，独立复核 PASS。
- 收据修复：Dashboard owner acceptance 原把 CWP 表述成完全闭环，并把 Dashboard 远端写成旧 `9c64723`。修正文档为 CWP push BLOCKED、Dashboard D00 远端 `631fa59`，并区分后续 acceptance 记录；提交 `4477eb9` 与父提交 `6d5c3a0` 已推送至 `origin/main`。JSON 885 条记录可解析，diff-check PASS，独立复核 PASS。
- CWP handoff 增补平台阻断详录并提交 `d6c873c78`。随后总控 PWF 四文档经独立复核后提交 `83f5b75a6`；两批提交均在本地 `master`。推送前 Mimosa L3 三次全仓扫描拦截（报告摘要 209 high / 39 medium / 6 low）；此门先于 `.githooks/pre-push`，不得绕过。当前 `git ls-remote` 另因 `getaddrinfo() thread failed to start` 不能刷新，故不声称远端已推进。
- FF 最终 `c2aec91`、ET `c777bf1`、RF `1ea50082`、SID `85f39ec`、Dashboard `4477eb9` 的 live remote 已核验分别等于本地 tip。RFAudit 最终 `50d8ab6` 本地 clean、无 remote，交接/review 位于本计划 review 目录。
- RF 仓的 scheduled `assurance/runs/daily_alert.jsonl` 在本轮出现一条 2026-11-14 运行记录（outcome `not-ok`）；已识别为运行数据并保留，未暂存或带入收据提交。
- 当前阶段：PWF 入口与 safe-cleanup disposition 已完成；保留目录因 active/evidence/跨 owner 理由未全部删除，不能称“物理上每仓只剩一个目录”。唯一阻塞是 CWP 远端发布；主业务 goal `du11-source-closure-2026-10-18` 继续 paused。
# 2026-11-15 — CWP 边界扫描器第二轮表达式/作用域修复

- 从第一轮 lambda 闭包修复继续审查表达式出口。最小反例证明外部模块对象仍可通过条件表达式、`and/or`、lambda 条件体、容器/生成器推导、`yield/yield from` 和 walrus alias 漏过简单名字扫描；测试先 RED，再改 `_reference` 与 visitor 处理转 GREEN。
- 独立复审进一步发现推导式循环变量泄漏到外层作用域会错误遮蔽已有模块绑定，并可能造成假阴性。修复按 Python 作用域分析：首个 iterable 在外层求值，循环目标与其余表达式隔离；循环目标不写回，walrus 绑定按语义向外层传播，并保守考虑推导式零次/多次运行。
- 正反例覆盖模块对象直接/嵌套表达式逃逸、lambda 参数遮蔽、公开 callable/opaque-port 通过、`and/or` 常量短路、dict/set/list/generator comprehensions、yield、yield-from、walrus alias、零迭代保留旧绑定与循环变量不外泄。
- 最终 `tests/contract/test_layer_public_boundaries.py`：ROOT **86 passed / 13.28 秒**；独立 reviewer 对最终文件复跑 **86 passed / 12.96 秒**；受影响 Ruff 通过。reviewer 未改文件，结论 PASS。提交 `b1e948276860ee0386e47253ce32479a4fa41919` 已推送，fresh `ls-remote`、本地 HEAD 与 `origin/master` 一致。完整 GitHub Actions CI 未核验；本改动仅限测试支持扫描器和合同测试，不改生产代码。
- 外仓只读快照：RF `main@f2215959` 的 11-15 weekly run `20261115T084227Z` 为 T3 `not-ok`，四个 FF 下载 E2E 在 `company-wiki ensure` 阶段退出 1，`downloads=0`；可见日志没有 ensure 内部原因。triplet 为 FF `1dfd818…` / RF `f2215959…` / CWP `0e741063…`，所以这不是本次 CWP 测试扫描器提交的回归证据。RF owner 需把两条 tracked weekly 文件与失败原因写入 RF canonical PWF。
- StockWiki `master@0450506`，未配置 remote；根 `task_plan.md`、`progress.md` 修改时间仍为 11-08 09:28/10:46。当前只读 `git status` 返回 “must be run in a work tree”，不能据此断言干净；StockWiki owner 在对齐根 PWF 时应核对 Git 工作树并记录。ROOT 未修改 StockWiki/RF。
- 后续仍是有限 M3 收口：待两位 owner 补齐 canonical PWF/工作树事实，ROOT 再绑定九仓精确 refs 与已通过证据。CWP 当前模块边界静态合同有明确范围，不声称是运行时隔离；完整远端 CI 也仍需精确 SHA 结果。

## 2026-11-16 各模块 PWF 入口对账

九个主模块与四条独立依赖链已按当前 Git 引用和本仓 canonical PWF 对账，详见 [逐仓交接](../module-boundaries-2026-11-11/owner_plans.md)。StockWiki `b4ca912` 已更新三组子计划，IQS/Dashboard 的进行中投影事项由各自 owner 接续。此阶段整理的是计划、接口与交接。临时目录处置保留既有清理收据和当前归属。
