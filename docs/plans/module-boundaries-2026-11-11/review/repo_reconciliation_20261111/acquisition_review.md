# FF / ET / SID 分支与工作区复核

观察日：2026-11-11。审查者：acquisition 子代理。只读检查；本轮未执行测试、安装、网络、采集、付费调用、Git 写入或作者工区修改。本文是接收与清理建议，实际 fetch / 接收 / 清理由 ROOT 执行；ROOT 已报告三仓 origin fetch 成功且未出现新提交。下面 HEAD 是本轮接收动作前快照，不能覆盖 ROOT 随后的接收结果。

证据基准：[inventory_before.json.gz](C:/Users/郑曾波/Projects/company-wiki/docs/plans/module-boundaries-2026-11-11/review/repo_reconciliation_20261111/inventory_before.json.gz)。完整架构缺口与五卡写集另见 [acquisition_architecture.md](C:/Users/郑曾波/Projects/company-wiki/docs/plans/module-boundaries-2026-11-11/review/acquisition_architecture.md)。

## 1. 可执行结论

1. **FF B34 有独有且范围很小的正确性修复**：`53285c259b0f0c9ede3f74783f45b6f3a38287b9`，允许逻辑 SourceRef 候选明确保留 `published_date:null`，不把未知日期当成格式错误；三个文件。当前 main 仍缺失。建议 ROOT 隔离接收此实现提交并集中验证；handoff 提交单独保留证据，不整支覆盖当前跨市场修复。
2. **FF job 分支的 seven “cherry +” 不是七项漏并需求**：正式接收版 `57351d0` 已吸收作业功能；`7d8392e` 又修复使用量/恢复/重试。旧 job 工区 7 项 dirty 的全部新增语义已吸收，其中 6 个文件规范化 Git blob 与 `57351d0` 完全相同，第七份协议的两处 diff 都出现在该接收版。可按精确清单恢复旧工区后回收；不要再合整支。
3. **FF transcript-companion 原型是已明确替代的旧实现**：`29085f7` 不是 patch 等价，但 main PWF 明确记录因重叠实现和猜测 checkout 路径而不整支并入，由 `cf05f7e` / `492f5d4` 的正式 SourceRef/ET transport 接口替代。无需重做，可回收原型分支/工区。
4. **ET 全部 19 refs、SID 全部 6 refs 都是目标祖先**，没有漏并代码。ET 的 7 月 `eval_results.json` 是旧翻译评价生成物，生产代码没有读取引用，可清理；工具记忆另行保留。
5. **SID 11 项 dirty 有实际价值但不适合原样提交**：保留进入 MB-SID A0，先修路径比较、跨请求状态与 tab 范围等静态已确认缺口，再接收；不能用 7 月 E2E 或 README 测试数字冒充当前验收。未跟踪 fixture 捕获脚本是既有 fixture 的独有出处，应保留在 A0，不执行。
6. 四处 Temp 工区每一项跟踪文件都已被删除，HEAD 都是主线祖先且无 untracked：可清理旧 worktree 登记与空壳，不把这些删除当成代码变更合并。FF 旧 pytest 目录和空 du11 placeholder 是已知历史测试垃圾，ROOT 已确认可以清理。
7. W06/W07/SID G4 的少量 PWF/交接镜像具有历史出处价值，但没有漏并生产代码；归入对应 MB 卡 A0 的“资料归档与旧工区回收”。不要把过期完成声明重新并成当前状态。

## 2. 基线与方法

| 仓库 | 真正 Git 根 | 目标 / HEAD | 本地 / remote-tracking refs | worktree |
|---|---|---|---:|---:|
| FF | `C:/Users/郑曾波/Projects/filing-fetch` | `main@f65e6ca75fbce0616e65870f0aea78b793ef883c` | 43 / 11 | 38 |
| ET | `C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts` | `main@003c1c065109d0b02c7bd4de09ad3e8461a99c0e` | 15 / 4 | 13 |
| SID | `C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite` | `v2-clean-rewrite@c0f07e12d4ba3e232d712bb6e5e491832023b0a0` | 5 / 1 | 4 |

所有仓库均无 stash、tag 或 heads/remotes 之外的 refs。默认主工区 FF/ET tracked clean；SID 11 项 unstaged。全 worktree tracked dirty 总计 FF 337（328 个旧临时工区删除 + 7 job + 2 PWF）、ET 212（同一空临时工区）、SID 11。未跟踪路径总计 FF 1776、ET 4、SID 6；这些是路径数，不能等同于漏并代码量。

对每个 ref / detached HEAD 使用 `merge-base --is-ancestor`；对非祖先使用 `rev-list --left-right --count` 和 `cherry -v`。FF 非祖先三支的 cherry 均为 +，因此继续看接收提交、逐路径 blob、PWF/handoff、当前实现：从未仅凭 ahead 数或 handoff 的“已并线”声明定案。

本次不存在可直接声称“git cherry 判为 -”的未吸收分支。job 是接收版/压缩整合加修复后的吸收；原型是语义替代；B34 是真正尚缺。三者严格分开。

结构调查沿用第一轮 CodeGraph 结论（FF 索引滞后、ET 未初始化、SID 外层索引未覆盖当前包），未初始化/重建索引。此次主要问题是 Git 血统、文字出处与已知文件 diff，使用原生只读 Git/rg。未读取 API 密钥和真实公司原件内容；仅列出敏感文件路径用于保护。

## 3. 三条 FF 非祖先分支

### 3.1 B34：接收候选

- ref：`codex/dashboard-ff-b34-candidate@9be5587e4faf623a644e2cda591f70916f7c35fe`，目标独有 18 / 分支独有 2。
- 实现：`53285c259b0f0c9ede3f74783f45b6f3a38287b9`。
- 文档：`9be5587e4faf623a644e2cda591f70916f7c35fe`。
- 来源工区：`C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b34-ff-candidate`。
- 写集：`scripts/ff_source_candidate.py`、`scripts/filing_contracts.py`、`tests/b34/test_unknown_publication_candidate.py`；101 additions / 1 deletion。
- handoff：该工区 `docs/handoffs/dashboard-B34-source-candidate/handoff.md`。声明旧基线上的 19 新例、85 affected、111 legacy 等历史结果；本轮没有重跑，不当成当前绿灯。

