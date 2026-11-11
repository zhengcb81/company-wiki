# RF / StockWiki / Audit / Dashboard 逐引用与工区核销独立审查

日期：2026-11-11。审查者：ROOT 的 research 独立只读子任务。范围：这四仓所有本地/远端分支、额外 tag/replace/stash 引用、登记 worktree、tracked dirty，以及部署支线与当前 main/master 的关系。

## 1. 可立即执行的结论

1. Dashboard 当前边界修复没有剩余阻断：公开 open_original 代理、可传播 traceback 的 OwnerPortError、隔离测试根、有限静态边界扫描均有明确用途。原来把所有 dynamic import 一律禁止的问题已修正；它只能证明所列静态模式，不是全运行时解耦证明。由现有 owner 完成有限回归与提交，不创建竞争施工包。真实 owner 原文流组合套件另有已确认入口缺口，见第 6.2 节，未标为通过。
2. Dashboard 4b30e1d9 / 8e3231c3 两个适配器提交可以接收，真实 public owner 合同支持其参数形状。本报告完成前已经观察到 main 新提交 5a16ca7（原文流测试）、c56e9ce（language 列表）、0addea2（reconcile 配置）。这三项由审查期间另一 harness 并发提交到 main，ROOT 仅观察并保留，并非 ROOT 或本审查完成的并线；不再列作当前主线“仍未接收”。完整 before 表保留原值供追溯。
3. RF 和 StockWiki 的 release 家族有真实未吸收的公开接口，但各自 main/master 也有新工作。不要整体复制 release 树或逐个重复合并其所有祖先。最小参考顶点是 RF B37 release、StockWiki C38 release，加 StockWiki d00-b03 的窄增量；先核对所需公开接口，再按文件/合同承接。RF 新 job recovery/concurrency 与 D4 source port、StockWiki 当前来源 consumer 和 F05 不能倒退。
4. RF assurance 四项是调度生成证据，不是源码：先保存原字节和失败信息，再由 ROOT 精确 restore 四路径。研究 authoring 草稿、旧审计独立 PASS、B03 repair_chain 草稿必须保留或归档，不能当缓存直接删。
5. Audit 22 个分支引用均是 main 祖先，没有独立未并线代码。StockWiki/Audit 继续 verification-first，不制造新实现卡。
6. 配置指向的 RF B37 / SW B34 / CWP B33 根暂保留。配置不证明现有进程正在使用它们；换根须通过对应 public CLI / read-only black box 再处理，不能随分支核销顺便切换生产数据或执行 identity repair。

## 2. 证据范围、基线与方法

冻结清单：[inventory_before.json.gz](C:/Users/郑曾波/Projects/company-wiki/docs/plans/module-boundaries-2026-11-11/review/repo_reconciliation_20261111/inventory_before.json.gz)。ROOT 已报告六个存在 origin 的仓 fetch 成功，无新增输出；StockWiki、Audit 没有 remote，本审查没有联网或猜建 remote。所有 refs / worktree 表以 before 为基线；ROOT 在本轮执行的动作另列，避免把一个动态工区的前后状态混写成“全干净”。

| 仓 | 冻结目标 | 分支/remote 引用 | 已为目标祖先 | 非祖先但 cherry 全为 - | 有 cherry + | 登记 worktree |
|---|---|---:|---:|---:|---:|---:|
| RF | main b005a179280ee19695578bdba9427b4dd44cdd73 | 96 | 77 | 1 | 18 | 62 |
| StockWiki | master 12c441e86282135b49120112dcf21c17509bbdd0 | 36 | 18 | 0 | 18 | 30 |
| Audit | main 3589b69cb9d28d7395607ce4fe689025b9acee96 | 22 | 22 | 0 | 0 | 18 |
| Dashboard | main b707473a1166d3f8740170dad77cb21aa09863ce | 95 | 61 | 17 | 17 | 80 |

共 249 个 branch/remote 引用（含 remote HEAD 别名），另发现 RF 7 个 annotated tag，peeled commit 全是 RF 冻结 main 祖先；其余三仓无 tag。四仓均未发现 refs/stash 或 refs/replace。7 个历史 release tag 应保留，不因“已吸收”删除。另逐一覆盖 before 的 190 个登记 worktree。

只读操作包括 git for-each-ref / log / show / diff / ls-tree / merge-base / rev-list / cherry、索引 blob 对照、指定文档和源码读取。外仓 worktree 状态在沙箱 Permission denied 时按 ROOT 授权使用宿主只读 Git。未更改源码、作者工区、索引、ref、配置；没有运行测试、采集、LLM、安装、付费调用，也没有读取密钥或原件内容。唯一写入是本报告。

判定规则：

- A：tip 是目标祖先，不需要再并线。并不意味着该 worktree 的 dirty/untracked 可以删除。
- P：非祖先，但 git cherry 所列非 merge 补丁全部为 -，不重新应用这些补丁。merge resolution 与独有文档仍按具体证据核对；P 不声称整个树逐字一致。
- +：补丁未等价，不自动等于未交付功能。再用 descendant/包含关系、当前 product blob、主线整合提交、PWF/handoff 区分真实差额、已改写吸收、文档和旧原型。
- ahead 是目标..tip 的提交数，包含 merge；+/- 是 git cherry 的非 merge 补丁数，所以两者不要求相等。
- trackedCount=0 仅表示 Git tracked 状态；不代表没有 ignored、原件、运行数据、untracked 或部署引用。ROOT 负责原始清单逐类空间/保留核对，本报告不替它作“全删”许可。

## 3. RF：真实余项与边界

### 3.1 release 拓扑及最小承接单位

c1e27877 同时是 d00-return5-rf-audit / dashboard-rf-b31-release / dashboard-rf-deploy-root 的 tip。B37 release 28d646d3 已包含这一家族以及 identity bridge、report catalog、report compare、B34 alias/catalog/source/publication、B35 lineage、B37 scope 的产品工作。B34 release 7f1d3a99 相对 B37 仅留下末尾 release 文档；不要为该文档再整合一遍产品。B37 publication a5afa6d2 的提交不是 B37 的字面祖先，但其发布实现经 80284 的适配进入 B37（管理 CLI 合并调整），不能因 cherry 仍显示 + 就再套整包。

B37 handoff：28d646d3:docs/handoffs/dashboard-B37-publication/INTEGRATED_RELEASE.md 第 3 行明确是独立部署 checkout，未并入 owner main；第 5 行记载 scope/publication 整合与管理 CLI 三方合并；第 9 行的 173 passed / 1 skip 是旧次运行证据；第 15、19–21 行维持 E14 paused 与 immutable binding 的范围，未宣称全业务闭环。不能把历史测试数当本轮通过。

RF 冻结 main 已另行拥有：

- ff1c69e0：durable jobs public owner CLI；
- bdef9fd3：owner report catalog / native admission；
- cd24976a：跨进程 jobs/catalog recovery；
- b005a179：completed job import 到 report catalog；
- D4 后续 7688226d / 7e8a46cd：可替换 reader port 到 prepared source 消费。

B37 与 main 共同祖先为 695dc749；冻结 main 侧 46 个、B37 侧 58 个提交不同，不能 fast-forward。B37 的 19 个产品路径中，4 个 tip blob 已与 main 相同、9 个同名不同、6 个 main 不存在（见下表）。不存在的 6 个 compare/scope 模块证明存在待承接接口；同名不同的 9 个必须保留当前 main 行为逐项适配，不能 restore 整文件。

RF job facade d347c4ab 建于 B37 之后，但旧 handoff 的“main 没有 job facade”已经过期。当前 main 与它的 scripts/rf_job_facade.py 有 413 行量级差异，且当前有 concurrency/recovery 测试。故 facade 分支不再整体并入；仅对 main 尚缺的合同做 fixture 验证，如有必要再提最小补丁。

rf-input-prep-01 4ab5ef4d 相对 facade 的 118 路径增量都在 .planning/rf-input-prep-01/，是部分研究交付证据，MongoDB 已做、Alibaba/catalog 标 NOT_RUN。它不增加 runtime 算法，也不是 MB 解耦退出条件。保留到原研究计划，不能以“补并线”为由再次付费跑预测或把研究质量列作 MB 阻断。

### 3.2 RF 最小产品差额（以 B37 release 为参考）

| 分类 | 路径 |
|---|---|
| main 已有，需保留新实现逐项适配 | scripts/company_wiki_source_v2.py |
| main 已有，需保留新实现逐项适配 | scripts/contracts/document.py |
| main 已有，需保留新实现逐项适配 | scripts/report_catalog.py |
| main 已有，需保留新实现逐项适配 | scripts/report_catalog_identity_cli.py |
| main 已有，需保留新实现逐项适配 | scripts/report_catalog_identity_resolver.py |
| main 已有，需保留新实现逐项适配 | scripts/report_catalog_research_attempt.py |
| main 已有，需保留新实现逐项适配 | scripts/report_catalog_research_identity.py |
| main 已有，需保留新实现逐项适配 | scripts/report_catalog_research_publication.py |
| main 已有，需保留新实现逐项适配 | scripts/report_catalog_source_alias.py |
| main 尚无此路径，验证公开合同后承接 | scripts/report_catalog_compare.py |
| main 尚无此路径，验证公开合同后承接 | scripts/report_catalog_compare_cli.py |
| main 尚无此路径，验证公开合同后承接 | scripts/report_catalog_scope_binding.py |
| main 尚无此路径，验证公开合同后承接 | scripts/report_catalog_subject_resolver.py |
| main 尚无此路径，验证公开合同后承接 | scripts/report_catalog_verified_compare.py |
| main 尚无此路径，验证公开合同后承接 | scripts/report_catalog_verified_compare_cli.py |

B37 其余 4 个 touched 产品路径已与 main 等字节：scripts/report_catalog_cli.py、scripts/report_catalog_deployment.py、scripts/report_catalog_lineage.py、scripts/report_catalog_research_publication_sources.py。代码候选总写集合是上述 19 路径及其对应测试；不能扩成整个 release 文档/产物树。

codex/revenue-source-reader 3b00b938 为早期 SourceReader 原型（4 个产品路径、6 个测试/文档路径的独立提交），其 4 个产品路径在 main 都已存在但不同；main 后续已有 reader-v2 / SourceRef / P5 默认入口 / replaceable readers。它不是应直接重放的“丢失修复”。保留 ref/原型证据，待 owner 确认无尚需的合同再归档，不制造平行 reader。

### 3.3 RF dirty 全归因

| 工区/项 | before 差额与归因 | 处置 |
|---|---|---|
| primary assurance/runs/daily_alert.jsonl | 增加 36 行调度记录；2026-10-06 至 11-10 的 T2 canary/bound stale 失败 | 原字节归档；不能抹去失败后声称 assurance 通过 |
| primary assurance/runs/weekly_alert.jsonl | 增加 6 行 T3 suite exit 1 记录 | 同上 |
| primary assurance/runs/monthly_manifest.json | 最新 20261101T050000Z，ok=true，triplet 更新 | 保存与当次日志关系后精确 restore |
| primary assurance/runs/weekly_manifest.json | 最新 20261108T043000Z，ok=false，triplet 更新 | 保存失败证据后精确 restore |
| .codex/worktrees/w04-research-authoring-20261011/revenue-forecast | SKILL.md 与 references/research-coverage.md 未提交；新增 research authoring 1C / requested horizon 说明，后者约 +113 行；另 14 个 untracked | 原研究 owner 继承/归档；不能整体覆盖当前 SKILL 4.3（旧工区 4.2 和 attestation mandatory 会回退现行政策） |
| Projects/rf-impl | 242 tracked 状态，238 staged（230 A、8 M），其中 233 staged blob 等于 main；4 unstaged 仅行尾变化 | 不提交旧树大包；下列 5 个不同 planning/evidence 文件保留审计后可核销，其余已吸收 |
| Temp/rf-fresh-dag-20261009 | 1424 D，tip 已是 main 祖先，before 无 untracked | ROOT 后续已报告清理空指针；不是应提交的删除补丁 |
| Temp/rf-merge-review-20260927、rf-narrative-consumer-20261003、rf-period-evidence-20261010、rf-source-ref-v2-integration-20261003 | 数万 D 是残缺 checkout 表象；ROOT 后续发现保留原件（如 msft-20260630.htm） | 保留，不因 Git untracked 数小或 tip 已吸收而删；本轮不读原件 |
| Temp/rfv2-tdd-20260927 | before 指向 3b00b938；ROOT 后续见 detached/只剩 .git 指针 | tip 非 main 祖先，保留记录；本审查随后 for-each-ref --points-at 3b00b938 仍查到 refs/heads/codex/revenue-source-reader，当前并非唯一可达引用 |

rf-impl 仅 5 个 staged 与当前 main 不同的文件：

- .planning/2026-09-19-three-project-history-audit/OWNER_DECISIONS.md
- .planning/2026-09-19-three-project-history-audit/execution_runs/RATCHET-FIX-C/a20260927-01/verification_output.txt
- .planning/2026-09-19-three-project-history-audit/execution_runs/RATCHET-FIX-REVIEW/a20260927-01/recompute_metric.py
- .planning/2026-09-19-three-project-history-audit/findings.md
- .planning/2026-09-19-three-project-history-audit/progress.md

其中 recompute_metric.py 是旧审计复算辅助件，不能只因扩展名为 .py 当作 runtime 差额。4 个 unstaged 路径是 I-04-D/r2_corrections.md、RF-RATCHET-REST-A/probe_new.json、probe_orig.json、TTL-30D-POLICY/hashes.json；忽略行末空白后 diff 空，不需要另造功能补丁。

ROOT 精确恢复仅可在保存四文件原字节后对以下四路径使用固定 before SHA；不递归 restore assurance，也不清理整个工区：

~~~powershell
git restore --source=b005a179280ee19695578bdba9427b4dd44cdd73 --worktree -- assurance/runs/daily_alert.jsonl assurance/runs/monthly_manifest.json assurance/runs/weekly_alert.jsonl assurance/runs/weekly_manifest.json
~~~

这是建议命令，本子任务未执行。

## 4. StockWiki：公开接口发布家族核销

