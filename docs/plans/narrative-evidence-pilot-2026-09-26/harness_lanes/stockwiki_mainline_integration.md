# StockWiki 独立施工卡：已完成 reader 与 identity lanes 并入主线

> **可直接交给一个 StockWiki harness。**唯一写入仓库：`C:\Users\郑曾波\Projects\StockWiki` 的新集成 worktree。仅整合本仓已完成的 SourceExport v2 reader 与 W02/W03 identity snapshot/mapping；CWP、IQS、RF、FF、ET 只读。本卡不扩展产品范围、不替 IQS 关闭 G2b，也不触碰 CWP 当前 E5/E6 代码工作树。

## 目标和范围

将两个已完成、各自有提交且当前未进入 StockWiki `master` 的功能线安全汇入本地 `master`，按本仓的单次大节点流程运行聚焦测试和一次 `scripts/check_all.sh`，形成可复核的主线状态。保留两个源 worktree/分支，直到集成结果确认；不做清理或归档。

本线包含：

- SourceExport v2 reader：`codex/source-export-v2-reader`，观测 HEAD `0b40683`；
- W02/W03 identity snapshot 与四态 mapping DTO：`codex/identity-snapshot-w02-w03`，观测 HEAD `ae11135`，产品实现提交 `a525802`；
- StockWiki 本仓测试、CLI 注册、必要的 PWF 收尾记录。

本线不包含：CWP/StockWiki 实际 producer 的新合同、selected evidence、full sync/weekly、身份数据批量回填、生产身份库迁移、IQS 代码修改、G2b 的 trusted receipt/market registry 补造、CWP E5/E6、生产 Worker、原始资料或派生文件清理。

## 派发时已核实的基线（2026-09-30）

- StockWiki 本地 `master`：`8590b0e`；可见唯一未跟踪项为根目录 `.claude/`，必须保留，不能清理或纳入本任务提交。
- Reader worktree：`C:\Users\郑曾波\Projects\StockWiki-v2-reader`，分支 `codex/source-export-v2-reader@0b40683`，工作树干净，基于 `5bb68f6`。
- Identity worktree：`C:\Users\郑曾波\Projects\StockWiki-identity`，分支 `codex/identity-snapshot-w02-w03@ae11135`，工作树干净；W02/W03 实现在 `a525802`，基于 `dd8912f`。
- 两条功能线相对共同主线的文件清单没有重叠；identity 修改 snapshot/mapping 及其测试，reader 修改 reader/CLI、reader 测试和 CWP v2 fixtures。主线 `8590b0e` 是 identity 施工卡/交接记录提交。
- StockWiki 工程验证规则已简化：开发迭代跑受影响测试；集成大节点只运行一次 `bash scripts/check_all.sh`，其中全套 pytest 已由 coverage 包装运行一次，同时检查 Ruff、73% 总覆盖率、`stockwiki/ui.py` 40% 覆盖率和 validate-framework。不要再额外跑一轮全量 pytest。
- **G2b 当前已知阻塞：**W02 snapshot 有 scope-attestation ID 和 source bindings，但 StockWiki 当前持久模型/公开 snapshot 不提供 IQS 所需的 owner identity-receipt 实体与 market-registry 投影。IQS handoff 要求由 StockWiki 公共接口返回这些真实记录。不得自造 receipt、伪造 market registry 或把 `scope_attestation_id` 当成完整 receipt。该阻塞不妨碍把已完成的两条 StockWiki 功能线整合入主线；G2b 仍为 pending。

执行时必须重查 refs、worktree 状态和活动 harness；本节 SHA 是定位线索，不能替代实时 Git 事实。若两个源 worktree 有未提交改动、提交已变化、owner 仍在写，先保留现状并报告，不 reset、不 clean、不覆盖。

## 单仓施工步骤