当前 `scripts/filing_contracts.py:614–615` 无条件校验 publication date，`ff_source_candidate.py` 未 opt-in；因此缺口仍存在。实现只允许显式 null，缺字段、空串、伪“null”、错误日期、未来日期仍拒绝；默认 metadata 和 legacy deep validation 仍严格。其 `return` 只从基础 metadata 校验返回，调用者继续做 SourceRef/hash/size/MIME、kind/year、当前 main 新增 fiscal_period/form_type、source market/security/issuer_link_id 绑定。不会读原件，不产生 availability、source_read_receipt，byte_verified 仍 false。

**接收风险/验收**：将两处小改动移植到当前 main，保留其 `source_identity` 与期间检查；追加“null + 错 fiscal_period / form_type / 跨市场主体”的负例，避免使用旧文件覆盖当前新规则。未知发布日期不代表已通过 as-of availability，后续 consumer 仍有权拒绝。

在隔离候选根执行（由 ROOT，本文未执行）：

```powershell
$env:PYTHONPATH = "$PWD/scripts;$PWD/tests"
python -B -m pytest -q -p no:cacheprovider tests/b34/test_unknown_publication_candidate.py tests/test_source_ref_v2_db_query.py tests/test_bundle_compat.py tests/test_fetch_filing.py
```

对应当前跨市场改动还涉及 `tests/test_m3_acquisition_usage_ff.py`、`tests/test_architecture_quality.py`，由 ROOT 按实际接收 diff 纳入集中验证。当前不存在 `tests/test_cross_market_source_scope.py`，不得使用这个猜测文件名。

本轮若接收成功，MB-FF A0 标为已吸收，只留下边界隔离合同工作；若未接收，则保持精确三文件候选入 A0，不整支重构。

### 3.2 ff-job-facade-01：已吸收实现，保留历史出处

ref：`codex/ff-job-facade-01@154c292cb25293afd090aec4ef8859c2bb2b150d`，目标独有 4 / 分支独有 7。七个 cherry+ 提交依次：

| commit | 原用途 |
|---|---|
| `a34f60e4b5e1abcc986711939d374ad9f947ee10` | acquire submit |
| `8af832c6b55b5b8310c5b3f91d909a9cc7cf6378` | 跨进程 status/actions/page |
| `4e03941e349bad3ac4a3cb061313ed35765a7d29` | 幂等与实际费用 |
| `f3b5544af2ace25fd1e6de35e1c2315649e8cc3c` | unknown/read-only reconcile |
| `c5fa3f1df49de0bb345d2283a4145c987b51f9aa` | protocol/PWF/验收 |
| `eaf8a5ecbfcbfcb8cda12d8a9976f04121f7af38` | 重审/交接 |
| `154c292cb25293afd090aec4ef8859c2bb2b150d` | handoff固定 |

实际 main 接收 `57351d0053cb5be529b532bec1297b0da7788c79`（2026-11-09），随后 `7d8392eb98c50a6d6d27d06d9d7fabee913fe484` 修复 verified usage/retry/recovery。不能把旧分支 `handoff.md` 中“11-07 ff-only merged eaf8a5e”当当前图事实：当前 HEAD 图明确不含该分支祖先链，功能由后来的接收版进入。

`154c292..57351d0` 的 scripts/tests/tools/protocol 差异恰好只落在旧 dirty 的七条路径，其他作业实现文件相同。旧 dirty 规范化 blob 证据：

| 旧工区路径 | dirty blob = 57351d0 blob |
|---|---|
| `scripts/fetch_filing.py` | `b4bd9aaf1c831dca7d170ad8d595d1ff7c667533` |
| `scripts/ff_job_runner.py` | `2df23ec6a3f8f32a3aef170fefe6c4b6693a73f7` |
| `scripts/ff_job_store.py` | `e52e12236027ba57a82f2546660512631b61d13b` |
| `tests/test_ff_job_cross_process.py` | `d83c143cb51c252c833977db166da65ffb5e7d87` |
| `tests/test_ff_job_facade.py` | `076cad52f05ff7ef37fb24608db32e78cefc9866` |
| `tools/ci_tests.py` | `3f8b8ac54549b82494d09b011563247369895fc2` |

第七 `docs/ff-job-protocol.md` dirty blob 为 `852ed412d741a5494e23419666b84e1b966faac4`；与接收版整体不同，但 dirty diff 只含“OS lock 替代 dangling pointer grace”的说明和 `index/idem/.submit.lock` 条目，两者都在 `57351d0` 和当前 main。无未吸收功能。

可清理对象：`Projects/_harness_worktrees/dashboard-ff-job-20261109` 七项 dirty；`Projects/ffjf01`（clean旧分支）；release 工区 `.../dashboard-ff-job-release-20261109`（clean且祖先）。旧 `.planning/ff-job-facade-01/**` 的独立重审/原始验收是历史资料，归档后可删旧 ref；不得以旧 handoff 覆盖当前协议。

后续如只清旧副本，验证 blob/主线 ancestry 与精确 status 足够，不必重跑作业或采集。若接收新代码才跑现有 `tests/test_ff_job_facade.py`、`tests/test_ff_job_cross_process.py`。

### 3.3 transcript-companion：正式设计已取代的原型

ref `codex/transcript-companion@29085f76ed60b9fc756b613c870288670566f720`，目标独有 176 / 原型独有 1。该 WIP 原型变更五文件（SKILL、fetch_filing、filing_contracts、transcript_companion、tests）。

不是逐 patch 等价。但 main `findings.md:67` 明确记录：standalone companion 没有整支并入，因为与 fetch_filing 重叠且猜测 checkout 路径；统一分支复用 SourceRef producer 并引入显式 `EarningsTranscriptsTransport`。main `progress.md:36–48`、`task_plan.md:238–244` 记录 `cf05f7e3877b2daa1bd3b649e0496991541f6fdf` 与 `492f5d4` 集成及复杂度拆分。