master 12c441e8 tracked clean；没有 remote。18 个非祖先分支不是 18 份独立工作：

- c38 release 4532b0da 已包含 B31/B33、identity、public research、onboarding、proof read、research scope、B37 subject 的产品链。aa0a69f0 的 b33-sw-proof / sw-b31-release 是同 tip；e22f15a6 的 b33-sw-binding / sw-b33-release 是同 tip；194abedf 的 all31-universe / b-integration 是同 tip。
- B34 id repair 的产品提交 a7b27 已在 C38；07fbb8a1 仅末尾 handoff 文档未包含。不要先独立合并 B34 再重复移植 C38 的同一实现。
- C1 authority 的 7be0c97、60a85efd 相对 C38 的 git cherry 都是 -（由 cc3e / 9349 路径吸收）；不再独立施工 C1。
- B03 author 分支 586b2f7 建在旧 B33 家族。d00-b03-stockwiki 652f6a48 是主线较新基座 d8d330 上的 12 个窄补丁；用 git cherry author d00-b03 d8d330 限定后，这 12 个都是 -，说明同一 B03 功能已在 author 家族，不应两份都合。当前 master 相对它仅需核对 dashboard_company_assessment_cli.py、stockwiki/public_company_assessments.py 和 tests/test_public_company_assessments.py 的公开差额，不能把 68 提交旧 author 树盖回。
- C38 对 master 的 43 个产品 touched 路径中，6 个同名不同、37 个 main 不存在；这不是“main 接口肯定已就绪”的证据。必须由 ROOT 先用所需合同做 verification-first，再决定最小承接。当前 source consumer、F05 字段/接纳规则和主线修复都保留。

关键历史文档：docs/handoffs/dashboard-B31-owner-release/README.md 声明独立 release 不是 master；docs/handoffs/B34-ID-NORMALIZATION/handoff.md 将 admin repair CLI/preview/apply 与身份规范化测试列清；B37 subject handoff 的公开 exact-revision ASJ port 不等于任意研究可接受。合并代码不隐含对真实数据库执行 repair/apply，不修改 IQS。

C38 的产品路径差额如下（这是有限候选集，不是要求无条件引入所有 43 文件）：

| 分类 | 路径 |
|---|---|
| main 已有，需保留新实现逐项适配 | stockwiki/cli_registry.py |
| main 已有，需保留新实现逐项适配 | stockwiki/identity_receipts.py |
| main 已有，需保留新实现逐项适配 | stockwiki/quick_scan_backup_manifest.py |
| main 已有，需保留新实现逐项适配 | stockwiki/quick_scan_schema.py |
| main 已有，需保留新实现逐项适配 | stockwiki/quick_scan_store.py |
| main 已有，需保留新实现逐项适配 | stockwiki/quick_scan_universe.py |
| main 尚无此路径，验证公开合同后承接 | dashboard_analysis_subject_cli.py |
| main 尚无此路径，验证公开合同后承接 | dashboard_identity_bridge_cli.py |
| main 尚无此路径，验证公开合同后承接 | dashboard_issuer_proof_cli.py |
| main 尚无此路径，验证公开合同后承接 | dashboard_membership_request_cli.py |
| main 尚无此路径，验证公开合同后承接 | dashboard_onboarding_cli.py |
| main 尚无此路径，验证公开合同后承接 | dashboard_profile_sources_cli.py |
| main 尚无此路径，验证公开合同后承接 | dashboard_research_binding_cli.py |
| main 尚无此路径，验证公开合同后承接 | dashboard_research_source_link_cli.py |
| main 尚无此路径，验证公开合同后承接 | dashboard_security_id_repair_cli.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/_public_research_view_content.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/_public_research_view_project.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/_public_research_view_refs.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/_public_research_view_source.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/_public_research_view_state.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/_public_research_view_wire.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/admin_security_id_normalization.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/cli_parsers/public_research_view.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/dashboard_identity_bridge.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/dashboard_issuer_proof.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/dashboard_onboarding.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/dashboard_onboarding_contract.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/dashboard_onboarding_owner.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/dashboard_profile_sources.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/dashboard_research_binding.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/dashboard_research_binding_contract.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/dashboard_research_binding_flow.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/dashboard_research_binding_owner.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/dashboard_research_binding_proof.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/dashboard_research_source_client.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/dashboard_research_source_link.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/dashboard_research_source_projection.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/public_analysis_subject.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/public_research_view.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/public_research_view_cli.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/quick_scan_membership_read.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/quick_scan_membership_request.py |
| main 尚无此路径，验证公开合同后承接 | stockwiki/research_profile_keys.py |

StockWiki 所有 dirty：仅 Temp/stockwiki-narrative-consumer-20261003（2019 D）与 Temp/stockwiki-w04-mic-relations-20260930（1991 D），对应 tip 已入 master；不提交 mass delete，ROOT 先确认物理保留内容再移除残缺工区。primary 有 7 个 untracked、其他工区的 before 数详见附录，统一交 ROOT 空间/类型清单，不据此宣告可删。

另一个不挂分支的 worktree：Projects/invest-quick-scan/.worktrees/stockwiki-dashboard-ports-20261109，HEAD c2c65c60fa6ad3fe1d73a2ea9ee27747264c7fff；独立运行 git merge-base --is-ancestor c2c65c60 master 返回 0。其代码可达，不需并线；仍然不改 IQS 工区。

## 5. Audit：已吸收，保留核销证据即可

22 refs 全部为 3589b69c main 祖先；18 worktree 的 tracked 状态均无变化；无 remote / stash / tag / replace。没有代码理由为 Audit 派新修复包。ROOT 完成 untracked/运行输出归档后，可按“已吸收工区”规则核销；无需为删除冗余 checkout 重跑真实收入预测或四 agent 研究审计。

## 6. Dashboard：有限接收与旧分支去重

### 6.1 本轮正在接收的边界修复

冻结 primary 4 个 tracked 差额均为实质修复：

- application/service.py 从公开 ports 导入 OriginalStream / OwnerPortError，新增 public async open_original 代理。
- transport/http.py 改调 service.open_original，移除对 service._port 的跨层私用。
- ports/protocols.py 的 OwnerPortError 去掉 dataclass frozen、保留 slots/public 字段/equality，允许 Python contextmanager 设置异常 traceback。
- tests/support/factory.py 使用 DASHBOARD_TEST_RUNS_ROOT 或本仓 .test-runs，并创建父目录，避免固化写出作者其他工区。

原新建 tests/unit/test_owner_port_error.py 与已有 m0-platform 同名文件造成 pytest import mismatch。ROOT 已把异步传播回归并入 tests/unit/m0-platform/test_owner_port_error.py，并移除重复入口；原 frozen/hash 断言绑定实现且与异常传播矛盾，修改后保留字段/equality 合同，审查无阻断。

tests/integration/test_module_boundaries.py 第 1–6 行声明有限扫描；176–190 行仅拦可静态识别的外部 owner 或私有跨层 dynamic import；248–259 行含 stdlib/public/unknown 反例。原“所有 dynamic import 禁用”的过宽要求已修。此测试不覆盖动态拼接路径、所有运行时 I/O，也不能单独证明 MB runtime isolation；继续由原 MB runtime artifact / black box 验证，不新增许可流程。

ROOT 负责本轮运行结果；本子任务没有测试执行权，不把静态通过写成测试通过。ROOT 曾报告首次 --basetemp 父目录缺失，已修环境 setup 后重跑，此项不是产品失败。

### 6.2 两个小 adapter 提交与原文流测试

| 原候选 | 本轮 main 观察 | 合同/副作用审查 |
|---|---|---|
| d03-e13-public-stream-test 5d2a761a | 5a16ca7 test(cwp): model reopened original stream | 增加实际 OwnerStreamTransfer 控制夹具，核对 reopened SourceRef、purpose=preview、媒体长度/etag、只调用一次 reopen；test-only |
| 4b30e1d9（owner-adapter 分支第一个提交） | c56e9ce fix(dashboard): encode the CWP browse language filter as a list | cwp.py:144 将非空 language 包成列表；CWP public_document_browser.py:188/195/334 的 tuple/list/_optional_text_list 对应，空值保留 null；无额外请求 |
| 8e3231c3（第二个提交） | 0addea2 fix(dashboard): reconcile filing jobs against the configured owner | ff_job.py:161 仅 action=reconcile 且有 config 时传 --config；FF scripts/ff_job.py:269 接受该参数，ff_job_runner.py:362–364/468–470 将其交给 reconcile readonly owner query；其他 action 不变、没有新增采集 |

注意旧 4b30 测试曾把旧 stream 测试改为 buffered read_exact_source_ref；与 5d2 的受控实际流测试接收时应保留两种有意义的覆盖，不能互相替换。本报告观察到另一 harness 按 stream → language → reconcile 顺序形成三个 main 提交；ROOT 仅观察并保留，不能将提交作者或动作归给 ROOT。

限定测试路径真实存在：

- tests/adapters/test_public_source_research.py
- tests/adapters/cwp_original_stream/test_adapter_stream.py
- tests/integration/m8-jobs-integrate/test_ff_job_adapter.py
- tests/unit/m0-platform/test_owner_port_error.py
- tests/integration/test_module_boundaries.py（本轮新文件）

ROOT 最新回报：当前 6 文件有限套件 189 passed（dashboard_verified_tests.log，100%）；两个 adapter 的有限套件 29 passed、70 subtests。上述结果是 ROOT 报告，本子任务未执行或独立重跑。

已有 tests/adapters/cwp_original_stream 的 24 cases 未通过：fixture 所选 owner checkout 找不到 source_stream_cli.py。ROOT 已确认这是未并线 T-READ 入口组合缺口，不能伪装成全部通过，也不能临时造 fake owner 将它转绿。保留失败日志与实际 owner root/HEAD，写回既有 CWP/ROOT 组合卡；在真实 owner 入口接收后只重验受阻的流式 public contract。此失败与两个参数修复的确定性本仓合同验证分开报告，不能反向抹去真实组合缺口，也不要求因此重跑付费 forecast。

### 6.3 其余非祖先分支的实际归因

| 家族 | 实际状态 | 建议 |
|---|---|---|
| b-real / b31 / b32 audit、b37 revision、C1 authority、C38 integration、CWP original-stream/integrity-repair | 附录列出的 17 refs cherry +0，非 merge patch 已等价吸收 | 不重放 patch；保留必要审查文本后核销冗余 refs/WT |
| e14-capture-followup / e14-d00-capture（同 3ca73788） | 3 ahead 中 2 patch 已吸收，仅独有 CUA 阻塞记录；旧 Connections.tsx 已被 main 模块化替代 | 保留历史暂停/阻塞记录，不恢复旧组件、不把 E14 CUA 旧状态变成本轮新增许可 |
| iqs-b-read-projection 27024c26 | 3 个文档/测试证据提交，无产品 touched | 归档/择取缺失测试证据，无新产品包 |
| issuer-proof-contract ba0abe2c | 5 个合同/证据提交，无产品 touched | 保留合同出处，不重做 owner |
| rf-provider-discovery c4b0d6af | 11 个 discovery/证据提交，无产品 touched | 归入原 PWF，不新造 RF provider |
| iqs-b03-company-result 8f126ed1 | cherry +19，但 main 已由 04756ca1 整合 B03，6ea719ce / 742bca59 / 5d6495a2 / dda77264 记录主线接收；旧 14 产品路径有 3 个已被 main 拆分/删除 | 只验证当前 B03 public wire 与保留 unique handoff，不能整包恢复旧 QuickScan.tsx / ScreenBuilder.tsx / adapters/iqs.py |
| x-b03-live-owner-verify 72529d78（含 remote 同 tip） | 7 个有限验证器/证据提交，无产品 touched | 有用证据与测试按原 PWF 保留，不能称新产品功能 |
| x-c01-schema7-rehearsal 9bfadfe8（含 remote 与 origin/HEAD） | 2 个 rehearsal/证据提交，无产品 touched | 保留迁移演练证据；origin/HEAD 指向它，不等于 origin/main，也不意味着当前默认 main 丢失 |
| x-c02-ff-statements-read 8c4e1d27、x-c02-ff-aggregate 82276d64（含 remote） | 当前 main 祖先 dc345e84 已整合 aggregate；filing_fetch.py blob 与这两个 tip 相同，service 的差异是 main 已改 ops registry、旧分支仍长 dispatch | 不重复加入 aggregate，不用旧 service 覆盖模块化主线；仅保留未吸收证据 |
| origin/main | 冻结清单中 tip 0dcf61... 为 before main 祖先 | ROOT 按现有正常推送流程同步已验收 main；本报告不宣称已推送 |

### 6.4 Dashboard 所有 dirty 工区