1. **锁定可写范围。**检查 StockWiki `git worktree list`、三个 worktree 的 `git status --short`、当前主线 HEAD 和相关 PWF。确认 reader 与 identity owner 均停写，两个功能分支的实现与测试已提交；识别并保留 `.claude/` 及所有不属于本线的 untracked 文件。若状态与上述观测不同，以现场为准，先分类，不猜测、不删除。
2. **建立集成分支。**从执行时最新本地 `master` 建立一个新的 `codex/stockwiki-lane-integration` worktree。不得在两个完成 worktree 上继续改功能，不更新/重置它们。先将 reader 分支正常合入集成分支，再将 identity 分支正常合入；保留原提交历史。不得 cherry-pick 后删源分支、force push、`reset --hard` 或使用通配符清理。如果意外出现文件冲突，逐文件核对语义；冲突超出这两条功能的已知文件范围时停止并报告。
3. **聚焦回归。**在集成 worktree 跑下列受影响测试（如果实际测试路径有变化，先按 Git 变更清单确认等价文件，不得静默漏测）：

   ```powershell
   python -m pytest -q tests/test_source_export_v2_reader.py tests/test_source_export_v2_cli.py tests/e2e/test_cwp_source_export_v2.py tests/test_identity_snapshot.py tests/test_identity_mapping.py tests/test_quick_scan_store.py
   ```

   reader 测试覆盖 pathless SourceExport v2 wire 校验、真实字节 verified-open seam、文本 locator 回放和 P06 PDF manifest；identity 测试覆盖真实 QuickScanStore serializer、snapshot hash、AnalysisSubject、`null/unknown/ambiguous/mapped` 和畸形绑定拒绝。聚焦测试任一失败先定位归属；不得靠放宽校验或跳过新测试让合并通过。

4. **运行一次集成大门。**聚焦测试全绿后，从集成 worktree 根目录只运行一次：

   ```bash
   bash scripts/check_all.sh
   ```

   该脚本包含完整 pytest/coverage、真实 workspace/data-contract、Ruff、覆盖率阈值和 validate-framework；按 StockWiki `AGENTS.md` 记录完整输出、退出码和耗时。若失败，修复本线引入的问题并重跑受影响测试；只有更改后再次达到大节点条件时才重跑完整门，不为同一未变代码重复运行全套。

5. **状态与数据核对。**保存集成前后 Git 状态和受影响生产身份/研究状态的只读摘要；确认测试生成的临时 DB、WAL、coverage/cache 只在本线测试根产生，完成后测试根恢复原样。验证原 reader 与 identity worktree 仍干净、原 refs 未移动，`.claude/` 未被触碰；执行 `git diff --check`。不读取/写入 CWP 或 IQS 的数据库和生产文件。

6. **本地并入与交接。**大门全绿后，在 StockWiki 本地 `master` 上用正常 Git merge 纳入集成提交；不推送远端（当前无已确认远端目标）。不删除源分支、worktree 或 `.claude/`。报告最终 master HEAD、合入的两个源 HEAD、测试命令/退出、测试根恢复、剩余未跟踪项和 G-B/G2b 状态。若本地 master 自执行期间前进，先把集成分支正常更新并重跑受影响验证，不能强行覆盖。

## 真实 IQS/G2b 的处理边界

- 本线不把 IQS 的 identity CLI 校验当成 StockWiki 的数据真实性证明。G2b 只有在 StockWiki 公共接口可以从其 owner-controlled store 读出被引用的 scope/issuer receipt、market registry 和 source-binding 记录，并能由真实 serializer 输出 exact request 时才可转绿。
- 如集成后发现真实记录已经由某个正式 owner/API 提供，可只做只读定位和交接：给出来源表/公开接口、字段映射、版本和可重现命令；把证据交主指挥与 IQS owner 后另开边界清楚的 G2b 任务。
- 如果记录仍不存在，本线以明确缺口结束，不添加只为满足 IQS 测试而造出的持久记录或常量注册表；由主指挥决定是否先设计真实数据 owner 与生命周期，再单独派发实现。
- StockWiki SourceExport reader 的本仓测试通过不等于跨仓 G-B 完成。总指挥仍需在 CWP 只读生产者可用时运行真实 CWP producer→verified-open→StockWiki reader E2E；本线不得修改 CWP。

## 自动验收与交付

完成条件：两条已完成产品线均进入 StockWiki 本地 `master`；reader/identity/QuickScanStore 聚焦回归通过且无新增 skip；单次 `scripts/check_all.sh` 退出 0；改动 diff check 通过；测试根与所有原有 worktree 状态恢复；`.claude/` 等非本线文件保留。

交付记录仅需列：合入前后 master HEAD、两个功能分支 HEAD、实际合并顺序、受影响测试与整套门结果、隔离根前后状态、未跟踪文件归属、G-B 是否已由真实 CWP CLI 验证、G2b 是否仍因 receipt/registry owner 数据待建而 pending。无需人工 review receipt 或额外逐项签收。