当前 transport、可配置入口、bounded budget、reuse-before-provider、查询/导入/open 都在正式实现内，原型不能覆盖它们。分类：**obsolete/superseded，可删旧ref/clean工区，不开新施工**。保留本报告及已跟踪 main PWF 即可；若 ROOT 统一归档分支 bundle，可随其统一流程归档，但不新增人工审批。

## 4. Dirty / untracked 逐组处置

### 4.1 FF

| 对象 | 来源与用途 | 结论 / owner |
|---|---|---|
| 主工区 `.ff_jobs/**` 9 路径 | 3 jobs + 3 logs + 3 idempotency pointers，公开作业面真实 owner state | 保留；不是测试垃圾，不入Git、不重建、不试跑。MB-FF 边界只需说明部署状态目录 |
| `.mimosa/**` 205 路径 | 工具状态/baseline，不是新增产品代码 | 本轮没有证明全部无用；保留本地，MB-FF A0登记为工具私有状态，不挪作source owner数据 |
| `.workbuddy-ai/memory/2026-11-02.md` | 工具笔记 | 保留本地，不并线 |
| `config/FMP_API_KEY.txt` | 凭据文件；仅读取路径名 | 保留不读、不哈希、不复制、不提交 |
| `.planning/du11-empty-placeholder-original.py` | ROOT 已确认空占位历史垃圾 | 可定点删除；无需测试 |
| `pytest-of-ff-root-failures/**` 18、`pytest-of-ff-root-failures-fixed/**` 18、`pytest-of-ff-s3-p5-full/**` 51 | ROOT 已确认历史R7测试残留 | 可在核对绝对目标均在这三目录后清理；不用生产config，不扩删到.ff_jobs |
| Temp三个工区 185/93/50 D | 每处 dirty数 = ls-files数；HEAD均祖先，无untracked | 旧工区清空残留。仅清理登记/空壳，不提交删除 |
| dashboard旧job 7 M | §3.2逐blob/逐hunk证明已吸收 | 可精准清理，无新需求 |
| W06 `.planning/w06-ff-matrix/{task_plan,progress}.md` 两个M | 作者补“complete/16PASS”历史交接；main已有ROOT接收修复与41-case结果 | 不并旧完成声明；归档dirty diff后回收。MB-FF A0资料整理 |
| W06 `docs/handoffs/w06-ff-matrix/input/**` 六个untracked | ROOT下发 input/amendment/manifest，作者PWF明确 input未提交归ROOT | 不当代码；归档到既有接收证据后回收。其原路径不在main |
| W07 `.planning/w07-ff-matrix-efficiency/**` 六个untracked | START_HERE、HANDOFF_CONTRACT、INPUTS、.gitignore、case-handler-baseline、dependency-manifest。基线/约束历史输入 | 保留/归档出处，不合并成新施工；MB-FF A0 |
| W07 `.tmp/**` 1460 路径 | 9个attempt输出组，见下；生成测试资料，无生产源码dirty | 旧输出可回收候选。main已跟踪final/first-failure/timing/proofs/restore收据；本轮未证明每个旧attempt都逐字节重复。ROOT先保留其唯一报告/manifest或在A0归档再清，不能凭.tmp名字抹掉独有证据 |

W06六输入：`ROOT_INTERFACE_AMENDMENT.md`、`amendment_manifest.json`、`construction_card.md`、`handoff_contract.md`、`inputs.json`、`manifest.json`。当前 main PWF 与作者dirty并不逐字节一致，且 ROOT 记录已否定旧“全完成”的笼统含义；建议只保留历史证据。

W07九组路径数：`w07-b1`218、`b2`260、`b3`172、`b4`208、`b5`284、`b6`286、`w07-q-out`10、`q2-out`10、`q3-out`12，总计1460。main 已有 `docs/handoffs/w07-ff-matrix-efficiency/evidence/{final-41-report,final-41-proofs-g1,final-41-proofs-g2,final-41-restore,first-run-failure-report,timing-before-after}.json` 及 ROOT-reception/handoff。

### 4.2 ET

- 全部 branch/ref 与 detached `d0ac42c...` 均已吸收，不新增“漏并实现”。
- 主树 `.workbuddy-ai/memory/{2026-09-03.md,2026-11-02.md,MEMORY.md}`：工具私有笔记，本轮保留，不并线。
- `eval_results.json`：38,956B，mtime 2026-07-07T21:23:29Z。唯一生产代码文字引用 `eval_translation.py:252` 是输出路径；未发现运行读取引用。main `progress.md:89` / `task_plan.md:134` 已分类为旧 July translation evaluation artifact，其他 handoff 文档只把它当原状保护哨兵。分类为历史生成物，可删除；无需重新翻译或重新生成。
- Temp `et-fresh-transcript-launch-20261009` 的212D覆盖全部212 tracked，无untracked，HEAD `c91f5f54...`为祖先。清理旧登记，不提交这些删除。
- MB-ET A0只记录这些历史清理结果；原合同/settings/worker依赖方向整改保持，不为历史refs增加实现量。

### 4.3 SID：11项 owner WIP

历史出处：CWP [2026-10-04 SID审计](C:/Users/郑曾波/Projects/company-wiki/docs/plans/repository-state-audit-2026-10-04/results/stock_info_dl_simple.md) 已逐项记录这组7月CW-2.27D/H工作；G4 PWF也明确基线保留相同11项。现有 G4/G5主线验收只证明其卡内写集，不证明这11项。当前diff合计743 additions / 94 deletions。