| 工区 | 差额 | 处理 |
|---|---|---|
| primary | 上述四源码/测试根文件，两个新测试；后经 ROOT 合并重复测试成既有 m0-platform + 新 scanner | 现有 owner 本轮接续；不派竞争写包 |
| .codex/worktrees/dashboard-d03-adapters/investment-dashboard | .codegraph/config.json；另 166 untracked | config 删除 **/.worktrees/** 排除项/行尾变化属索引范围残留，非产品；166 项由 ROOT 分类型，不能统删 |
| 上述目录/.worktrees/d06-e13-public-cli | .codegraph/config.json | 同类索引配置残留；与业务 patch 分开核销 |
| Projects/d00-b03-dashboard | .codegraph/config.json | 同上 |
| Projects/dashboard-iqs-b03-company-result | .codegraph/config.json + repair_chain.py；另 36 untracked | repair_chain 增加 public SW publish-release 优先、truncated/import/release/unpublished 负例，是真实未提交验证器草稿；交 B03 owner 保留，不能以“旧分支已吸收”丢弃 |
| .worktrees/all31-listing-preview-combo | 120 staged（104 A / 16 M），其中 110 staged blob 等于 main | 下述 10 项分别处理；不提交完整旧 staging |
| .worktrees/m5-e05e06-ext-01 | INDEPENDENT_AGENT_REVIEW.md | 独立 PASS 报告替换原 self-review NOT_RUN 占位；有价值的历史验收证据，保留/文档提交，不能恢复占位删掉 |

all31-listing-preview-combo 剩余 10 个与 main 不同项：7 个旧 PWF 文件（OWNERSHIP.md、START_HERE.md、dispatch/E14-URL-DIAGNOSIS、findings.md、progress.md、status.json、task_plan.md 一组）；2 个旧 React 文件 OriginalPreview.tsx / Documents.tsx（main 已拆分，不得复活旧 16 MiB/iframe 实现）；1 个 test_original_loopback.py（旧版本缺 main 后来补的 TemporaryDirectory/cleanup）。保留独有 E14 诊断和历史 PWF 差额即可；这不是 120 文件的新产品补丁。

## 7. 部署支线、并线顺序与原 MB 卡的落点

仅选择性读取 config/b37-main.local.json 的 root 字段：

- rf_root → Projects/investment-dashboard/.worktrees/b37-rf-release；rf_data_root → RF 主工区。
- stockwiki_root / identity root → Projects/investment-dashboard/.worktrees/b34-sw-id-repair；workspace → StockWiki 主工区。
- cwp_root → Projects/investment-dashboard/.worktrees/b33-cwp-source-proof；其数据/配置根仍可在 CWP 主工区。

这些目录位于 Dashboard 下，但 Git owner 分别是 RF/SW/CWP，不能由 Dashboard “清理本仓 .worktrees”顺带删掉。未取得实际进程命令行/启动配置或新进程 public probe，本报告仅记“配置引用”，不作当前运行证明。CWP 支线由另一 owner/ROOT 审查，本报告不重复决定其祖先或源码状态。

建议接续顺序与唯一写 owner：

| 次序 | owner / 原卡 | 有限动作 | 退出证据 |
|---|---|---|---|
| 1（可独立立即做） | Dashboard 现有 owner / ROOT | 完成当前 boundary dirty 修复；核对并保留另一 harness 已提交的 stream+language+reconcile 三项 | 必要测试路径通过、每个 dirty 可解释、main 新 SHA；静态扫描不冒充 runtime 全解耦 |
| 1（可并行只读核销） | ROOT | RF assurance 原字节归档后四路径 restore；Audit/已吸收 refs 依数据保留规则核销 | 路径明确的 before/after；不删原件和 unique audit |
| 2 | ROOT 组合验证 / CWP 原卡 | 保持 CWP B33 旧根可用；从 owner 审查结论验证目标 main 的 source document/proof 合同 | exact public fixture/read-only probe 与部署根矩阵；必须保留并解决本轮 24-case 原文流 owner T-READ 入口缺口，不用 fake owner 冒充真实组合；不重跑采集 |
| 2（verification-first） | ROOT / StockWiki 原卡 | 对 C38 必需 public identity/research/subject 合同与当前 master 做差额核验；B03 用 d00-b03 的三文件窄集合；仅失败缺口进既有 owner | 本仓 fixtures + public CLI；保留 master 新来源消费；代码集成不运行 production repair |
| 3 | MB-RF 原卡 owner | 承接 B37 尚缺 compare/scope/publication 合同，保留 main durable jobs/recovery/source ports；不合 input-prep 研究产物或旧 facade 全树 | 旧公开行为与新主线回归同时通过；current-default isolation，历史固定路径兼容有说明 |
| 4 | ROOT | 使用已准备 runtime artifacts 的组合 black box；冻结 root/config 映射，再决定旧部署 WT 退休 | 移除邻仓源码可见性后 public contract 正常；换根前后同请求归属/版本一致，不更改数据权威 |

并行性：Dashboard 可独立写本仓；RF owner 仅写 RF；StockWiki 优先只读验证，只有证明缺口才继续原 SW owner；Audit 不派实现。每仓只留一个作者写集合，CWP/FF owner 独立。这些小修复无需等新 ROOT fixture 许可；本仓缺 fixture 由 owner 在隔离 tmp 建立，组合样本在 M2 前准备即可。保留现有 paused 的研究/E14 大节点，不把“等待研究质量完善”塞进解耦退出。

针对 RF 真实已有的限定测试路径（只建议，未运行）：main 的 tests/test_report_catalog_rf_job_import.py、tests/test_rf_job_concurrency.py、tests/test_rf_job_recovery.py、tests/test_rf_job_boundary_regression.py、tests/test_decoupled_source_port.py、tests/test_d4_narrative_consumption_port.py；B37 的 tests/b37_scope_binding/、tests/b37_publication_sources/、tests/b34_publication/、tests/b35_lineage/ 及相应 report_catalog compare tests。先用所改合同的负例证明失败，再适配，再回归受影响 seam；不加预测准确率/研究结论通过条件。

StockWiki 真实限定路径：C38 中 tests/b34_id_normalization/test_normalization.py、tests/b37_subject/test_public_subject.py、tests/test_dashboard_identity_bridge.py、tests/test_dashboard_research_binding.py、tests/test_public_research_view.py、tests/test_quick_scan_membership_request.py；d00-b03 的 tests/test_public_company_assessments.py；主线既有 source export/narrative consumer tests 依触及 seam 回归。只在合成数据库/临时 workspace 上测试，不能把测试运行等价成真实 identity repair。

## 8. 完整 refs 核销表（冻结 before）

处置代码：

- A：祖先已吸收；不重复并线。若有 dirty/untracked/部署引用，按第 3–7 节保留。
- P：patch-equivalent；不重新应用，保留需要的审查证据。
- RF-B37：归入 B37 最小合同/文件差额，不能分别重复并全部历史祖先。
- RF-DOC：B34 末尾 release 文档；产品已入 B37，保留文档即可。
- RF-PUB：B37 publication 经 release 适配吸收；不独立重复重放。
- RF-JOB：旧 facade，main 已有更新实现；只核对残余合同。
- RF-RESEARCH：input-prep 部分研究证据，原研究计划保留，不是 MB 代码。
- RF-PROTOTYPE：早期 reader 原型，保留 ref/证据，不直接重放。
- SW-C38：在 C38 家族中集中 verification-first，不独立派包。
- SW-B34：产品已入 C38；末尾文档保留，配置引用 WT 先留。
- SW-C1：两独有 patch 对 C38 为等价，不重复实现。
- SW-B03：仅 d00-b03 三文件候选集；author 家族不整包重放。
- D-STREAM / D-ADAPTER：本轮已观察到另一 harness 写入新 main 提交，ROOT 仅观察保留，before 数保留。
- D-E14 / D-EVIDENCE：独有历史文档/有限测试，保留证据，不恢复旧产品。
- D-B03：主线已改写整合功能；保留独有验证器/证据，核对公开合同。
- D-FF：主线 dc345e84 已整合产品；保留独有证据，不还原旧 dispatch。
- REMOTE-HEAD：别名指向 rehearsal，不是 main，也不作删除/默认分支更改授权。


### rf refs

| 引用 | tip SHA | ancestor | ahead | cherry + / - | 处置 |
|---|---|---:|---:|---:|---|
| refs/heads/codex/aq-rf-20261013 | f0d694d69a05ef3f7a449e87cd91cdb44d1ff8ce | yes | 0 | 0 / 0 | A |
| refs/heads/codex/cmrf-input-semantics-20261008 | b1763fc034558674b56c941e0b13620df9c11a12 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/company-pool-failure-consumer-20261009 | cf06ba000fe594597c5d32a18aad6040d19a0fa0 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/d00-return5-rf-audit | c1e27877da9da8e78d5e76a08b7e090a6e096080 | no | 19 | 19 / 0 | RF-B37 |
| refs/heads/codex/dashboard-owner-release-20261109 | cd24976a958bc2abee841a592691268b45b117ee | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-rf-b31-release | c1e27877da9da8e78d5e76a08b7e090a6e096080 | no | 19 | 19 / 0 | RF-B37 |
| refs/heads/codex/dashboard-rf-b34-alias | d8890b4a09e4f73666db97296cc8743ec341fe70 | no | 24 | 24 / 0 | RF-B37 |
| refs/heads/codex/dashboard-rf-b34-catalog | a72cec5a74bf7ef9ffdf22a8fdef444cdf63adc2 | no | 26 | 26 / 0 | RF-B37 |
| refs/heads/codex/dashboard-rf-b34-publication | 2b89730c0d7a5f977145fbe135a8cc8a53068565 | no | 45 | 41 / 0 | RF-B37 |
| refs/heads/codex/dashboard-rf-b34-release | 7f1d3a990b7814724ee91dca832d98ebe29960af | no | 42 | 38 / 0 | RF-DOC |
| refs/heads/codex/dashboard-rf-b34-source | 28cdf12eb08aa2545d7640ac224583e005b2ecdb | no | 23 | 23 / 0 | RF-B37 |
| refs/heads/codex/dashboard-rf-b35-lineage | 9cbc32c98931caa1ce49fea304b8be50f6f11b54 | no | 50 | 46 / 0 | RF-B37 |
| refs/heads/codex/dashboard-rf-b37-publication | a5afa6d248d1b279d160224330abaf6c6da86dcb | no | 51 | 47 / 0 | RF-PUB |
| refs/heads/codex/dashboard-rf-b37-release | 28d646d306e8f0b5f90d402e204676cf97d2b5a1 | no | 58 | 54 / 0 | RF-B37 |
| refs/heads/codex/dashboard-rf-b37-scope | 21decc17be9de1d039347b19d71e9e344c9387db | no | 52 | 48 / 0 | RF-B37 |
| refs/heads/codex/dashboard-rf-deploy-root | c1e27877da9da8e78d5e76a08b7e090a6e096080 | no | 19 | 19 / 0 | RF-B37 |
| refs/heads/codex/dashboard-rf-identity-bridge | 11e0a2a7eab3f76f1a8dc2d6a75f5298be678ec6 | no | 8 | 8 / 0 | RF-B37 |
| refs/heads/codex/dashboard-rf-report-catalog | 430fabb4ff3d52c7859d83598eba3dc46d0e47de | no | 5 | 5 / 0 | RF-B37 |
| refs/heads/codex/dashboard-rf-report-compare | 1db861f15a6ad4dea5e06342a9f5d8fb64844066 | no | 13 | 13 / 0 | RF-B37 |
| refs/heads/codex/du11-rf-citation-closure | d578da58b01b6cb9d3145ca88c0c292911398607 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/du5-rf-units-20261015 | e2f6afd01789e9d355fd169b15b7db97d3253173 | no | 1 | 0 / 1 | P |
| refs/heads/codex/du6-rf-targets-20261016 | 86ca29411fbed1eaf2958b2eff579395f7d151a7 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/du8-rf-comparison-20261016 | 8845bc180efaf8b1638ee2056e5152014b425dd5 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/fresh-rf-dag-20261009 | 5a3defcdbf45f5b1f0b7133511769c9e037796c1 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/fresh-runtime-boundaries-20261009 | f88ace5a82f94e8b8acdabda66761f36bae2e040 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/fresh-source-scope-reasons-20261009 | 5dcd19be77e8425f88a3d162d21c16b55070d51c | yes | 0 | 0 / 0 | A |
| refs/heads/codex/fresh-typed-cause-20261009 | 3c3c03792b189734aac5a0c8900b67b2c6f73ca5 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/g2-rf-tools | 1a2f9428a599504eb8355fcaebf86c6cbcaccbb3 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/g3-main-rf | ab7a7a4434bbb4c52a5bd2a6cd6ed710d7151eee | yes | 0 | 0 / 0 | A |
| refs/heads/codex/g3-rf-assurance | 4a936395be692c6dbf23685b89d2e4894ac73984 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/g5-rf-install | 0d8b5dedd148e4459ba74d425c71af4ee457478c | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m3-acceptance-20261010 | c3e39184b4e66f87422a28fedcf1d7afb6e3b011 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m3-acquisition-usage-20261010 | 741f7c01fc2e13d42f919aa0fc8053eb8cabfe08 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m3-optional-period-20261009 | ccce3bf4aa8905753565c4cef5905550d394b958 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m3-period-evidence-20261010 | f8ae04884237c39d204689883c8756ee7d33a0a9 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m3-source-display-20261009 | 43635e5110d69c5ccf04647692ba8ef6ccfb01aa | yes | 0 | 0 / 0 | A |
| refs/heads/codex/main-permission-residue-20261009 | 5108f4703e92a385c37d01720ad930a751fbdc11 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/p2-summary-lineage-20261031 | 535604fa468e8a69be44e073dc7e29eacde80cbc | yes | 0 | 0 / 0 | A |
| refs/heads/codex/p5-rf-main-integration | 6e6b817a1a6e4567293a4dcb835815f3be508a03 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/p5-rf-source-default | a74b9ceb8aa97072f41992a2bbf062809c7f16da | yes | 0 | 0 / 0 | A |
| refs/heads/codex/p7-rf-calibration-binding | 47f497ad9dee9dc47f66fca37016e9ba6b6b6f33 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/pool-rf-source-context-20261009 | a73705171bf9704b313e2f3ed8fff9fda33233e4 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/r1-local-budget-observation | 32f013a979dedd6310a43877e818c69f614dd2b2 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/r1-narrative-availability | 674d08d92fe2ec64e1d42a3ebab0b364e0ac4354 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/r1-source-boundary | 35e999758662a8ecc8cfef74f0fe84e69df0d1d5 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/r1-targets | 95c8136a64e2049a8f63e47de33bdfaa82534cc1 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/r1-w09-research-20261023 | eb7c2deec3650889a10220fdfe8fccb168b28c72 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/r3-null-retrieval | 343e2de2b1a401e24f32e0db98c911eecd0ae653 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/r3a-current-material-read | c672a5e5b496dfac532a705b70a7976540399177 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/revenue-source-reader | 3b00b9384f3b8f3f87c5227e957aa42821fa101e | no | 1 | 1 / 0 | RF-PROTOTYPE |
| refs/heads/codex/rf-asof-20261007 | e241389adeda37bc9cbb53d7831063718552a936 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/rf-assurance-merge-20260927 | 3a69f9c5b6516ebc949d1c95bd50965f9112b7ad | yes | 0 | 0 / 0 | A |
| refs/heads/codex/rf-evidence-20260929 | 8b11b0ce62c1c18cfa8c846a41a3468615cd8f2a | yes | 0 | 0 / 0 | A |
| refs/heads/codex/rf-input-prep-01 | 4ab5ef4d89211a8a21b09aad04a398776af325be | no | 83 | 79 / 0 | RF-RESEARCH |
| refs/heads/codex/rf-job-facade-01 | d347c4ab43c847432ea354446cfea2947bf81d28 | no | 70 | 66 / 0 | RF-JOB |
| refs/heads/codex/rf-mainline-integration-20261004 | 8a153f3387ae75fb172e70f8ab63ffd38100779a | yes | 0 | 0 / 0 | A |
| refs/heads/codex/rf-narrative-consumer-20261003 | 6fb2def709d13bda9cfada7ecf62bfc0e3744ae2 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/rf-preserved-main-wip-20261006 | 6fb2def709d13bda9cfada7ecf62bfc0e3744ae2 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/rf-reader-v2-20260929 | 415d8eb3aeb3fefa25cc3e1fd9dc828bd63e35d0 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/rf-release-readiness-20260929 | 88b3bda3f1c85cf492ac6bcc2b160393ace037e4 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/rf-source-ref-v2-integration-20261003 | 0573c40c739bdbe0bef9445e97e88046e3ef1b69 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/root-du67-rf-20261016 | 2a68c6878c8bfd2b88c208d1bbc87540dedd6676 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/root-du8-rf-20261017 | c984a8fafc2a1e4d46d47d5f4fd7e9ba8f13d105 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/root-w05-rf-flow-20261011 | 30ddae8ed2a457c418e63b182e7d8c9230fbf3ff | yes | 0 | 0 / 0 | A |
| refs/heads/codex/root-w07-rf-model-reception | 8dc2671040f4330d3b54d1bea1d17246130f9c2a | yes | 0 | 0 / 0 | A |
| refs/heads/codex/root-w08-rf-20261013 | b9208a2117b8423f4b355dfca885aaf0d56a05bb | yes | 0 | 0 / 0 | A |
| refs/heads/codex/root-w16-acceptance-20261025 | 695dc7493cd5a1d3e10f7d9d1d5436f5447a3861 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/shared-reading-rf-reader-20261014 | aed581ac31b19108ab0f2cf638a830d152bbee11 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/source-clock-20261009 | a55603fba4bb7371616e067b6dc07ce05d86cb5d | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w04-research-authoring-20261011 | b7fe04aabe1d2a53b67a385c97161af976031040 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w04-rf-public-consumer-20261011 | 1b616622763ece6549676f2a74f596e6c65244af | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w05-rf-flow | f1a782a478d255b9b4b8f531e7a3961134e257ba | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w07-rf-model-quality | 72d0ced4f08d51256308707ab397fc280c35bb54 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w08-rf-combinations | 4d5c9f05835c46cc445288f2883c6bf215c39348 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w14-rf-clean-chain-20261024 | cafcfa42d0c8ff227fa56d58fc888e683be7ce61 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w16-rf-basis-20261025 | 611b1d62b2eb3228df037c95145a1d8d8d1f01d8 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w20-rf-adoption-20261028 | 3e8fbc5522a814abc4db7d828c3e4dcf84f308b8 | yes | 0 | 0 / 0 | A |
| refs/heads/fcap | 5319ee263c4af41ac255938c25bebd32cce56f66 | yes | 0 | 0 / 0 | A |
| refs/heads/main | b005a179280ee19695578bdba9427b4dd44cdd73 | yes | 0 | 0 / 0 | A |
| refs/heads/phase-14-input-build-tools | cbb1dd40b9435ed83e661547e5c28906d2c7e182 | yes | 0 | 0 / 0 | A |
| refs/heads/phase-19-tooling-docs | c0571d8b269ab73c4697c144e488ee4e52472b4d | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/HEAD | b005a179280ee19695578bdba9427b4dd44cdd73 | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/codex/company-pool-failure-consumer-20261009 | cf06ba000fe594597c5d32a18aad6040d19a0fa0 | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/codex/dashboard-owner-rf-release-20261109 | cd24976a958bc2abee841a592691268b45b117ee | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/codex/dashboard-p2-rf-mdb-20261109 | b005a179280ee19695578bdba9427b4dd44cdd73 | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/codex/g2-rf-tools | 1a2f9428a599504eb8355fcaebf86c6cbcaccbb3 | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/codex/g5-rf-install | 0d8b5dedd148e4459ba74d425c71af4ee457478c | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/codex/m3-acquisition-usage-20261010 | 741f7c01fc2e13d42f919aa0fc8053eb8cabfe08 | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/codex/m3-period-evidence-20261010 | f8ae04884237c39d204689883c8756ee7d33a0a9 | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/codex/r1-w09-research-20261023 | eb7c2deec3650889a10220fdfe8fccb168b28c72 | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/codex/w14-rf-clean-chain-20261024 | aa19b653da18566e582e802269f5908471c456db | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/codex/w16-rf-basis-20261025 | 611b1d62b2eb3228df037c95145a1d8d8d1f01d8 | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/codex/w20-rf-adoption-20261028 | 3e8fbc5522a814abc4db7d828c3e4dcf84f308b8 | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/fcap | 5319ee263c4af41ac255938c25bebd32cce56f66 | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/main | b005a179280ee19695578bdba9427b4dd44cdd73 | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/phase-14-input-build-tools | 02d89137f083a0931615b5b9717787a9f26804d8 | yes | 0 | 0 / 0 | A |

### stockwiki refs

| 引用 | tip SHA | ancestor | ahead | cherry + / - | 处置 |
|---|---|---:|---:|---:|---|
| refs/heads/codex/d00-all31-universe-stockwiki | 194abedfcaa617dadb3cee90474606fbe3f1b0ad | no | 41 | 39 / 0 | SW-C38 |
| refs/heads/codex/d00-b03-stockwiki | 652f6a48992b260cfb9fe25d6496341dc6ecba5a | no | 12 | 12 / 0 | SW-B03 |
| refs/heads/codex/d00-return5-sw-audit | 5dbcede6be50be6fdde7a317ce60c3e25d4a18a1 | no | 29 | 29 / 0 | SW-C38 |
| refs/heads/codex/d4-01-company-source-virtualization | 23d84586dc2425961e953f5ab28aef867de6cb87 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/d5-sw-processed-reader | 6d1e40bcdcde5e99488e22c38d57bd8e1b33c27e | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b33-sw-binding | e22f15a6df23daef8403b783f5a36ee1bb115c1c | no | 56 | 53 / 0 | SW-C38 |
| refs/heads/codex/dashboard-b33-sw-proof | aa0a69f09f1f35bae2f9ea7a0498988069491faa | no | 48 | 45 / 0 | SW-C38 |
| refs/heads/codex/dashboard-c38-sw-release | 4532b0da00a38eb74d5464466a166dc38b890222 | no | 66 | 63 / 0 | SW-C38 |
| refs/heads/codex/dashboard-owner-sw-b03-assessments | 586b2f7e73688aef2c16e6881591953637a1cf32 | no | 68 | 65 / 0 | SW-B03 |
| refs/heads/codex/dashboard-owner-sw-c1-authority | 60a85efd536349ee7efb89744a3f4a79bbbcec4b | no | 58 | 55 / 0 | SW-C1 |
| refs/heads/codex/dashboard-stockwiki-b-integration | 194abedfcaa617dadb3cee90474606fbe3f1b0ad | no | 41 | 39 / 0 | SW-C38 |
| refs/heads/codex/dashboard-stockwiki-identity-bridge | 9c47effec043985da5df419e5713d6c5dc91b6ea | no | 3 | 3 / 0 | SW-C38 |
| refs/heads/codex/dashboard-stockwiki-onboarding | 042951b3f8ab5c9d0148d5542bb819633ffcbe08 | no | 25 | 25 / 0 | SW-C38 |
| refs/heads/codex/dashboard-stockwiki-proof-read | eca69e1c463e472591c1b4cb1833d34e0f21b96d | no | 30 | 30 / 0 | SW-C38 |
| refs/heads/codex/dashboard-stockwiki-public-research | f6c402cd9685604204c488c89000775f283cd9be | no | 4 | 4 / 0 | SW-C38 |
| refs/heads/codex/dashboard-stockwiki-research-scope | a4eb1a39820718ca290df7aaeb8b7055a9ce2427 | no | 9 | 9 / 0 | SW-C38 |
| refs/heads/codex/dashboard-sw-b31-release | aa0a69f09f1f35bae2f9ea7a0498988069491faa | no | 48 | 45 / 0 | SW-C38 |
| refs/heads/codex/dashboard-sw-b33-release | e22f15a6df23daef8403b783f5a36ee1bb115c1c | no | 56 | 53 / 0 | SW-C38 |
| refs/heads/codex/dashboard-sw-b34-id-repair | 07fbb8a1169cca8dc17884002e78790219d906ca | no | 61 | 58 / 0 | SW-B34 |
| refs/heads/codex/dashboard-sw-b37-subject | c73dd8b0e9fe067a1767dc8c8f99663a4fe6fdef | no | 63 | 60 / 0 | SW-C38 |
| refs/heads/codex/f05-fact-ingest-20261109 | 93b25927f58b129628776b349f8bda7f2f264dba | yes | 0 | 0 / 0 | A |
| refs/heads/codex/f05-owner-runtime-01 | 3799b439cfd9808b428eca85b07d5e18b9b3370c | yes | 0 | 0 / 0 | A |
| refs/heads/codex/g2-sw-daily | 0b48919065a912f1da10d89d36bf6bf1e659db88 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/identity-snapshot-w02-w03 | ae11135cc1160adc74cc1d307ca8bd73cb4fa832 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/main-permission-residue-20261009 | d98acdcdf1a2feada2ae91f2f56aafaa74046728 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/r3-null-retrieval | 1ebe012adcdeab371d0dedfd04b89e11e1ee2fd4 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/r3a-current-material-read | 42fba06878fc58c01f58c0206f4d694a68e4d451 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/source-export-v2-reader | 0b406832b744892df7b592ca5d5c0d9fe2a0e3da | yes | 0 | 0 / 0 | A |
| refs/heads/codex/stockwiki-asof-20261007 | 9f552a6741dd093dc760ad6965458989cd027251 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/stockwiki-g2b-owner-context | 6f0c2c4abe9b70e0e9c48c32e80f883a14c40983 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/stockwiki-lane-integration | 52add7fd8710b6c7e4b4f4294b358cc10cd01ac8 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/stockwiki-narrative-consumer-20261003 | 4c3334ed412a6a6241eac307f20ad0593355f90f | yes | 0 | 0 / 0 | A |
| refs/heads/codex/stockwiki-sw-ident | 0c8603e43f8fa42bc9a877d43715826c8a48c121 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/stockwiki-w04-mic-relations | afa969226dd56d1d0a729990eb6bd30912fd7a45 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/sw-company-projection-01 | 27acd5d6ee7df2094c2bb1ad7e7599eb5be48ce5 | yes | 0 | 0 / 0 | A |
| refs/heads/master | 12c441e86282135b49120112dcf21c17509bbdd0 | yes | 0 | 0 / 0 | A |

### audit refs

| 引用 | tip SHA | ancestor | ahead | cherry + / - | 处置 |
|---|---|---:|---:|---:|---|
| refs/heads/codex/du5-audit-summary-20261015 | 583a13d9ed667cb58f15348d22582d5f361e5cb3 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/du6-audit-import-20261016 | c603d23d6ba731ed2f510f30a731f6ef3f3b43d3 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/du8-audit-measures-20261016 | 3ed248df06b2ba00e4f59d930647149ecc1f88af | yes | 0 | 0 / 0 | A |
| refs/heads/codex/p7-audit-execution-review | 40b38103f4b96860617e9bae98ec5b4ea8ee08d5 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/pool-audit-event-compat-20261009 | 681f2d19ff3058408fa0ceefa4919039b5b486db | yes | 0 | 0 / 0 | A |
| refs/heads/codex/root-du67-audit-20261016 | 8fd5a33949735422abbf3a5f39108d1fc606edb1 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/root-du8-audit-20261016 | 7ea6071b42ffb5155cf3d0741ac0603708aad6fa | yes | 0 | 0 / 0 | A |
| refs/heads/codex/root-w05-audit-loop-20261011 | 321d4c165575e81add3b4aa1ee9ba0a047ca6082 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/root-w06-audit-measures-20261011 | 9cd5ff8a2c8f9c1726c4047785164e3263673614 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/root-w07-audit-analyst-reception | e7c92577e853f6567475dcd26d54bdd30f5ab141 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/root-w08-audit-20261013 | e5189a0614477d4d84c9cd4e0237f9b2a64a059a | yes | 0 | 0 / 0 | A |
| refs/heads/codex/root-w17-acceptance-20261025 | 33200f8c947f35be75a77de38040982724e033a7 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/root-w20-audit-final-20261029 | 55c29fe5f3a9554f883156e3a4232eece04bf581 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w04-audit-capture-20261011 | c0993332623637d53f059350a382d99a95ef731d | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w05-audit-loop | 2ed0b5e2dcaf3c5b2436e6a61bcf06f8fb03ac3a | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w06-audit-measures | 6a50d7ed1b4cf389589c7ca62b4ab161b5dc0ad1 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w07-audit-analyst-quality | e3206880224f7fa97d3923cb70044a6956f7d2f4 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w08-audit-evidence | 96889c6a6d0d85b9c0ff6f54e35c4ea73e648bb6 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w15-audit-portable-20261024 | 9bc2248f7d66636a7ce5e5d23933b0f7ac12eb49 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w17-audit-coverage-20261025 | 7c71c8111f14a3aae6a1df274eeffb81c01939b7 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/w20-audit-checkpoints-20261028 | 5b8aa7182e7f7b219b0ef279106f1fc1886137b1 | yes | 0 | 0 / 0 | A |
| refs/heads/main | 3589b69cb9d28d7395607ce4fe689025b9acee96 | yes | 0 | 0 / 0 | A |

### dashboard refs

| 引用 | tip SHA | ancestor | ahead | cherry + / - | 处置 |
|---|---|---:|---:|---:|---|
| refs/heads/codex/d00-all31-listing-fix | e158288c622553bff17ed631a90a33dc0b57a9e9 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/d00-all31-listing-preview-combo | e158288c622553bff17ed631a90a33dc0b57a9e9 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/d00-all31-preview-audit | 475d44d133dfa781f7137cc292ad15d3e9660bf4 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/d00-all31-preview-fix | 475d44d133dfa781f7137cc292ad15d3e9660bf4 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/d00-all31-transport-audit | c544ebdb1cdacf5614257bcc57e4967f2a4dde7e | yes | 0 | 0 / 0 | A |
| refs/heads/codex/d00-all31-universe-audit | fa8e09a35a86018aa354dc79503281f227fc854c | yes | 0 | 0 / 0 | A |
| refs/heads/codex/d00-b03-dashboard | 6ea719ce6eac17165b70a633a21c250f39543622 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/d00-c04-combination | a909b5962ff86fd65c540ced7075681fc80626e3 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/d00-four-package-acceptance | dc345e8423c3464868a5229d65f42116abdef14e | yes | 0 | 0 / 0 | A |
| refs/heads/codex/d00-return5-listing-audit | e158288c622553bff17ed631a90a33dc0b57a9e9 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/d03-e13-public-stream-test-20261107 | 5d2a761ac75c19ada92a2a79c90e4ecf953055ad | no | 1 | 1 / 0 | D-STREAM |
| refs/heads/codex/d06-e13-public-cli-20261107 | 0c60e5daed0ad1a0ae21f7cd1e2eec22e4dab7ca | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b-forecast-iqs | 351a68fb4e841dd4173c76288b50215955aa869a | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b-listing-read | eec8963ea160cd16756ef508c9c79e5ad6202d3a | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b-owner-config | 51d6ad2e5e395e579be046adf7961e8481fe5ea2 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b-preview-isolation | 7bac216abd1fead3602ca232d2f19340e2ad9a72 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b-real-browser | 6d18617199736ef54ede3aa958cbd60c73fd5a8f | no | 7 | 0 / 5 | P |
| refs/heads/codex/dashboard-b-real-code-audit | 66566afc821e0c0f8993af2ceb75d8a7a24f6e39 | no | 7 | 0 / 5 | P |
| refs/heads/codex/dashboard-b-real-connections-fix | 870c7e676dc8a6d0fa90dbd9d1898c2a6c9b633a | no | 2 | 0 / 2 | P |
| refs/heads/codex/dashboard-b-real-listing-plan | d1c252f806a78e967ff3e24507dee1462939100e | no | 1 | 0 / 1 | P |
| refs/heads/codex/dashboard-b-real-owner-packet-audit | 39a4770bae51fe8e360700657396e653c9639650 | no | 2 | 0 / 2 | P |
| refs/heads/codex/dashboard-b-real-rf-compare | 72774b6019a7b4f5946c3f282eeef295895d8fdf | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b-real-source-check | b015b895e7029ffcfa22ddcc541df7704154365f | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b-source-research | 4cbc36f9a8d7677088c48d0f0709fe4d754417f2 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b-transport-bounds | 42d353201c368f829bcba55c324e473ad341e0c5 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b31-browser | 0767d71fe3f374fa7d9f8b76e5dd054ad51472ef | no | 1 | 0 / 1 | P |
| refs/heads/codex/dashboard-b31-independent | 3bb5a933de10558e5d0f0897f70ccb1279320fc0 | no | 1 | 0 / 1 | P |
| refs/heads/codex/dashboard-b31-integration | ac8fbca835f6f94fd4881de6eeabe3799be967be | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b31-pagination-repair | fb2ca21916febc8a23ba4d5b68c723cada4c8100 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b31-public-adapters | d2c48fe2fcd030fda0815a07643aa543752a51fc | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b32-audit-bind | 4163def0614dd76e0e4986dde6509743e30ca436 | no | 1 | 0 / 1 | P |
| refs/heads/codex/dashboard-b32-audit-combined-transport | d5f5f42a92810375faee6f078507da12e0539fc0 | no | 1 | 0 / 1 | P |
| refs/heads/codex/dashboard-b32-audit-combined-universe | 5c086ab90df81e04092e0f3c1a47f2739ab79293 | no | 1 | 0 / 1 | P |
| refs/heads/codex/dashboard-b32-audit-transport | 4424e7fb2aaee575e340db57e60432169dee06de | no | 1 | 0 / 1 | P |
| refs/heads/codex/dashboard-b32-audit-universe | 3d4f406e41941bf115f5eff7837ac25b6d8699b0 | no | 4 | 0 / 2 | P |
| refs/heads/codex/dashboard-b32-bind-fix | c1996068f82e2d2ee7b60c928afad0e223ce9814 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b32-integration | e8a13d8605ce4391c2a5fb09073b7c00534a61dc | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b32-transport-fix | 77776f351895294947a702735bc1de712809c006 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b32-universe-fix | cd2e88511928e747ee26f8e51d207e62c2bf4537 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b33-integration | 6c8439557505563e25c2022359d592dbfbc8c53a | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b34-combination-ui | c250a153af6bfbd69a2e003342e674326e81072c | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b34-integration | 0338c24b09afc4f4be5623c1a538e4a8d5d70a1e | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b35-bridge | 03c22de6657217a7633c7a583fa182940e2c1c35 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b35-lineage | 5e0c29fe9417011711dc7ed0ce077ba20d44e4b7 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b36-iqs | a3ba03e4df26303885c312724360e13608ab5190 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-b37-revision | 61b73eb95e1748659a875a7bfd7cf294225ca893 | no | 4 | 0 / 4 | P |
| refs/heads/codex/dashboard-c1-request-authority | d02a228818c0cededaa8f6600c1b256c47a797b0 | no | 2 | 0 / 2 | P |
| refs/heads/codex/dashboard-c1-universe-protocol | 6a747549f489280cf275aa9a1f7f3352a0697e84 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-c38-integration | 88327c388cd7f389d1a26d3a1fd4edd30d478eea | no | 4 | 0 / 4 | P |
| refs/heads/codex/dashboard-d01-architecture | 51a19c905909fa1611b338baaf282f72866772c2 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-d02-experience | d728b92ea7d237167554e3a23eb28c19fb55e6f1 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-d03-adapters | 9d563b390f11763a6b3cf04b479da07d9248dc4b | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-d04-product | 54d787d470f700a6414c5b81540ed481d0bae719 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-d05-audit | 32646f35e112016d8cbaf5ebc0d01d76cf583ad4 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-d06-usability | 07cb95987c43db10fea9b5533c71fcc38583bad9 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-e14-capture-followup | 3ca737888e4a4fdf3cf5662dd3f977c2c0ceffeb | no | 3 | 1 / 2 | D-E14 |
| refs/heads/codex/dashboard-e14-d00-capture | 3ca737888e4a4fdf3cf5662dd3f977c2c0ceffeb | no | 3 | 1 / 2 | D-E14 |
| refs/heads/codex/dashboard-e14-d00-review | d360f9b42bc486bbb9f83429255c0bb6498d726f | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-e14-real-zoom | 8a189c0080aadcc5e6cabeab9063bedce8bb228f | yes | 0 | 0 / 0 | A |
| refs/heads/codex/dashboard-iqs-b-read-projection | 27024c2622cc790afd92f624496c2a508909cafb | no | 3 | 3 / 0 | D-EVIDENCE |
| refs/heads/codex/dashboard-iqs-b03-company-result | 8f126ed1afd7b21f8ebed39e2c2264454fa5c2b2 | no | 19 | 19 / 0 | D-B03 |
| refs/heads/codex/dashboard-issuer-proof-contract | ba0abe2cde9869bc4fae98499f3a738dd4babe2e | no | 5 | 5 / 0 | D-EVIDENCE |
| refs/heads/codex/dashboard-owner-adapter-contracts-20261109 | 8e3231c319b0c845514d7a40036f8800795cf4f0 | no | 2 | 2 / 0 | D-ADAPTER |
| refs/heads/codex/dashboard-rf-provider-discovery | c4b0d6af083d81c5d28ef7e5630080ac875ca6bf | no | 11 | 11 / 0 | D-EVIDENCE |
| refs/heads/codex/dashboard-sw-research-bind-design | 14321f6ff889d8de198b9ec5bf28af8bf4860a4f | yes | 0 | 0 / 0 | A |
| refs/heads/codex/e12-iqs-dashboard-closeout-20261109 | efad14ff6292924b90a030d8ab87365ca66db8b4 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/iqs-public-reply-boundary-20261109 | b1aca35da3bb0d96e1362b976e5a382c3644ef2e | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m0-fe-test-infra-01 | 271dd3133372dee046a1c9f7d81f059a87e2c3b5 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m0-phase0-modularity-01 | 37bc9009f595cd2cecbeb1b8e6a31e51afebe97e | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m1-e08-prod-launch-01 | 452a1c7ab7fa81084448e5cc5506dddaf2b0ade0 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m1-e08-real-launch-01 | 4334a981b83f1a12b9bb0e0a0f0bbd7c46946825 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m2-e01-onboarding-real-01 | a05930837bb00056f1809d7d383c8f4a21b49529 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m3-c04-harness-01 | dc48be50cbba27c55349fdab7b2e0986c90e05ad | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m4-e04-extension-01 | 984411e84391fdf8466b7631f2d9f4e4cffc6dc4 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m5-e05e06-extension-01 | 88063c5b79446d9cdfe3d76c71f1ed122c7d3bc4 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m7-formula-builder-01 | 7ee602ad61ddf06c4b9d0849f73171712f2bcba6 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m8-executor-integrate-01 | 511d956cda5dde65d0cea3bbd4f3976b31582786 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m8-executor-survey-01 | 88ac37a803cb3dd1d3c73f949e4da5ff211d65e5 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/m9-e10-display-01 | 2980445a987d577158004c1d72a01c8f4dbf11c3 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/x-b03-live-owner-verify-01 | 72529d78441d1c866e29ba725a2c8e42c7d3a7f8 | no | 7 | 7 / 0 | D-EVIDENCE |
| refs/heads/codex/x-c01-schema7-rehearsal | 9bfadfe84f64d5b5de0b3a1fc1598ad7d16dd254 | no | 2 | 2 / 0 | D-EVIDENCE |
| refs/heads/codex/x-c02-ff-aggregate-context-01 | 82276d64b670884374fe1903478546d3a2b8329d | no | 11 | 11 / 0 | D-FF |
| refs/heads/codex/x-c02-ff-statements-read-01 | 8c4e1d27ce13a04ec63b25aa4ab681d4f7588e9e | no | 7 | 7 / 0 | D-FF |
| refs/heads/codex/x-c04-current-main-compat-01 | 1375d64e80ad8c491e61532b65d27be509791940 | yes | 0 | 0 / 0 | A |
| refs/heads/codex/x-c04-cwp-original-stream-01 | e3f443f153c1c56fff9d014242fcae8ff22c3b3a | no | 3 | 0 / 3 | P |
| refs/heads/codex/x-c04-integrity-repair-01 | 9a27b152d0128374726007982057021e083408f8 | no | 6 | 0 / 6 | P |
| refs/heads/codex/x-e15-2000-ui-perf-slice-01 | 976b1991cbb6f7fab7f750035cca324f80c7419d | yes | 0 | 0 / 0 | A |
| refs/heads/main | b707473a1166d3f8740170dad77cb21aa09863ce | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/HEAD | 9bfadfe84f64d5b5de0b3a1fc1598ad7d16dd254 | no | 2 | 2 / 0 | REMOTE-HEAD / D-EVIDENCE |
| refs/remotes/origin/codex/iqs-public-reply-boundary-20261109 | b1aca35da3bb0d96e1362b976e5a382c3644ef2e | yes | 0 | 0 / 0 | A |
| refs/remotes/origin/codex/x-b03-live-owner-verify-01 | 72529d78441d1c866e29ba725a2c8e42c7d3a7f8 | no | 7 | 7 / 0 | D-EVIDENCE |
| refs/remotes/origin/codex/x-c01-schema7-rehearsal | 9bfadfe84f64d5b5de0b3a1fc1598ad7d16dd254 | no | 2 | 2 / 0 | D-EVIDENCE |
| refs/remotes/origin/codex/x-c02-ff-aggregate-context-01 | 82276d64b670884374fe1903478546d3a2b8329d | no | 11 | 11 / 0 | D-FF |
| refs/remotes/origin/codex/x-c02-ff-statements-read-01 | 8c4e1d27ce13a04ec63b25aa4ab681d4f7588e9e | no | 7 | 7 / 0 | D-FF |
| refs/remotes/origin/main | 0dcf61f59595ebe4b64d9bd8ea490087ed62f7fd | yes | 0 | 0 / 0 | A |

### RF 历史 tags（额外完整列举）

| 引用 | tag object | peeled commit | 处置 |
|---|---|---|---|
| refs/tags/v3.0.0 | 3547bd5b74e8a0022d466a0caef032dd491bc5d8 | cc789bd9d71e6f8c40310fe178e9c2d0d1203d0a | main 祖先，保留历史 tag，无需并线 |
| refs/tags/v3.1.0 | ef77ae53d92a771d4ee733081a083704e01cd513 | 11060ad93b96d3ff8224ec9f19ae75bc18ba39f0 | main 祖先，保留历史 tag，无需并线 |
| refs/tags/v3.2.0 | 1b569a07544a3ce94d1a53697f6e6c1026a725c6 | cb65a126d70bfa3f5e3e00f3cde7209227b9b798 | main 祖先，保留历史 tag，无需并线 |
| refs/tags/v3.2.1 | 48eda54c362039a308e545d9bd5a6a1fc2d1fa9a | 6d7027eb2b653245155a15e86d4be71671f3b7a3 | main 祖先，保留历史 tag，无需并线 |
| refs/tags/v3.3.0 | a0c2a9d1f3ce74b3f11af12fa6d10146cc54e8fc | 69df60d64931e09a82831c2b0323a6b5528de94e | main 祖先，保留历史 tag，无需并线 |
| refs/tags/v3.4.0 | f1fdb2d35fb49a98e202a8ecb513ccc7bb01dff8 | 3d105b185c6fe48e17d4e0b0c57f94865d9978cc | main 祖先，保留历史 tag，无需并线 |
| refs/tags/v3.5.0 | c714ca778f3a017f58377ad6a19cfbe0f6571b68 | 71f717bc0243b2e6578106cbdb03eb2fd208bc2e | main 祖先，保留历史 tag，无需并线 |

## 9. 完整 worktree 核销表（冻结 before）

本表是 inventory_before 的 190 个登记工区，不是删除清单。主仓原件/产物和 untracked 全名以 inventory_before 与 ROOT 空间类型调查为准。ROOT 后续状态：rf-fresh-dag 空指针已清；rfv2-tdd 保留非祖先 tip 登记且已证实有 revenue-source-reader ref；另四个 RF Temp 有原件，保留。Dashboard main 已向 0addea2 前进，本表不覆盖该后续接收。

“无 tracked 差额”与“工区完全清洁”严格区分。branch 为 — 的 detached worktree 已单独检查；除 StockWiki c2c65c60 和 ROOT 后报的 RF rfv2 变化外，before 表保留其原分支信息。


### rf worktrees

| 绝对路径 | before 分支 | HEAD | tracked 状态数量/类型 | untracked 数 | 状态读取 | 处置依据 |
|---|---|---|---:|---:|---:|---|
| C:/Users/郑曾波/Projects/revenue-forecast | refs/heads/main | b005a179280ee19695578bdba9427b4dd44cdd73 | 4 ( M:4) | 5867 | 0 | A；dirty 见本仓正文；ROOT 分类保留 |
| C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/revenue-forecast | refs/heads/codex/w04-rf-public-consumer-20261011 | 1b616622763ece6549676f2a74f596e6c65244af | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/.codex/worktrees/m3-acquisition-usage-20261010/revenue-forecast | refs/heads/codex/m3-acquisition-usage-20261010 | 741f7c01fc2e13d42f919aa0fc8053eb8cabfe08 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/.codex/worktrees/w04-research-authoring-20261011/revenue-forecast | refs/heads/codex/w04-research-authoring-20261011 | b7fe04aabe1d2a53b67a385c97161af976031040 | 2 ( M:2) | 14 | 0 | A；dirty 见本仓正文；ROOT 分类保留 |
| C:/Users/郑曾波/AppData/Local/Temp/rf-fresh-dag-20261009 | refs/heads/codex/m3-optional-period-20261009 | ccce3bf4aa8905753565c4cef5905550d394b958 | 1424 ( D:1424) | 0 | 0 | A；dirty 见本仓正文；ROOT 后报已清 |
| C:/Users/郑曾波/AppData/Local/Temp/rf-merge-review-20260927 | refs/heads/codex/rf-assurance-merge-20260927 | 3a69f9c5b6516ebc949d1c95bd50965f9112b7ad | 47179 ( D:47179) | 0 | 0 | A；dirty 见本仓正文；ROOT 确认原件保留 |
| C:/Users/郑曾波/AppData/Local/Temp/rf-narrative-consumer-20261003 | refs/heads/codex/rf-narrative-consumer-20261003 | 6fb2def709d13bda9cfada7ecf62bfc0e3744ae2 | 46940 ( D:46940) | 0 | 0 | A；dirty 见本仓正文；ROOT 确认原件保留 |
| C:/Users/郑曾波/AppData/Local/Temp/rf-period-evidence-20261010 | refs/heads/codex/m3-period-evidence-20261010 | f8ae04884237c39d204689883c8756ee7d33a0a9 | 47529 ( D:47529) | 1 | 0 | A；dirty 见本仓正文；ROOT 分类保留；ROOT 确认原件保留 |
| C:/Users/郑曾波/AppData/Local/Temp/rf-source-ref-v2-integration-20261003 | refs/heads/codex/rf-source-ref-v2-integration-20261003 | 0573c40c739bdbe0bef9445e97e88046e3ef1b69 | 46657 ( D:46657) | 1 | 0 | A；dirty 见本仓正文；ROOT 分类保留；ROOT 确认原件保留 |
| C:/Users/郑曾波/AppData/Local/Temp/rfv2-tdd-20260927 | refs/heads/codex/revenue-source-reader | 3b00b9384f3b8f3f87c5227e957aa42821fa101e | 198 ( D:198) | 0 | 0 | RF-PROTOTYPE；dirty 见本仓正文；后报 detached，但 ref 已证存在 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1003-rev | — | 26bdfb273cf97553f2bdd96df2bfc747bcc719cb | 0 (无 tracked 差额) | 0 | 0 | detached；第 4 节已核 ancestry |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1101-rev | — | 1b41d62fa2d1fb327d86ab964094b6a9489b8a9f | 0 (无 tracked 差额) | 0 | 0 | detached；第 4 节已核 ancestry |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1204/base-revenue | — | 9315ddf3621e76bd18d1fa9318a03c4bb069e57f | 0 (无 tracked 差额) | 0 | 0 | detached；第 4 节已核 ancestry |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1204/layout/revenue-forecast | — | 4750fecd446e48b85f5ea28b56a63d51a0351c17 | 0 (无 tracked 差额) | 0 | 0 | detached；第 4 节已核 ancestry |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1204/r2/revenue-forecast | — | 387e6ac54c3c3a52a3ddb1d462f5151e309b0a67 | 0 (无 tracked 差额) | 0 | 0 | detached；第 4 节已核 ancestry |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1204/r3/revenue-forecast | — | 91cbc137916b1ab7571e199555fddfa4115d914b | 0 (无 tracked 差额) | 0 | 0 | detached；第 4 节已核 ancestry |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1205/revenue-base | — | 91cbc137916b1ab7571e199555fddfa4115d914b | 0 (无 tracked 差额) | 0 | 0 | detached；第 4 节已核 ancestry |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1205/revenue-forecast | — | 58db948678d7a04b525fe57006cf9a9658f133bf | 0 (无 tracked 差额) | 0 | 0 | detached；第 4 节已核 ancestry |
| C:/Users/郑曾波/Projects/.fcap-review/fc-130x/revenue-base | — | 4a4c1089b00716696b8c382b9265ba9478b9ec05 | 0 (无 tracked 差额) | 0 | 0 | detached；第 4 节已核 ancestry |
| C:/Users/郑曾波/Projects/.fcap-review/fc-130x/revenue-forecast | — | a9f1ff1821c64dde55601d7fd4606a4e91d0c0df | 0 (无 tracked 差额) | 0 | 0 | detached；第 4 节已核 ancestry |
| C:/Users/郑曾波/Projects/_g2/revenue-forecast | refs/heads/codex/g2-rf-tools | 1a2f9428a599504eb8355fcaebf86c6cbcaccbb3 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_g3/RF-ASSURANCE/revenue-forecast | refs/heads/codex/g3-rf-assurance | 4a936395be692c6dbf23685b89d2e4894ac73984 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_g5/rf | refs/heads/codex/g5-rf-install | 0d8b5dedd148e4459ba74d425c71af4ee457478c | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/rf-inputs | refs/heads/codex/source-clock-20261009 | a55603fba4bb7371616e067b6dc07ce05d86cb5d | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/rf-permission-residue | refs/heads/codex/main-permission-residue-20261009 | 5108f4703e92a385c37d01720ad930a751fbdc11 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/shared-reading-completion-20261014/rf-reader | refs/heads/codex/shared-reading-rf-reader-20261014 | aed581ac31b19108ab0f2cf638a830d152bbee11 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow | refs/heads/codex/w05-rf-flow | f1a782a478d255b9b4b8f531e7a3961134e257ba | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/w07/rf-model-quality | refs/heads/codex/w07-rf-model-quality | 72d0ced4f08d51256308707ab397fc280c35bb54 | 0 (无 tracked 差额) | 8 | 0 | A；ROOT 分类保留 |
| C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-rf-model-reception | refs/heads/codex/root-w07-rf-model-reception | 8dc2671040f4330d3b54d1bea1d17246130f9c2a | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/w08/rf-combinations | refs/heads/codex/w08-rf-combinations | 4d5c9f05835c46cc445288f2883c6bf215c39348 | 0 (无 tracked 差额) | 9 | 0 | A；ROOT 分类保留 |
| C:/Users/郑曾波/Projects/cwp-lanes-20261005/rf-source-v2 | refs/heads/codex/p5-rf-source-default | a74b9ceb8aa97072f41992a2bbf062809c7f16da | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/dashboard-owner-rf-compare | refs/heads/codex/dashboard-rf-report-compare | 1db861f15a6ad4dea5e06342a9f5d8fb64844066 | 0 (无 tracked 差额) | 0 | 0 | RF-B37 |
| C:/Users/郑曾波/Projects/dashboard-owner-rf-deploy-root | refs/heads/codex/dashboard-rf-deploy-root | c1e27877da9da8e78d5e76a08b7e090a6e096080 | 0 (无 tracked 差额) | 0 | 0 | RF-B37 |
| C:/Users/郑曾波/Projects/dashboard-owner-rf-identity | refs/heads/codex/dashboard-rf-identity-bridge | 11e0a2a7eab3f76f1a8dc2d6a75f5298be678ec6 | 0 (无 tracked 差额) | 0 | 0 | RF-B37 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b34-rf-alias | refs/heads/codex/dashboard-rf-b34-alias | d8890b4a09e4f73666db97296cc8743ec341fe70 | 0 (无 tracked 差额) | 0 | 0 | RF-B37 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b34-rf-catalog | refs/heads/codex/dashboard-rf-b34-catalog | a72cec5a74bf7ef9ffdf22a8fdef444cdf63adc2 | 0 (无 tracked 差额) | 0 | 0 | RF-B37 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b34-rf-publication | refs/heads/codex/dashboard-rf-b34-publication | 2b89730c0d7a5f977145fbe135a8cc8a53068565 | 0 (无 tracked 差额) | 0 | 0 | RF-B37 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b34-rf-release | refs/heads/codex/dashboard-rf-b34-release | 7f1d3a990b7814724ee91dca832d98ebe29960af | 0 (无 tracked 差额) | 1 | 0 | RF-DOC；ROOT 分类保留 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b34-rf-source | refs/heads/codex/dashboard-rf-b34-source | 28cdf12eb08aa2545d7640ac224583e005b2ecdb | 0 (无 tracked 差额) | 0 | 0 | RF-B37 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b35-rf-lineage | refs/heads/codex/dashboard-rf-b35-lineage | 9cbc32c98931caa1ce49fea304b8be50f6f11b54 | 0 (无 tracked 差额) | 0 | 0 | RF-B37 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b37-rf-publication | refs/heads/codex/dashboard-rf-b37-publication | a5afa6d248d1b279d160224330abaf6c6da86dcb | 0 (无 tracked 差额) | 0 | 0 | RF-PUB |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b37-rf-release | refs/heads/codex/dashboard-rf-b37-release | 28d646d306e8f0b5f90d402e204676cf97d2b5a1 | 0 (无 tracked 差额) | 0 | 0 | RF-B37；配置引用保留 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b37-rf-scope | refs/heads/codex/dashboard-rf-b37-scope | 21decc17be9de1d039347b19d71e9e344c9387db | 0 (无 tracked 差额) | 0 | 0 | RF-B37 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/owner-rf | refs/heads/codex/dashboard-rf-report-catalog | 430fabb4ff3d52c7859d83598eba3dc46d0e47de | 0 (无 tracked 差额) | 0 | 0 | RF-B37 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/return5-rf-audit | refs/heads/codex/d00-return5-rf-audit | c1e27877da9da8e78d5e76a08b7e090a6e096080 | 0 (无 tracked 差额) | 3 | 0 | RF-B37；ROOT 分类保留 |
| C:/Users/郑曾波/Projects/revenue-forecast-dashboard-owner-release-20261109 | refs/heads/codex/dashboard-owner-release-20261109 | cd24976a958bc2abee841a592691268b45b117ee | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-du11-citation-closure | refs/heads/codex/du11-rf-citation-closure | d578da58b01b6cb9d3145ca88c0c292911398607 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-du5-units | refs/heads/codex/du5-rf-units-20261015 | e2f6afd01789e9d355fd169b15b7db97d3253173 | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/revenue-forecast-du6-targets | refs/heads/codex/du6-rf-targets-20261016 | 86ca29411fbed1eaf2958b2eff579395f7d151a7 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-du67-integration | refs/heads/codex/root-du67-rf-20261016 | 2a68c6878c8bfd2b88c208d1bbc87540dedd6676 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-du8-comparison | refs/heads/codex/du8-rf-comparison-20261016 | 8845bc180efaf8b1638ee2056e5152014b425dd5 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-r1-boundary | refs/heads/codex/r1-narrative-availability | 674d08d92fe2ec64e1d42a3ebab0b364e0ac4354 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-r1-local-observation | refs/heads/codex/r1-local-budget-observation | 32f013a979dedd6310a43877e818c69f614dd2b2 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-r1-research | refs/heads/codex/r1-w09-research-20261023 | eb7c2deec3650889a10220fdfe8fccb168b28c72 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-r1-targets | refs/heads/codex/r1-targets | 95c8136a64e2049a8f63e47de33bdfaa82534cc1 | 0 (无 tracked 差额) | 17 | 0 | A；ROOT 分类保留 |
| C:/Users/郑曾波/Projects/revenue-forecast-w14-clean-chain | refs/heads/codex/w14-rf-clean-chain-20261024 | cafcfa42d0c8ff227fa56d58fc888e683be7ce61 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-w16-basis | refs/heads/codex/w16-rf-basis-20261025 | 611b1d62b2eb3228df037c95145a1d8d8d1f01d8 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-w20-adoption | refs/heads/codex/w20-rf-adoption-20261028 | 3e8fbc5522a814abc4db7d828c3e4dcf84f308b8 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/rf-impl | refs/heads/codex/rf-preserved-main-wip-20261006 | 6fb2def709d13bda9cfada7ecf62bfc0e3744ae2 | 242 ( M:4,A :230,M :8) | 0 | 0 | A；dirty 见本仓正文 |
| C:/Users/郑曾波/Projects/rf-input-prep-01-wt | refs/heads/codex/rf-input-prep-01 | 4ab5ef4d89211a8a21b09aad04a398776af325be | 0 (无 tracked 差额) | 0 | 0 | RF-RESEARCH |
| C:/Users/郑曾波/Projects/rf-job-facade-01-wt | refs/heads/codex/rf-job-facade-01 | d347c4ab43c847432ea354446cfea2947bf81d28 | 0 (无 tracked 差额) | 0 | 0 | RF-JOB |
| C:/Users/郑曾波/Projects/rf-mainline-integration-20261004 | refs/heads/codex/p5-rf-main-integration | 6e6b817a1a6e4567293a4dcb835815f3be508a03 | 0 (无 tracked 差额) | 0 | 0 | A |

### stockwiki worktrees

| 绝对路径 | before 分支 | HEAD | tracked 状态数量/类型 | untracked 数 | 状态读取 | 处置依据 |
|---|---|---|---:|---:|---:|---|
| C:/Users/郑曾波/Projects/StockWiki | refs/heads/master | 12c441e86282135b49120112dcf21c17509bbdd0 | 0 (无 tracked 差额) | 7 | 0 | A；ROOT 分类保留 |
| C:/Users/郑曾波/AppData/Local/Temp/stockwiki-narrative-consumer-20261003 | refs/heads/codex/stockwiki-narrative-consumer-20261003 | 4c3334ed412a6a6241eac307f20ad0593355f90f | 2019 ( D:2019) | 0 | 0 | A；dirty 见本仓正文 |
| C:/Users/郑曾波/AppData/Local/Temp/stockwiki-w04-mic-relations-20260930 | refs/heads/codex/stockwiki-w04-mic-relations | afa969226dd56d1d0a729990eb6bd30912fd7a45 | 1991 ( D:1991) | 0 | 0 | A；dirty 见本仓正文 |
| C:/Users/郑曾波/Projects/_g2/sw/StockWiki | refs/heads/codex/g2-sw-daily | 0b48919065a912f1da10d89d36bf6bf1e659db88 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/sw-permission-residue | refs/heads/codex/main-permission-residue-20261009 | d98acdcdf1a2feada2ae91f2f56aafaa74046728 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/d4-01-20261102/stockwiki | refs/heads/codex/d4-01-company-source-virtualization | 23d84586dc2425961e953f5ab28aef867de6cb87 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/d5-20261105/stockwiki | refs/heads/codex/d5-sw-processed-reader | 6d1e40bcdcde5e99488e22c38d57bd8e1b33c27e | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/d00-b03-stockwiki | refs/heads/codex/d00-b03-stockwiki | 652f6a48992b260cfb9fe25d6496341dc6ecba5a | 0 (无 tracked 差额) | 0 | 0 | SW-B03 |
| C:/Users/郑曾波/Projects/dashboard-owner-stockwiki | refs/heads/codex/dashboard-stockwiki-public-research | f6c402cd9685604204c488c89000775f283cd9be | 0 (无 tracked 差额) | 0 | 0 | SW-C38 |
| C:/Users/郑曾波/Projects/dashboard-owner-stockwiki-b-integration | refs/heads/codex/dashboard-stockwiki-b-integration | 194abedfcaa617dadb3cee90474606fbe3f1b0ad | 0 (无 tracked 差额) | 0 | 0 | SW-C38 |
| C:/Users/郑曾波/Projects/dashboard-owner-stockwiki-identity | refs/heads/codex/dashboard-stockwiki-identity-bridge | 9c47effec043985da5df419e5713d6c5dc91b6ea | 0 (无 tracked 差额) | 0 | 0 | SW-C38 |
| C:/Users/郑曾波/Projects/dashboard-owner-stockwiki-onboarding | refs/heads/codex/dashboard-stockwiki-onboarding | 042951b3f8ab5c9d0148d5542bb819633ffcbe08 | 0 (无 tracked 差额) | 0 | 0 | SW-C38 |
| C:/Users/郑曾波/Projects/dashboard-owner-stockwiki-proof-read | refs/heads/codex/dashboard-stockwiki-proof-read | eca69e1c463e472591c1b4cb1833d34e0f21b96d | 0 (无 tracked 差额) | 0 | 0 | SW-C38 |
| C:/Users/郑曾波/Projects/dashboard-owner-stockwiki-research-scope | refs/heads/codex/dashboard-stockwiki-research-scope | a4eb1a39820718ca290df7aaeb8b7055a9ce2427 | 0 (无 tracked 差额) | 0 | 0 | SW-C38 |
| C:/Users/郑曾波/Projects/dashboard-owner-sw-b03-assessments | refs/heads/codex/dashboard-owner-sw-b03-assessments | 586b2f7e73688aef2c16e6881591953637a1cf32 | 0 (无 tracked 差额) | 0 | 0 | SW-B03 |
| C:/Users/郑曾波/Projects/dashboard-owner-sw-c1-authority | refs/heads/codex/dashboard-owner-sw-c1-authority | 60a85efd536349ee7efb89744a3f4a79bbbcec4b | 0 (无 tracked 差额) | 0 | 0 | SW-C1 |
| C:/Users/郑曾波/Projects/invest-quick-scan/.worktrees/stockwiki-dashboard-ports-20261109 | — | c2c65c60fa6ad3fe1d73a2ea9ee27747264c7fff | 0 (无 tracked 差额) | 0 | 0 | detached；第 4 节已核 ancestry |
| C:/Users/郑曾波/Projects/invest-quick-scan/.worktrees/sw-f05-fact-ingest-20261109 | refs/heads/codex/f05-fact-ingest-20261109 | 93b25927f58b129628776b349f8bda7f2f264dba | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b31-sw-release | refs/heads/codex/dashboard-sw-b31-release | aa0a69f09f1f35bae2f9ea7a0498988069491faa | 0 (无 tracked 差额) | 0 | 0 | SW-C38 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b33-sw-binding | refs/heads/codex/dashboard-b33-sw-binding | e22f15a6df23daef8403b783f5a36ee1bb115c1c | 0 (无 tracked 差额) | 62 | 0 | SW-C38；ROOT 分类保留 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b34-sw-id-repair | refs/heads/codex/dashboard-sw-b34-id-repair | 07fbb8a1169cca8dc17884002e78790219d906ca | 0 (无 tracked 差额) | 5 | 0 | SW-B34；ROOT 分类保留；配置引用保留 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b37-sw-subject | refs/heads/codex/dashboard-sw-b37-subject | c73dd8b0e9fe067a1767dc8c8f99663a4fe6fdef | 0 (无 tracked 差额) | 0 | 0 | SW-C38 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/c38-sw-release | refs/heads/codex/dashboard-c38-sw-release | 4532b0da00a38eb74d5464466a166dc38b890222 | 0 (无 tracked 差额) | 0 | 0 | SW-C38 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/return5-sw-audit | refs/heads/codex/d00-return5-sw-audit | 5dbcede6be50be6fdde7a317ce60c3e25d4a18a1 | 0 (无 tracked 差额) | 14 | 0 | SW-C38；ROOT 分类保留 |
| C:/Users/郑曾波/Projects/StockWiki-f05-mainline-wt | refs/heads/codex/f05-owner-runtime-01 | 3799b439cfd9808b428eca85b07d5e18b9b3370c | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/StockWiki-identity | refs/heads/codex/identity-snapshot-w02-w03 | ae11135cc1160adc74cc1d307ca8bd73cb4fa832 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/StockWiki-lane-integration | refs/heads/codex/stockwiki-lane-integration | 52add7fd8710b6c7e4b4f4294b358cc10cd01ac8 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/StockWiki-sw-ident | refs/heads/codex/stockwiki-sw-ident | 0c8603e43f8fa42bc9a877d43715826c8a48c121 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/StockWiki-v2-reader | refs/heads/codex/source-export-v2-reader | 0b406832b744892df7b592ca5d5c0d9fe2a0e3da | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/StockWiki-w04-g2b | refs/heads/codex/stockwiki-g2b-owner-context | 6f0c2c4abe9b70e0e9c48c32e80f883a14c40983 | 0 (无 tracked 差额) | 0 | 0 | A |

### audit worktrees

| 绝对路径 | before 分支 | HEAD | tracked 状态数量/类型 | untracked 数 | 状态读取 | 处置依据 |
|---|---|---|---:|---:|---:|---|
| C:/Users/郑曾波/Projects/revenue-forecast-audit | refs/heads/main | 3589b69cb9d28d7395607ce4fe689025b9acee96 | 0 (无 tracked 差额) | 2 | 0 | A；ROOT 分类保留 |
| C:/Users/郑曾波/Projects/_harness_worktrees/p7/audit | refs/heads/codex/w04-audit-capture-20261011 | c0993332623637d53f059350a382d99a95ef731d | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/pool-20261009/audit-events | refs/heads/codex/pool-audit-event-compat-20261009 | 681f2d19ff3058408fa0ceefa4919039b5b486db | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop | refs/heads/codex/w05-audit-loop | 2ed0b5e2dcaf3c5b2436e6a61bcf06f8fb03ac3a | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop-root | refs/heads/codex/root-w05-audit-loop-20261011 | 321d4c165575e81add3b4aa1ee9ba0a047ca6082 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures | refs/heads/codex/w06-audit-measures | 6a50d7ed1b4cf389589c7ca62b4ab161b5dc0ad1 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures-root | refs/heads/codex/root-w06-audit-measures-20261011 | 9cd5ff8a2c8f9c1726c4047785164e3263673614 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/w07/audit-analyst-quality | refs/heads/codex/w07-audit-analyst-quality | e3206880224f7fa97d3923cb70044a6956f7d2f4 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-audit-analyst-reception | refs/heads/codex/root-w07-audit-analyst-reception | e7c92577e853f6567475dcd26d54bdd30f5ab141 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/_harness_worktrees/w08/audit-evidence | refs/heads/codex/w08-audit-evidence | 96889c6a6d0d85b9c0ff6f54e35c4ea73e648bb6 | 0 (无 tracked 差额) | 9 | 0 | A；ROOT 分类保留 |
| C:/Users/郑曾波/Projects/revenue-forecast-audit-du5-summary | refs/heads/codex/du5-audit-summary-20261015 | 583a13d9ed667cb58f15348d22582d5f361e5cb3 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-audit-du6-import | refs/heads/codex/du6-audit-import-20261016 | c603d23d6ba731ed2f510f30a731f6ef3f3b43d3 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-audit-du67-integration | refs/heads/codex/root-du67-audit-20261016 | 8fd5a33949735422abbf3a5f39108d1fc606edb1 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-audit-du8-integration | refs/heads/codex/root-du8-audit-20261016 | 7ea6071b42ffb5155cf3d0741ac0603708aad6fa | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-audit-du8-measures | refs/heads/codex/du8-audit-measures-20261016 | 3ed248df06b2ba00e4f59d930647149ecc1f88af | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-audit-w15-portable | refs/heads/codex/w15-audit-portable-20261024 | 9bc2248f7d66636a7ce5e5d23933b0f7ac12eb49 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-audit-w17-coverage | refs/heads/codex/w17-audit-coverage-20261025 | 7c71c8111f14a3aae6a1df274eeffb81c01939b7 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/revenue-forecast-audit-w20-checkpoints | refs/heads/codex/w20-audit-checkpoints-20261028 | 5b8aa7182e7f7b219b0ef279106f1fc1886137b1 | 0 (无 tracked 差额) | 0 | 0 | A |

### dashboard worktrees

| 绝对路径 | before 分支 | HEAD | tracked 状态数量/类型 | untracked 数 | 状态读取 | 处置依据 |
|---|---|---|---:|---:|---:|---|
| C:/Users/郑曾波/Projects/investment-dashboard | refs/heads/main | b707473a1166d3f8740170dad77cb21aa09863ce | 4 ( M:4) | 8 | 0 | A；dirty 见本仓正文；ROOT 分类保留 |
| C:/Users/郑曾波/.codex/worktrees/dashboard-d01-architecture/investment-dashboard | — | 5e6a7fa97af430997346ecf8606ac6c81ae984e1 | 0 (无 tracked 差额) | 0 | 0 | detached；第 4 节已核 ancestry |
| C:/Users/郑曾波/.codex/worktrees/dashboard-d02-experience/investment-dashboard | — | 5e6a7fa97af430997346ecf8606ac6c81ae984e1 | 0 (无 tracked 差额) | 0 | 0 | detached；第 4 节已核 ancestry |
| C:/Users/郑曾波/.codex/worktrees/dashboard-d03-adapters/investment-dashboard | refs/heads/codex/d00-four-package-acceptance | dc345e8423c3464868a5229d65f42116abdef14e | 1 ( M:1) | 166 | 0 | A；dirty 见本仓正文；ROOT 分类保留 |
| C:/Users/郑曾波/.codex/worktrees/dashboard-d03-adapters/investment-dashboard/.worktrees/d06-e13-public-cli | refs/heads/codex/d06-e13-public-cli-20261107 | 0c60e5daed0ad1a0ae21f7cd1e2eec22e4dab7ca | 1 ( M:1) | 0 | 0 | A；dirty 见本仓正文 |
| C:/Users/郑曾波/Projects/_b03live/dashboard | refs/heads/codex/x-b03-live-owner-verify-01 | 72529d78441d1c866e29ba725a2c8e42c7d3a7f8 | 0 (无 tracked 差额) | 0 | 0 | D-EVIDENCE |
| C:/Users/郑曾波/Projects/d00-b03-dashboard | refs/heads/codex/d00-b03-dashboard | 6ea719ce6eac17165b70a633a21c250f39543622 | 1 ( M:1) | 0 | 0 | A；dirty 见本仓正文 |
| C:/Users/郑曾波/Projects/dashboard-b-listing-read | refs/heads/codex/dashboard-b-listing-read | eec8963ea160cd16756ef508c9c79e5ad6202d3a | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/dashboard-b-preview-isolation | refs/heads/codex/dashboard-b-preview-isolation | 7bac216abd1fead3602ca232d2f19340e2ad9a72 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/dashboard-b-transport-bounds | refs/heads/codex/dashboard-b-transport-bounds | 42d353201c368f829bcba55c324e473ad341e0c5 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/dashboard-c1-request-authority | refs/heads/codex/dashboard-c1-request-authority | d02a228818c0cededaa8f6600c1b256c47a797b0 | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/dashboard-c1-universe-protocol | refs/heads/codex/dashboard-c1-universe-protocol | 6a747549f489280cf275aa9a1f7f3352a0697e84 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/dashboard-e14-capture-followup | refs/heads/codex/dashboard-e14-capture-followup | 3ca737888e4a4fdf3cf5662dd3f977c2c0ceffeb | 0 (无 tracked 差额) | 0 | 0 | D-E14 |
| C:/Users/郑曾波/Projects/dashboard-e14-real-zoom | refs/heads/codex/dashboard-e14-real-zoom | 8a189c0080aadcc5e6cabeab9063bedce8bb228f | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/dashboard-iqs-b-read-projection | refs/heads/codex/dashboard-iqs-b-read-projection | 27024c2622cc790afd92f624496c2a508909cafb | 0 (无 tracked 差额) | 0 | 0 | D-EVIDENCE |
| C:/Users/郑曾波/Projects/dashboard-iqs-b03-company-result | refs/heads/codex/dashboard-iqs-b03-company-result | 8f126ed1afd7b21f8ebed39e2c2264454fa5c2b2 | 2 ( M:2) | 36 | 0 | D-B03；dirty 见本仓正文；ROOT 分类保留 |
| C:/Users/郑曾波/Projects/dashboard-issuer-proof-contract | refs/heads/codex/dashboard-issuer-proof-contract | ba0abe2cde9869bc4fae98499f3a738dd4babe2e | 0 (无 tracked 差额) | 0 | 0 | D-EVIDENCE |
| C:/Users/郑曾波/Projects/dashboard-rf-provider-discovery | refs/heads/codex/dashboard-rf-provider-discovery | c4b0d6af083d81c5d28ef7e5630080ac875ca6bf | 0 (无 tracked 差额) | 0 | 0 | D-EVIDENCE |
| C:/Users/郑曾波/Projects/dashboard-sw-research-bind-design | refs/heads/codex/dashboard-sw-research-bind-design | 14321f6ff889d8de198b9ec5bf28af8bf4860a4f | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/invest-quick-scan/.worktrees/dashboard-iqs-protocol-20261109 | refs/heads/codex/e12-iqs-dashboard-closeout-20261109 | efad14ff6292924b90a030d8ab87365ca66db8b4 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/all31-listing-fix | refs/heads/codex/d00-all31-listing-fix | e158288c622553bff17ed631a90a33dc0b57a9e9 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/all31-listing-preview-combo | refs/heads/codex/d00-all31-listing-preview-combo | e158288c622553bff17ed631a90a33dc0b57a9e9 | 120 (A :104,M :16) | 0 | 0 | A；dirty 见本仓正文 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/all31-preview-audit | refs/heads/codex/d00-all31-preview-audit | 475d44d133dfa781f7137cc292ad15d3e9660bf4 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/all31-preview-fix | refs/heads/codex/d00-all31-preview-fix | 475d44d133dfa781f7137cc292ad15d3e9660bf4 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/all31-transport-audit | refs/heads/codex/d00-all31-transport-audit | c544ebdb1cdacf5614257bcc57e4967f2a4dde7e | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/all31-universe-audit | refs/heads/codex/d00-all31-universe-audit | fa8e09a35a86018aa354dc79503281f227fc854c | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b-forecast-iqs | refs/heads/codex/dashboard-b-forecast-iqs | 351a68fb4e841dd4173c76288b50215955aa869a | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b-owner-config | refs/heads/codex/dashboard-b-owner-config | 51d6ad2e5e395e579be046adf7961e8481fe5ea2 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b-real-browser | refs/heads/codex/dashboard-b-real-browser | 6d18617199736ef54ede3aa958cbd60c73fd5a8f | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b-real-code-audit | refs/heads/codex/dashboard-b-real-code-audit | 66566afc821e0c0f8993af2ceb75d8a7a24f6e39 | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b-real-connections-fix | refs/heads/codex/dashboard-b-real-connections-fix | 870c7e676dc8a6d0fa90dbd9d1898c2a6c9b633a | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b-real-listing-plan | refs/heads/codex/dashboard-b-real-listing-plan | d1c252f806a78e967ff3e24507dee1462939100e | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b-real-owner-packet-audit | refs/heads/codex/dashboard-b-real-owner-packet-audit | 39a4770bae51fe8e360700657396e653c9639650 | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b-real-rf-compare | refs/heads/codex/dashboard-b-real-rf-compare | 72774b6019a7b4f5946c3f282eeef295895d8fdf | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b-real-source-check | refs/heads/codex/dashboard-b-real-source-check | b015b895e7029ffcfa22ddcc541df7704154365f | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b-source-research | refs/heads/codex/dashboard-b-source-research | 4cbc36f9a8d7677088c48d0f0709fe4d754417f2 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b31-browser | refs/heads/codex/dashboard-b31-browser | 0767d71fe3f374fa7d9f8b76e5dd054ad51472ef | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b31-independent | refs/heads/codex/dashboard-b31-independent | 3bb5a933de10558e5d0f0897f70ccb1279320fc0 | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b31-integration | refs/heads/codex/dashboard-b31-integration | ac8fbca835f6f94fd4881de6eeabe3799be967be | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b31-pagination-repair | refs/heads/codex/dashboard-b31-pagination-repair | fb2ca21916febc8a23ba4d5b68c723cada4c8100 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b31-public-adapters | refs/heads/codex/dashboard-b31-public-adapters | d2c48fe2fcd030fda0815a07643aa543752a51fc | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b32-audit-bind | refs/heads/codex/dashboard-b32-audit-bind | 4163def0614dd76e0e4986dde6509743e30ca436 | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b32-audit-combined-transport | refs/heads/codex/dashboard-b32-audit-combined-transport | d5f5f42a92810375faee6f078507da12e0539fc0 | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b32-audit-combined-universe | refs/heads/codex/dashboard-b32-audit-combined-universe | 5c086ab90df81e04092e0f3c1a47f2739ab79293 | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b32-audit-transport | refs/heads/codex/dashboard-b32-audit-transport | 4424e7fb2aaee575e340db57e60432169dee06de | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b32-audit-universe | refs/heads/codex/dashboard-b32-audit-universe | 3d4f406e41941bf115f5eff7837ac25b6d8699b0 | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b32-bind-fix | refs/heads/codex/dashboard-b32-bind-fix | c1996068f82e2d2ee7b60c928afad0e223ce9814 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b32-integration | refs/heads/codex/dashboard-b32-integration | e8a13d8605ce4391c2a5fb09073b7c00534a61dc | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b32-transport-fix | refs/heads/codex/dashboard-b32-transport-fix | 77776f351895294947a702735bc1de712809c006 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b32-universe-fix | refs/heads/codex/dashboard-b32-universe-fix | cd2e88511928e747ee26f8e51d207e62c2bf4537 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b33-integration | refs/heads/codex/dashboard-b33-integration | 6c8439557505563e25c2022359d592dbfbc8c53a | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b34-combination-ui | refs/heads/codex/dashboard-b34-combination-ui | c250a153af6bfbd69a2e003342e674326e81072c | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b34-integration | refs/heads/codex/dashboard-b34-integration | 0338c24b09afc4f4be5623c1a538e4a8d5d70a1e | 0 (无 tracked 差额) | 167 | 0 | A；ROOT 分类保留 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b35-bridge | refs/heads/codex/dashboard-b35-bridge | 03c22de6657217a7633c7a583fa182940e2c1c35 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b35-integration | refs/heads/codex/dashboard-b35-lineage | 5e0c29fe9417011711dc7ed0ce077ba20d44e4b7 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b37-integration | refs/heads/codex/dashboard-b37-revision | 61b73eb95e1748659a875a7bfd7cf294225ca893 | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/c38-integration | refs/heads/codex/dashboard-c38-integration | 88327c388cd7f389d1a26d3a1fd4edd30d478eea | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/d00-c04-combination | refs/heads/codex/d00-c04-combination | a909b5962ff86fd65c540ced7075681fc80626e3 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/d01 | refs/heads/codex/dashboard-d01-architecture | 51a19c905909fa1611b338baaf282f72866772c2 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/d02 | refs/heads/codex/dashboard-d02-experience | d728b92ea7d237167554e3a23eb28c19fb55e6f1 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/d03 | refs/heads/codex/dashboard-d03-adapters | 9d563b390f11763a6b3cf04b479da07d9248dc4b | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/d03-e13-public-stream-test | refs/heads/codex/d03-e13-public-stream-test-20261107 | 5d2a761ac75c19ada92a2a79c90e4ecf953055ad | 0 (无 tracked 差额) | 0 | 0 | D-STREAM |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/d04 | refs/heads/codex/dashboard-d04-product | 54d787d470f700a6414c5b81540ed481d0bae719 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/d05 | refs/heads/codex/dashboard-d05-audit | 32646f35e112016d8cbaf5ebc0d01d76cf583ad4 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/d06 | refs/heads/codex/dashboard-d06-usability | 07cb95987c43db10fea9b5533c71fcc38583bad9 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/e08-real-launch | refs/heads/codex/m1-e08-real-launch-01 | 4334a981b83f1a12b9bb0e0a0f0bbd7c46946825 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/e14-d00-capture | refs/heads/codex/dashboard-e14-d00-capture | 3ca737888e4a4fdf3cf5662dd3f977c2c0ceffeb | 0 (无 tracked 差额) | 3 | 0 | D-E14；ROOT 分类保留 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/e14-d00-review | refs/heads/codex/dashboard-e14-d00-review | d360f9b42bc486bbb9f83429255c0bb6498d726f | 0 (无 tracked 差额) | 2 | 0 | A；ROOT 分类保留 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/m0-fe-test-infra | refs/heads/codex/m0-fe-test-infra-01 | 271dd3133372dee046a1c9f7d81f059a87e2c3b5 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/m0-test-suite | refs/heads/codex/m0-phase0-modularity-01 | 37bc9009f595cd2cecbeb1b8e6a31e51afebe97e | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/m5-e05e06-ext-01 | refs/heads/codex/m5-e05e06-extension-01 | 88063c5b79446d9cdfe3d76c71f1ed122c7d3bc4 | 1 ( M:1) | 0 | 0 | A；dirty 见本仓正文 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/return5-listing-audit | refs/heads/codex/d00-return5-listing-audit | e158288c622553bff17ed631a90a33dc0b57a9e9 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/x-c01-schema7-rehearsal | refs/heads/codex/x-c01-schema7-rehearsal | 9bfadfe84f64d5b5de0b3a1fc1598ad7d16dd254 | 0 (无 tracked 差额) | 0 | 0 | D-EVIDENCE |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/x-c02-ff-aggregate-context-01 | refs/heads/codex/x-c02-ff-aggregate-context-01 | 82276d64b670884374fe1903478546d3a2b8329d | 0 (无 tracked 差额) | 0 | 0 | D-FF |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/x-c02-ff-statements-read-01 | refs/heads/codex/x-c02-ff-statements-read-01 | 8c4e1d27ce13a04ec63b25aa4ab681d4f7588e9e | 0 (无 tracked 差额) | 0 | 0 | D-FF |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/x-c04-compat-dashboard | refs/heads/codex/x-c04-current-main-compat-01 | 1375d64e80ad8c491e61532b65d27be509791940 | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/x-c04-integrity-repair | refs/heads/codex/x-c04-integrity-repair-01 | 9a27b152d0128374726007982057021e083408f8 | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/x-c04-original-stream | refs/heads/codex/x-c04-cwp-original-stream-01 | e3f443f153c1c56fff9d014242fcae8ff22c3b3a | 0 (无 tracked 差额) | 0 | 0 | P |
| C:/Users/郑曾波/Projects/investment-dashboard-e15 | refs/heads/codex/x-e15-2000-ui-perf-slice-01 | 976b1991cbb6f7fab7f750035cca324f80c7419d | 0 (无 tracked 差额) | 0 | 0 | A |
| C:/Users/郑曾波/Projects/investment-dashboard-owner-adapters-20261109 | refs/heads/codex/dashboard-owner-adapter-contracts-20261109 | 8e3231c319b0c845514d7a40036f8800795cf4f0 | 0 (无 tracked 差额) | 0 | 0 | D-ADAPTER |

## 10. 尚未验证与本报告的终态

- 不把历史 handoff 测试数当本轮结果；Dashboard 本轮 ROOT 已报告 189 passed、两个 adapter 29 passed/70 subtests，同时真实 owner stream 的 24 cases 因 T-READ 入口缺失未通过；日志、提交/推送与 cleanup after inventory 由 ROOT 填入父计划。
- RF/SW release 尚未与 current main/master 整体接收，配置根也未由本子任务迁移。报告已给有限顶点、具体产品路径、冲突保留要求及可复用测试；其余工作写回原 MB-RF、SW verification/ROOT 卡，不另造整仓重构。
- 全部非祖先 + 已解释为集中 release 合同差额、旧主线改写吸收、独有证据、小适配器修复或 reader 原型；未将 cherry + 直接等同功能缺失。
- 四个 RF Temp 的原件发现覆盖了 before “只有少量/零 untracked”的误导性表象；明确保留。不要删除原件来使 Git 工区变干净。
- 不新增权限/签收门，不恢复冻结历史 writer，不更改 IQS，不读/写原始资料与真实数据库，不把 RF 预测质量或研究完整性混入模块解耦验收。

独立审查状态：Dashboard 本轮有限修复与两个 adapter 的设计审查无剩余阻断；真实 owner stream 的 24-case 组合未通过，仍是既有 T-READ/ROOT 卡必须保留的缺口。大型 RF/SW release 不应盲目并线，按原卡承接真实公共接口差额。此报告完成只读核销与路线建议，不宣称 ROOT 尚未执行的测试、清理、推送或部署已经完成。