| 文件 | 本轮读取的实际内容 / 价值 | 接收建议 |
|---|---|---|
| `README.md` | 批量company输入、progress、目录/清理用法、测试数字更新 | A0与实际接口同步；删除/修正未验证测试数量，不把硬编码CWP主机路径当产品默认边界 |
| `config_template.json` | prospectus max_pages 2→3；periodicReports allowed_keywords 年报/半年报/季报 | A0保留配置意图；以tmp模板fixture测试。禁止写真实config.json |
| `main.py` | 消费verification_warnings并改变success | A0修成明确owner验证结果，区分真实缺失/错scope与纯诊断；配main行为测试 |
| `src/browser.py` | 独立解析www/static关键host，裸域可选；button即时检测+短wait | 有价值但现有新测试仅查源码字符串；A0加mock DNS/launch行为验证，保持累计超时、不做真实DNS |
| `src/downloader.py` | typed空结果、tab选择、active links、post-download校验 | 主要价值与主要风险并存；先做下面RED再接收 |
| `src/logger.py` | StreamHandler stdout→stderr | 正确的JSON输出卫生候选；需隔离新进程stdout合同，不只测被CLI重定向后的情况 |
| `src/mapping.py` | _crawl_org_id移除catch-all吞错，让基础设施异常可见 | 有价值；加not-found与crawler异常不混淆的mock测试，明确旧调用者失败传播 |
| `src/models.py` | DownloadResult增可选load_state/error_code/retryable | 与downloader同组接收，兼容旧默认构造 |
| `tests/e2e/official_e2e_test.py` | report-suffix避免多轮覆盖；其余大多格式调整 | 保留用途，离线单元测两个报告名不同及suffix路径合法；不运行真实E2E |
| `tests/unit/test_downloader.py` | 新校验、状态、browser源码、CLI错误测试 | 不是完整验收；补真实行为反例，去脆弱源码字串/强制版本常量掩盖 |
| `tests/unit/test_official_e2e_contract.py` | mock接受新增suffix参数 | 与runner一起接收，并补新参数实际行为而非只改mock |

**确认的静态缺口（本轮未运行反例）**：

1. `src/downloader.py:598–599` 将 `raw/prospectus` 替换成反斜杠，再用字符串子串判断目录。POSIX正常目录会被误拒；Windows路径含 `raw/prospectus-extra` 也可能误接受。应按Path组件/相对目录语义验证，测试正确路径、相似兄弟路径、两种平台语义。
2. `src/downloader.py:244` 为保留预置空结果而跨调用保留 `CONFIRMED_EMPTY`；该标记没有request绑定/消费。用现有测试seam预置A为空，再同实例发B且页面无links，会继承A的空。当前真实API并未证明接入此私有seam，因此描述为**可由现有seam确定触发的状态合同缺口**，不声称已发生真实错公司下载。
3. `_switch_tab` 用全页面links数验证，`_get_links:618` active pane无结果后回退宽XPath；空目标tab而其他tab有链接时可能错误采集。补“目标空/隐藏tab非空”、“菜单未命中”和合法目标tab三个离线反例。
4. `DownloadResult.success=True` 携带verification_warnings，再由main二次判失败，使API与CLI成功语义分裂。校验警告本身包含真实文件缺失/错scope，也可能含第1项假告警；不能一概称其全是可忽略诊断，也不能把任意文字告警当许可。应由下载owner输出机器可读验证结果，CLI映射它。
5. Browser新行为缺乏mock行为测试；text搜索只证明词出现。报告suffix是新路径构造输入，应测分轮不覆盖及分隔符/父目录参数拒绝或规整。后者是接收测试缺口，本文没有声称发生目录写穿。

**MB-SID A0接收顺序**：冻结并保存11项patch和未跟踪fixture脚本的哈希/出处；在clean目标worktree复制受审patch，不改原工区。先为上述反例写RED，修正downloader/model/main一致性，再集中验证并合入；同卡随后完成typed provider error和pure metadata方向修复。无需新provider、重做Playwright或人工逐项放行。

现有离线集中命令（由实施者运行，本文未执行）：

```powershell
python -B -m pytest -q -p no:cacheprovider tests/unit/test_downloader.py tests/unit/test_main.py tests/unit/test_models.py tests/unit/test_mapping.py tests/unit/test_config.py tests/unit/test_official_e2e_contract.py tests/unit/test_company_wiki_adapter_cli.py tests/unit/test_cninfo_api_fixture_contract.py
```

新增用例建议放 `tests/unit/test_legacy_download_contract.py`：request-scoped-empty、active-tab-only、component-directory-match、verification-outcome-consistency、DNS critical/optional、stderr-only logging。报告suffix的用例放已有 `test_official_e2e_contract.py`。全部mock/tmp，不启动浏览器、网络或碰真实下载目录。最终原provider职责回归沿用 `test_cninfo_api.py`、`test_cninfo_api_budget.py`、`test_company_wiki_adapter.py`、`test_company_wiki_adapter_cli_budget.py`、`test_g4_latest_discovery.py`、`test_g5_provider_runtime.py`，与原MB-SID边界改动同一集中节点执行。

### 4.4 SID untracked

| 路径 | 用途/来源 | 处置 |
|---|---|---|
| `a_share_companies.txt`、`companies.txt` | 本地批次输入；README的--companies用法明确引用前者，未读名单内容 | 保留本地配置输入，不混入包。A0文档明确示例由tmp合成，不提交用户批次名单 |
| `scripts/capture_byd_fy2024_fixture.py` | CW-2.27E/Phase4的单次公开API metadata捕获器，生成已经tracked的2个CNINFO fixture；不下载PDF，固定公司/期间 | **独有出处保留**。无runtime引用；不执行、不重抓。A0将它作为历史fixture再现工具/说明接收，清理旧Gate文案不能扩成生产采集入口 |
| `_g4/.../docs/implementation/.planning/g4-sid-latest/{task_plan,progress,findings}.md` | PWF resolver镜像，D7明确解释与deliverable双路径；已完成G4，当前main正式docs已包含交接 | 非生产遗漏；镜像与main正式docs blob不相同（含历史时点），保留归档后回收，不能无证声称逐字节重复 |

fixture契约主线已有 `tests/unit/test_cninfo_api_fixture_contract.py`，涵盖real标记/公告数组/唯一全年报/日期/summary筛选/total一致/合成空标记/secret-shaped keys；脚本本身并非运行依赖。既有脚本固定公司是历史fixture出处，不是生产业务词典；无需为了保留出处强做通用下载器。

## 5. 归入原模块卡与有限完成条件

| 原卡 | A0新增接收清单 | 完成定义 |
|---|---|---|
| MB-FF | B34三文件；旧job/原型吸收证明；W06/W07历史资料归档及旧测试垃圾回收；保护jobs/密钥/工具状态 | B34在当前main通过限定合同回归并被ROOT接收，或有明确未接收原因；旧job无重复实现；每组残留归档/保留/清理结果可复算。原隔离契约仍可NO_CHANGE，不为卡存在强制重构 |
| MB-ET | 已吸收refs、空临时工区、旧eval生成物；工具记忆保留说明 | 无漏并分支；旧生成物清理有before/after。原contracts/settings/worker方向整改继续，历史盘点不加新provider |
| MB-SID | 11项patch+fixture出处脚本+3份G4镜像；本地公司名单保留 | 先补明确RED并修正WIP缺口，再受测接收；原typed error/pure metadata缺口同卡关闭。无需把用户名单或真实下载原件纳入Git |

这是既有五卡中三卡的A0，**没有增加第六张实现卡**。人工门禁数量不增加；原来集中验收/独立质量审查沿用。实际ROOT本轮能接收的B34、能清理的等价副本和生成物直接执行，不因本表再要求用户批准。

清理验证只需精确目标路径、git status前后、目标HEAD与候选吸收关系；不要为清理重新执行采集/付费/大规模E2E。删除前核对绝对路径仍在明确目标目录，不能递归扫全Projects。工作区存在被别的活跃任务使用的迹象时，保留目录并记录归属；这不是每个小动作新增审批。

## 6. 全部 refs 清单

“目标独有 / ref 独有”来自 `target...ref`，不是未吸收需求数量；祖先判定才证明已合入，非祖先另见§3。下表包含remote-tracking的origin/HEAD符号引用，不将其算成新分支。

### FF 全部 refs

| ref | HEAD | 目标独有 / ref 独有 | 判定 |
|---|---|---:|---|
| `refs/heads/codex/aq-ff-20261013` | `e2efa81d7995836d457479eb528fa6f8cd5dc3f3` | 110 / 0 | 已吸收（祖先） |
| `refs/heads/codex/ci-push-parity-20261009` | `23d25644a78390ebd5d7fd4da20e42d6788c1240` | 132 / 0 | 已吸收（祖先） |
| `refs/heads/codex/cmrf-provider-diagnostics-20261008` | `a1f3e4f18bf644c6af668fddc009cacdf1aace20` | 141 / 0 | 已吸收（祖先） |
| `refs/heads/codex/company-pool-failure-consumer-20261009` | `e9b0d0882f46772e333a5b986c7c414733c284cd` | 139 / 0 | 已吸收（祖先） |
| `refs/heads/codex/cwp-source-ref-v2-20261004` | `e1eda607f5536ebf7c498da2a128dedd2c7bd9f3` | 157 / 0 | 已吸收（祖先） |
| `refs/heads/codex/dashboard-ff-b34-candidate` | `9be5587e4faf623a644e2cda591f70916f7c35fe` | 18 / 2 | 独有修复，接收候选 |
| `refs/heads/codex/du10-ff41-close` | `ff2ba400ad37e1188b88ed61ff7a1814a647b94b` | 86 / 0 | 已吸收（祖先） |
| `refs/heads/codex/du11-ff-transcript-reuse` | `8a83e27863269b14c897dc2c7ba953f3b9102ef1` | 80 / 0 | 已吸收（祖先） |
| `refs/heads/codex/du6-ff-portable-20261016` | `ff08a8e04f2ae146e42daf9b36710b3ef1f47d89` | 105 / 0 | 已吸收（祖先） |
| `refs/heads/codex/du8-ff-matrix-20261016` | `6f381199f146109b4f517537a70da1c20c6e05bd` | 93 / 0 | 已吸收（祖先） |
| `refs/heads/codex/ff-job-facade-01` | `154c292cb25293afd090aec4ef8859c2bb2b150d` | 4 / 7 | 已按接收版吸收，非逐commit等价 |
| `refs/heads/codex/ff-s3-single-request-limits` | `1d0c73c2a6ea9a1273328ae84b67ab98141d2bb3` | 158 / 0 | 已吸收（祖先） |
| `refs/heads/codex/ff-source-companion-integration` | `c47c397c4d93979d8a7defbe026eff9e9edf0e6d` | 167 / 0 | 已吸收（祖先） |
| `refs/heads/codex/ff-source-reader-v2-20260927` | `aaf35bc19f9e716545c1f7a6a7e1a7c5ef0b5320` | 174 / 0 | 已吸收（祖先） |
| `refs/heads/codex/fresh-transcript-launch-20261009` | `5101b76ceaadff5dee559f3599f7ea737d3b5bd5` | 130 / 0 | 已吸收（祖先） |
| `refs/heads/codex/fresh-typed-cause-20261009` | `41ba0150c9c634f6021c9346744cada391ec2c4c` | 125 / 0 | 已吸收（祖先） |
| `refs/heads/codex/m3-acceptance-20261010` | `08ec85b27133cdf8a8d3b38fdba15255fc1ebac2` | 121 / 0 | 已吸收（祖先） |
| `refs/heads/codex/m3-acquisition-usage-20261010` | `f0f4e36319d6b3afc17e896f12a2aa1b183894b0` | 124 / 0 | 已吸收（祖先） |
| `refs/heads/codex/main-local-source-prepare-20261009` | `a1e97fa462f6fc381f18ce39641224310c7228a8` | 137 / 0 | 已吸收（祖先） |
| `refs/heads/codex/main-permission-residue-20261009` | `55b7347a29b98e6844e6bef8c0708a58a5c68e45` | 135 / 0 | 已吸收（祖先） |
| `refs/heads/codex/p5-ff-main-integration` | `211a56ff1b1f7b5c5d1809b17a60e9a2af1ce6e8` | 146 / 0 | 已吸收（祖先） |
| `refs/heads/codex/p5-ff-runtime-cleanup` | `ab9ce33b88d2e2ed914b95ac864fba80d8363c0a` | 151 / 0 | 已吸收（祖先） |
| `refs/heads/codex/pool-ff-response-budget-20261009` | `59c4d0d96f02e039298dfbbbbcd3f79200711f78` | 138 / 0 | 已吸收（祖先） |
| `refs/heads/codex/r1-local-budget-observation` | `130fd6b67c227768c6bbb8eb1acdf327bdf32428` | 63 / 0 | 已吸收（祖先） |
| `refs/heads/codex/r1-source-boundary` | `df9a1d3edab46768e30de134bdf9f71ca3fcf745` | 71 / 0 | 已吸收（祖先） |
| `refs/heads/codex/root-du10-ff-20261017` | `f1a939e522c22b23659712a8bd2b344f5eb0a364` | 84 / 0 | 已吸收（祖先） |
| `refs/heads/codex/root-du11-ff-reception` | `e8740748f91999cb24169b42f8e789726ed50482` | 76 / 0 | 已吸收（祖先） |
| `refs/heads/codex/root-du67-ff-20261016` | `e8a85585b4c64a9596e576ff3b73e5c2ee29c334` | 100 / 0 | 已吸收（祖先） |
| `refs/heads/codex/root-du8-ff-20261016` | `41f498827943676fc0d352124e286461c73726ca` | 92 / 0 | 已吸收（祖先） |
| `refs/heads/codex/root-w06-ff-matrix-20261011` | `2d380a054c658ce3b5f0763523e49a0ab34acf78` | 117 / 0 | 已吸收（祖先） |
| `refs/heads/codex/root-w07-ff-perf-reception` | `64b4d294a1e61e595e330b4a7d4075c289f9fdc3` | 112 / 0 | 已吸收（祖先） |
| `refs/heads/codex/root-w20-ff-final-20261029` | `5ec54e02b8db69d0f38adfd0d7cee58f04f3a2b8` | 18 / 0 | 已吸收（祖先） |
| `refs/heads/codex/transcript-companion` | `29085f76ed60b9fc756b613c870288670566f720` | 176 / 1 | 旧原型被正式实现替代 |
| `refs/heads/codex/w06-ff-contract-matrix` | `c5527f1a9b2123e3f1796b5eb4dd35e0a81e13f5` | 119 / 0 | 已吸收（祖先） |
| `refs/heads/codex/w07-ff-matrix-efficiency` | `8c7adedde373862968037b0d97857291452749e5` | 115 / 0 | 已吸收（祖先） |
| `refs/heads/codex/w19-root-integration-20261026` | `f7aa0bab5fd110397ce31bfc7c7c069013cfa51d` | 52 / 0 | 已吸收（祖先） |
| `refs/heads/codex/w19-sina-statements-20261025` | `d396fe73df27768468d6ea84835562820b4ae952` | 54 / 0 | 已吸收（祖先） |
| `refs/heads/codex/w20-ff-replay-20261028` | `2b610881b9da509d6fb3f3bcbeb5b32707e051f2` | 19 / 0 | 已吸收（祖先） |
| `refs/heads/d4-05-ff-process-diagnostics` | `bf7e1dab4aebcfe671554a4fda59705eb7fe1765` | 4 / 0 | 已吸收（祖先） |
| `refs/heads/fcap` | `d4d2fac4c690bfb8b1368d2ca140fd75150fd288` | 155 / 0 | 已吸收（祖先） |
| `refs/heads/main` | `f65e6ca75fbce0616e65870f0aea78b793ef883c` | 0 / 0 | 当前目标/同点 |
| `refs/heads/phase-15-lock-retry` | `a9bf70b0e3910d36dd7fc782a42ae074ef984a78` | 266 / 0 | 已吸收（祖先） |
| `refs/heads/phase-19-ambiguous-candidates` | `fd95d30e7ee066f039bf6166ed77163eb991ca5d` | 264 / 0 | 已吸收（祖先） |
| `refs/remotes/origin/HEAD` | `f65e6ca75fbce0616e65870f0aea78b793ef883c` | 0 / 0 | 当前目标/同点 |
| `refs/remotes/origin/codex/company-pool-failure-consumer-20261009` | `e9b0d0882f46772e333a5b986c7c414733c284cd` | 139 / 0 | 已吸收（祖先） |
| `refs/remotes/origin/codex/dashboard-ff-job-release-20261109` | `7d8392eb98c50a6d6d27d06d9d7fabee913fe484` | 2 / 0 | 已吸收（祖先） |
| `refs/remotes/origin/codex/dashboard-p2-ff-market-20261109` | `f65e6ca75fbce0616e65870f0aea78b793ef883c` | 0 / 0 | 当前目标/同点 |
| `refs/remotes/origin/codex/ff-s3-single-request-limits` | `5b9a8c19640190202a6ba62ba823c36e6e766f7e` | 160 / 0 | 已吸收（祖先） |
| `refs/remotes/origin/codex/m3-acquisition-usage-20261010` | `f0f4e36319d6b3afc17e896f12a2aa1b183894b0` | 124 / 0 | 已吸收（祖先） |
| `refs/remotes/origin/codex/p5-ff-runtime-cleanup` | `ab9ce33b88d2e2ed914b95ac864fba80d8363c0a` | 151 / 0 | 已吸收（祖先） |
| `refs/remotes/origin/codex/w07-ff-matrix-efficiency` | `8c7adedde373862968037b0d97857291452749e5` | 115 / 0 | 已吸收（祖先） |
| `refs/remotes/origin/codex/w19-sina-statements-20261025` | `d396fe73df27768468d6ea84835562820b4ae952` | 54 / 0 | 已吸收（祖先） |
| `refs/remotes/origin/codex/w20-ff-replay-20261028` | `2b610881b9da509d6fb3f3bcbeb5b32707e051f2` | 19 / 0 | 已吸收（祖先） |
| `refs/remotes/origin/main` | `f65e6ca75fbce0616e65870f0aea78b793ef883c` | 0 / 0 | 当前目标/同点 |

### ET 全部 refs

| ref | HEAD | 目标独有 / ref 独有 | 判定 |
|---|---|---:|---|
| `refs/heads/codex/du10-et-txt-fidelity` | `cb8e29cddb3836fe670d93d65a02678f5ce8e466` | 3 / 0 | 已吸收（祖先） |
| `refs/heads/codex/du7-et-extraction-20261016` | `511fe4968e3be86dd3c548b231a7a19a57020582` | 22 / 0 | 已吸收（祖先） |
| `refs/heads/codex/du9-legacy-comparison-20261016` | `6d94c38df1f0edaae34cfed199ae8407287b0681` | 9 / 0 | 已吸收（祖先） |
| `refs/heads/codex/et-s3-bounded-runtime` | `53e1e60633e6e1fa225f308c2d0be84dea4cfeaa` | 39 / 0 | 已吸收（祖先） |
| `refs/heads/codex/et-s3-deadline` | `63c4090083cd34ece2ebb23affab81a419bc79dc` | 36 / 0 | 已吸收（祖先） |
| `refs/heads/codex/fresh-transcript-launch-20261009` | `c91f5f54bc2a24e7b5d6e648dba3f9d578f5fa52` | 28 / 0 | 已吸收（祖先） |
| `refs/heads/codex/main-permission-residue-20261009` | `8c23ef66f5f4e3f0ffda8c049b6899c623b46e48` | 31 / 0 | 已吸收（祖先） |
| `refs/heads/codex/n5-et-local-text` | `2b9fb84660f98ce27a05709a7e31342ab044b4d2` | 34 / 0 | 已吸收（祖先） |
| `refs/heads/codex/pool-et-response-budget-20261009` | `f4f2eca0e27ab877b9ab2012a28c70468eb3a364` | 32 / 0 | 已吸收（祖先） |
| `refs/heads/codex/root-du10-et-20261017` | `2584b7eed062a9a30254bc06b4f19ab5471b414e` | 1 / 0 | 已吸收（祖先） |
| `refs/heads/codex/root-du7-et-20261016` | `0cb71731cef6c6b3582f595d44f5b8a077392ac1` | 21 / 0 | 已吸收（祖先） |
| `refs/heads/codex/root-du9-et-20261017` | `7d06777e250ee3f7ae58f0be2cee62944bd2c104` | 7 / 0 | 已吸收（祖先） |
| `refs/heads/codex/root-w06-et-cutoff-20261011` | `d0ac42c60dcca992db78860b8469cfed3dd527e5` | 27 / 0 | 已吸收（祖先） |
| `refs/heads/codex/transcript-companion-adapter` | `4924d57044ae061d5fec3ccd4f1b7e74633f013a` | 41 / 0 | 已吸收（祖先） |
| `refs/heads/main` | `003c1c065109d0b02c7bd4de09ad3e8461a99c0e` | 0 / 0 | 当前目标/同点 |
| `refs/remotes/origin/HEAD` | `003c1c065109d0b02c7bd4de09ad3e8461a99c0e` | 0 / 0 | 当前目标/同点 |
| `refs/remotes/origin/codex/et-s3-bounded-runtime` | `53e1e60633e6e1fa225f308c2d0be84dea4cfeaa` | 39 / 0 | 已吸收（祖先） |
| `refs/remotes/origin/codex/et-s3-deadline` | `63c4090083cd34ece2ebb23affab81a419bc79dc` | 36 / 0 | 已吸收（祖先） |
| `refs/remotes/origin/main` | `003c1c065109d0b02c7bd4de09ad3e8461a99c0e` | 0 / 0 | 当前目标/同点 |

### SID 全部 refs

| ref | HEAD | 目标独有 / ref 独有 | 判定 |
|---|---|---:|---|
| `refs/heads/codex/cninfo-bounded-budget` | `8ed5fdde5e88c13470c120665ff3074a7f44a052` | 10 / 0 | 已吸收（祖先） |
| `refs/heads/codex/g4-main-sid` | `0cb3c1f0b4a5784757971265b2b20a7a0b4c5104` | 3 / 0 | 已吸收（祖先） |
| `refs/heads/codex/g4-sid-latest` | `201a8f059b658eb0b3c12cb7e4db2ef08e3907da` | 5 / 0 | 已吸收（祖先） |
| `refs/heads/codex/g5-sid-runtime` | `47e10593ec1c152f1e613cc1f14813267c9b396b` | 1 / 0 | 已吸收（祖先） |
| `refs/heads/v2-clean-rewrite` | `c0f07e12d4ba3e232d712bb6e5e491832023b0a0` | 0 / 0 | 当前目标/同点 |
| `refs/remotes/origin/v2-clean-rewrite` | `c0f07e12d4ba3e232d712bb6e5e491832023b0a0` | 0 / 0 | 当前目标/同点 |

## 7. 全部 worktree 清单

dirty / untracked 是初始化盘点路径数；clean不涵盖被ignore的运行缓存和原件，因此回收旧目录前不应把未检查的ignored下载资料一并强删。本文列出的目标是Git工区与已核实残留，不授权抹除真实原件。

| 仓库 | worktree绝对路径 | HEAD | 目标祖先 | dirty / untracked | 结论 |
|---|---|---|---|---:|---|
| FF | `C:/Users/郑曾波/Projects/filing-fetch` | `f65e6ca75fbc` | 是 | 0 / 304 | 当前主工区；按§4逐组处理 |
| FF | `C:/Users/郑曾波/.codex/worktrees/du11-ff-reception/filing-fetch` | `e8740748f919` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/filing-fetch` | `08ec85b27133` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/.codex/worktrees/m3-acquisition-usage-20261010/filing-fetch` | `f0f4e36319d6` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/AppData/Local/Temp/ff-fresh-transcript-launch-20261009` | `41ba0150c9c6` | 是 | 185 / 0 | 全部跟踪文件已缺失；清理旧 worktree 元数据，不提交删文件 |
| FF | `C:/Users/郑曾波/AppData/Local/Temp/ff-source-reader-v2-20260927` | `c47c397c4d93` | 是 | 93 / 0 | 全部跟踪文件已缺失；清理旧 worktree 元数据，不提交删文件 |
| FF | `C:/Users/郑曾波/AppData/Local/Temp/filing-fetch` | `89c8bdb2cfba` | 是 | 50 / 0 | 全部跟踪文件已缺失；清理旧 worktree 元数据，不提交删文件 |
| FF | `C:/Users/郑曾波/Projects/.fcap-review/fc-1003-fil` | `7745eb19409a` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/.fcap-review/fc-1101-fil` | `592fae610872` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/.fcap-review/fc-1204/base-filing` | `b7ef9cca0747` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/.fcap-review/fc-1204/layout/filing-fetch` | `93aa5ad11430` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/.fcap-review/fc-1204/r2/filing-fetch` | `83c638e76e40` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/.fcap-review/fc-1205/filing-fetch` | `83c638e76e40` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/.fcap-review/fc-130x/filing-fetch` | `83c638e76e40` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/ff-diagnostics` | `a1e97fa462f6` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/ff-permission-residue` | `55b7347a29b9` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/_harness_worktrees/dashboard-ff-job-20261109` | `154c292cb252` | 否 | 7 / 0 | 7项已吸收；按清单清理 |
| FF | `C:/Users/郑曾波/Projects/_harness_worktrees/dashboard-ff-job-release-20261109` | `7d8392eb98c5` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix` | `c5527f1a9b21` | 是 | 2 / 6 | 仅历史资料/产物未清；按§4处理 |
| FF | `C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root` | `2d380a054c65` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/_harness_worktrees/w07/ff-matrix-efficiency` | `8c7adedde373` | 是 | 0 / 1466 | 仅历史资料/产物未清；按§4处理 |
| FF | `C:/Users/郑曾波/Projects/cwp-lanes-20261005/ff-main-integration` | `211a56ff1b1f` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/cwp-lanes-20261005/ff-runtime-cleanup` | `ab9ce33b88d2` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/ffjf01` | `154c292cb252` | 否 | 0 / 0 | job接收版已吸收；历史handoff归档后移除 |
| FF | `C:/Users/郑曾波/Projects/filing-fetch-du10-41-matrix` | `ff2ba400ad37` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/filing-fetch-du11-local-transcript-reuse` | `8a83e2786326` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/filing-fetch-du6-portable` | `ff08a8e04f2a` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/filing-fetch-du67-integration` | `e8a85585b4c6` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/filing-fetch-du8-integration` | `41f498827943` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/filing-fetch-du8-matrix` | `6f381199f146` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/filing-fetch-r1-boundary` | `df9a1d3edab4` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/filing-fetch-r1-local-observation` | `130fd6b67c22` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/filing-fetch-s3-limits` | `1d0c73c2a6ea` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/filing-fetch-source-ref-v2-20261004` | `e1eda607f553` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/filing-fetch-transcript-companion` | `29085f76ed60` | 否 | 0 / 0 | 原型废弃，可移除 |
| FF | `C:/Users/郑曾波/Projects/filing-fetch-w19-sina-statements` | `d396fe73df27` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/filing-fetch-w20-replay` | `2b610881b9da` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| FF | `C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b34-ff-candidate` | `9be5587e4faf` | 否 | 0 / 0 | 保留待接收 B34 |
| ET | `C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts` | `003c1c065109` | 是 | 0 / 4 | 当前主工区；按§4逐组处理 |
| ET | `C:/Users/郑曾波/AppData/Local/Temp/et-fresh-transcript-launch-20261009` | `c91f5f54bc2a` | 是 | 212 / 0 | 全部跟踪文件已缺失；清理旧 worktree 元数据，不提交删文件 |
| ET | `C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/et-permission-residue` | `8c23ef66f5f4` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| ET | `C:/Users/郑曾波/Projects/_harness_worktrees/pool-20261009/et-budget` | `f4f2eca0e27a` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| ET | `C:/Users/郑曾波/Projects/_harness_worktrees/w06/et-cutoff-root` | `d0ac42c60dcc` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| ET | `C:/Users/郑曾波/Projects/cwp-lanes-20261006/et-local-text` | `2b9fb84660f9` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| ET | `C:/Users/郑曾波/Projects/earnings-transcripts-du10-txt-fidelity` | `cb8e29cddb38` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| ET | `C:/Users/郑曾波/Projects/earnings-transcripts-du6-ff-readonly` | `d0ac42c60dcc` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| ET | `C:/Users/郑曾波/Projects/earnings-transcripts-du7-extraction` | `511fe4968e3b` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| ET | `C:/Users/郑曾波/Projects/earnings-transcripts-du7-integration` | `0cb71731cef6` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| ET | `C:/Users/郑曾波/Projects/earnings-transcripts-du9-legacy-comparison` | `6d94c38df1f0` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| ET | `C:/Users/郑曾波/Projects/earnings-transcripts-s3-deadline` | `63c4090083cd` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| ET | `C:/Users/郑曾波/Projects/earnings-transcripts-s3-runtime` | `53e1e60633e6` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| SID | `C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite` | `c0f07e12d4ba` | 是 | 11 / 3 | 当前主工区；按§4逐组处理 |
| SID | `C:/Users/郑曾波/Projects/_g4/SID-LATEST/StockInfoDLSimple` | `201a8f059b65` | 是 | 0 / 3 | 仅历史资料/产物未清；按§4处理 |
| SID | `C:/Users/郑曾波/Projects/_g5/sid` | `47e10593ec1c` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |
| SID | `C:/Users/郑曾波/Projects/StockInfoDLSimple/cwp-cninfo-bounded-budget` | `8ed5fdde5e88` | 是 | 0 / 0 | 祖先且无dirty/untracked；旧工区可回收 |

## 8. 复算命令（只读）

由ROOT按三仓目标代入；不会触碰索引或refs：

```powershell
git --no-optional-locks -C ABS_REPO for-each-ref --format="%(refname)|%(objectname)"
git --no-optional-locks -C ABS_REPO worktree list --porcelain
git --no-optional-locks -C ABS_REPO merge-base --is-ancestor REF TARGET
git --no-optional-locks -C ABS_REPO rev-list --left-right --count TARGET...REF
git --no-optional-locks -C ABS_REPO cherry -v TARGET REF
git --no-optional-locks -C ABS_WORKTREE status --porcelain=v1 --untracked-files=all
git --no-optional-locks -C ABS_REPO hash-object --path=RELATIVE_PATH -- ABS_WORKTREE_FILE
git --no-optional-locks -C ABS_REPO rev-parse COMMIT:RELATIVE_PATH
```

对于job，最后两条对照本文六个blob；protocol对照精确diff的两处语义。对于B34，对照当前main的明确null候选测试，而不是用整个旧分支的ahead数量决定。对于SID，不应用过往PWF中“保护WIP未变化”的证明替代“WIP正确并通过验收”的证明。

本文未声称任何本轮测试通过、任何分支已被本代理合并或任何文件已被本代理删除。ROOT最终after清单与受测接收记录覆盖本报告的操作建议。
