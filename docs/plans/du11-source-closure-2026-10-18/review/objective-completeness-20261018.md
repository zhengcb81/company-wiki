# DU11 目标完成度独立审查（2026-10-18）

- 审查范围：客户目标"按 PWF 推进 DU11 主线"的证据完整性；只读，不重做 C 内容审查。
- 当前工作区：master，HEAD e84806b0（docs(pwf): record the 4.0.8 regression and its revert），与 origin/master 同步。
- 审查方式：打开 PWF、review、b2 receipts、live C receipts、packages、usage ledger；只读运行 B2 测试收集/执行；未改源码/测试/配置，未 git 写，未调供应商。
- C 内容已知缺口按用户给定口径记录，不重新论证。

## 总判定

**目标未完成；不具备"除 C 内容外即可直接交接"的干净条件。**

- B2：**DONE_WITH_GAP**。代码、105 测试、三源回放、推送提交存在；但最终代码没有独立复审签收，且全量回放收据绑定的 product_reference 不是当前最终性能提交。
- C 工程侧：**DONE**。CN/US receipt PASS、1 POST、activation_recovery PASS、same/cross-run zero POST、FF 复用、RF 读取、native usage 证据齐全；HK 401 已记录。
- C 内容侧：**MISSING**（已知）。CN 最佳 8/10（critical 5/7），US 2–4/8，HK 未跑；正式三供应商原语言摘要未完成。
- 施工包：**DONE_WITH_GAP**。README、INTERFACES、四张 card 都在，card 级写集基本不相交；但 README 与 P2 card 对 docx/pptx parser 的写集自相矛盾。
- PWF/交接：**DONE_WITH_GAP**。task_plan/progress/findings 顶部已记录 4.0.8 回归与回退；handoff 仍称 B2"已完成并发布"，usage 数字与 c-coverage-decision 有过期/矛盾。
- 红线：**PASS（未发现违规证据）**。无 tracked 生产 config/DB/gold/原件/key 改动；无 pre-push 绕过；B2 未删测试/放宽断言；C 本地门禁是 parked，不是绕过。

## 1. B2（DONE_WITH_GAP）

### 1.1 已具备的证据

- 代码/测试：tests/unit/du11_source_closure 共 5 个测试文件；当前代码实测 **105 passed in 4.26s**（命令：python -m pytest tests/unit/du11_source_closure -q -p no:cacheprovider）。收集数为 105。
- 三源回放：
  - CN：docs/plans/du11-source-closure-2026-10-18/b2-v3-20261018/cn-h1.json：status ENGINEERING_PASS_CONTENT_OPEN，selected_required=10/10，selected_count=96，api_calls=0，original_unchanged=true，gold_unchanged=true。
  - HK：b2-real-sources-v3-20261018/hk-annual.json：7/7，0 API，original/gold unchanged。
  - US：b2-real-sources-v3-20261018/us-10k.json：8/8，0 API，original/gold unchanged。
  - replay.json：api_calls=0、raw_copies=0、source_unchanged=true，含 17 个 source_bindings。
- 推送：d55d3369、6a2ee853 都是 origin/master 的祖先（git merge-base --is-ancestor 通过）；当前 HEAD e84806b0、origin/master 同步。
- 审查报告：review/b2-antecedent-independent-review.md、-v2.md、-v3.md 三份都存在。

### 1.2 缺口

1. **最终代码没有被独立复审签收。**
   - v3 审查对象是 1a774af0，结论 **REJECT**（review/b2-antecedent-independent-review-v3.md:11，code_commit=1a774af0）。
   - d55d3369（11:23）和 6a2ee853（12:20）是在 v3 之后修的；没有 v4/最终复审报告。
   - handoff:14 却写 "B2 已完成并发布：d55d3369（三审修复）、6a2ee853（性能修复）"；这与"v3 仍 REJECT、无最终复审"不一致。
2. **三源回放不是最终性能提交的全量回放。**
   - replay.json 的 source_bindings 中 product_reference 绑定 e946b493…，当前 src/company_wiki/document_understanding/operating_states/product_reference.py 是 8e742d71…（我本地重算）。
   - 差异来自 6a2ee853（性能修复，改 product_reference.py 14 行）；该提交没有更新 b2-v3/b2-real-sources-v3 的全量收据。
   - docs/plans/.../b2-v3fast-20261018/page-scope.json 确实绑定当前 8e742d71，但它只是 diagnostic-only page scope，不是 CN/HK/US 三源全量回放。
3. **CI run 只有文字引用，没有本地 CI 收据。**
   - findings/progress/task_plan 写 CI 39123679375 success；review/ 下没有对应的 CI JSON/log。
   - 未联网，无法独立核验该 run 的 result；commits 的 pushed 祖先关系可核验，CI 结论不可核验。

### 1.3 结论

B2 工程成果和测试/回放证据大体存在，但"已完成并发布"的最终状态证据不足：**DONE_WITH_GAP**；不能把 105 测试或三源金标命中当作最终独立签收。

## 2. C 工程侧（DONE）

以当前最佳 CN/US 工程 run 为准：

| 项 | CN | US |
|---|---|---|
| run | live-cn-h1-b2v3w-20261018 | live-us-10k-b2v3b-20261018 |
| receipt | PASS | PASS |
| model_post_attempts | 1 | 1 |
| tokens / micro_usd | 15,970 / 2,968 | 10,829 / 5,353 |
| activation_recovery | PASS（same run，1→1 attempt，tokens 不变） | 同左 |
| same_run_zero_POST | true | true |
| cross_run_zero_POST | true | true |
| FF reuse | ff-reuse.stdout.json：reused_existing，downloads=0 | 同左 |
| RF read | rf-source.stdout.json：verified_read/read receipt | 同左 |
| protected/sentinel | true | true |

- native usage：两份 overall.json 的 states[0].native_usage 各有 1 条 native_model_charge，attempt/tokens/金额与 receipt 一致。
- HK：live-hk-annual-b2v3-20261018 receipt FAIL；native-failures 明确 http_status=401；未产生可用的摘要。
- **HK 计费口径需要修正**：task_plan.md:114 写 "HK 的 401 未计费"；实际 native usage 为 69,046 tokens / $0.031208，usage_status=unknown，cost_kind=budget_proxy_or_unknown_hold_not_invoice。它不是已结算发票，但**是未知 hold/预算占用**，不能说"未计费"。
- **母账不一致**：
  - .planning/shared-reading-production/live/usage.jsonl 当前 65 行，44 个唯一 attempt（21 个 attempt 有重复行）。
  - 按 attempt 去重：900,711 tokens / $0.238405；其中 known 41 个 / 692,409 tokens / $0.181256；unknown 3 个 / 208,302 tokens / $0.057149；4 个 error。
  - handoff:18 写 41 attempts / 857,961 tokens / $0.2311；handoff:61 另写 742,228 tokens / $0.421556；task_plan:114 写 20 unique attempts / 479,369 tokens / $0.135217。三组数字互相不一致，也不等于当前 ledger 去重值。
  - 结论：C 工程回执本身 DONE；**累计账/handoff 不一致是证据缺口**，需要以 ledger 重算并写 as-of 时间。

## 3. C 内容侧（MISSING，已知）

- CN 最佳：live-cn-h1-b2v3w-20261018，22 claims；review/c-content-review-20261018-cn-v3.md 判 required 8/10、critical 5/7。缺 f-five-year-target-is-plan、f-current-coverage-30（t13 两条）。
- US 最佳：live-us-10k-b2v3b-20261018，9 claims；review/c-content-review-20261018-v2.md 判 required 4/8、critical 4/8。缺 Azure consumption、M365 consumer/commercial、RPO scope、RPO forward；t28/t59 重复。
- HK：401 未跑，无摘要。
- 4.0.8 回归：live-cn-h1-b2v4e-20261018，14 claims，review/c-content-review-20261018-cn-v4.md 判 required 6/10、critical 4/7；已在 46ffee41 回退，当前 HEAD 记录在 e84806b0；best 仍是 4.0.6 的 8/10。
- 结论：正式三供应商原语言摘要 **MISSING**；产品决策（A/C/D）待定。该缺口已在 task_plan/progress/findings/handoff 记录，**但 c-coverage-decision 仍是旧版**（见下）。

## 4. 施工包（DONE_WITH_GAP）

- 文件齐全：docs/plans/parallel-packages-2026-10-18/README.md、INTERFACES.md、P1-OCR-TEXT/card.md、P2-OFFICE-TABLE/card.md、P3-IDENTITY-AUDIT/card.md、P4-CONSUMER-CONTRACT/card.md。
- 卡级写集：四卡各自的 docs 目录、测试目录、生产模块互不重叠；P1/P2 同在 document_normalization 但不同文件；P3 tools/identity_audit 与 P4 tests/integration/test_p4_contract 不重叠。依赖方向：P1/P2 独立；P3 依赖已发布读/导出接口；P4 依赖已发布 CLI + 冻结消费端观测。README 第 2.3 节写得清楚。
- **自相矛盾（必须修）**：
  - README.md:27-28 把 src/company_wiki/document_normalization/docx_parser.py、pptx_parser.py 列为 P2 的"写（仅增量）"。
  - P2-OFFICE-TABLE/card.md:22 明确"本卡不要求这两个文件任何改动"；:40 把它们列入禁写；:183 甚至要求 git diff --stat 中这两个文件出现次数为 0。
  - 结果是"P2 的规范写集"有两个版本；派发/验收无法按同一份写集执行。其余卡未发现同等级冲突。
- 结论：结构完整、card 级不相交，但 README/P2 card 需统一；**DONE_WITH_GAP**。

## 5. PWF / 交接（DONE_WITH_GAP）

### 5.1 已一致的部分

- task_plan.md、progress.md、findings.md 顶部都记录了 4.0.8 的 6/10 回归、46ffee41 revert、best 8/10、B 路径失败、下一步 A/C/D；三者一致。
- handoff:10 明确"整个计划没有完成"；:14-17 记录 B2、C 工程/C 内容、待拍板；没有把 C 内容写成通过。
- 105 测试、三源 10/7/8、C receipt/activation/cross-run 等核心事实可在 receipt/review 中复核。

### 5.2 矛盾 / 过期

1. **handoff:14 "B2 已完成并发布"**：与 v3 REJECT、无最终复审、全量回放未绑最终 6a2ee 冲突（见第 1 节）。
2. **handoff:18 与 :61 的累计账互相冲突**，也与 ledger 不一致（见第 2 节）。
3. **c-coverage-decision 过期**：
   - :54 仍建议"先做 B（任务合并）"；task_plan:15 已明确 B 路径实测失败并回退（4a983c98 → 12914f62），remaining A/C/D。
   - :6 仍写"上一轮 5 P1 全部关闭，只剩两条"；这是 4.0.6 的状态，未记录 4.0.8 的 6/10/4 P1 回归（虽然已回退）。
   - handoff:17 仍把 section 任务合并列为三条路径之一，会让接手者重复失败路径。
4. **handoff:35 旧 worktree HEAD 10699188** 与当前主线 e84806b0 不同；文中标为"当时 HEAD"，属于历史上下文，不是硬错误，但"当前基准"应写当前远端 HEAD/分支，避免接手者误用旧工区。
5. **HK "401 未计费"** 与 native hold 69,046/$0.031208 冲突（见第 2 节）。
6. **CI 39123679375** 无本地收据；handoff 仅文字（见第 1 节）。

### 5.3 能否让接手者直接继续

不能直接按 handoff 执行：B2 状态、C 方案、累计账三处会误导。需要先修文档；C 内容本身仍是已知未完成项。

## 6. 红线检查

**结论：PASS（未发现违规证据）。**

- 生产 config/DB/原件/gold/key：git status 的 tracked 文件干净；B2 replay 的 original_unchanged/gold_unchanged 为 true；C CN/US 的 protected_unchanged/sentinel_unchanged 为 true；FF raw_unchanged；未发现 key 值被读取/打印。
- pre-push：未发现 --no-verify / hook bypass；task_plan:151 记录的是本地两个非 CI 范围合同测试挡住、parked patch 未推、未绕 hook，和"绕过"相反。
- 测试：B2 三个提交只增加测试/修改 product_reference，没有删测试或放宽断言；当前 105 测试独立跑过。历史提交中的测试删除与 DU11/B2 无关，未作为本节点违规。
- C 临时库：native usage 的 database 在 C:/Users/.../cwp-temp/...，不在生产 catalog；C 的 temporary_lake_removed=true。
- 需注意但不构成红线：工作区有大量未跟踪 .planning/review/b2-review* 临时目录与 b2-v3fast 诊断收据；不应把它们当作已提交验收证据，也不应在交接时 clean/reset 掉用户数据。

## 7. 缺失/矛盾证据清单（可执行）

1. **B2 最终复审缺失**：review/b2-antecedent-independent-review-v3.md:11（REJECT，code_commit 1a774af0）vs handoff:14（d55d/6a2ee 已完成）。补一份绑定 d55d3369 或 6a2ee853 的最终独立 review，或明确把 B2 标为 DONE_WITH_GAP 而不是 done。
2. **B2 全量回放绑定过期**：b2-real-sources-v3-20261018/replay.json 的 product_reference sha256=e946b493… vs 当前 src/.../product_reference.py=8e742d71…。用当前 6a2ee 代码重跑 CN/HK/US 全量并更新 receipts，或明确 6a2ee 只改性能、不影响语义并提供等价测试证据。
3. **B2 CI 无本地 receipt**：handoff:14 的 39123679375 只在文字中；补 CI run JSON/log，或标为未独立核验。
4. **P2 写集冲突**：README.md:27-28（docx/pptx 写）vs P2 card.md:22、:40、:183（不写/禁写/0 次）。二选一，更新 README 或 card，并重新核对四卡写集。
5. **累计账三套数字**：handoff:18（41/857,961/$0.2311）、handoff:61（742,228/$0.421556）、task_plan:114（20/479,369/$0.135217）vs usage.jsonl 去重 44/900,711/$0.238405。以 ledger 重算，标注 as-of 与 known/unknown hold。
6. **HK 计费口径**：task_plan:114 "未计费" vs live-hk.../phaseC-090-05a921ea8e9f.native-failures.json 的 401 + 69,046/$0.031208 unknown hold。改为"未结算发票，但产生 unknown budget hold"。
7. **C 决策文档过期**：c-coverage-decision:54 仍推荐 B；task_plan:15 说 B 失败回退；handoff:17 仍列 B。更新 c-decision 或 handoff，只保留 A/C/D。
8. **C 状态未进 c-decision**：c-decision:6 的"只剩两条"是 4.0.6 状态；补一句 4.0.8 6/10 回归与 46ffee41 回退，避免接手者误读为最新一次内容测量。

## 8. 是否具备"除 C 内容外可交接"的条件

**不具备（as-is）。**

- C 内容缺口的记录是充分的（task_plan/progress/findings/handoff 都有），可以把 C 内容明确留给产品决策。
- 但"除 C 内容外"仍有三个会直接影响接手的缺口：
  1. B2 最终代码没有独立复审签收，且全量 replay 未绑定最终性能提交；
  2. 施工包 P2 写集 README/card 自相矛盾，派发时可能越界；
  3. handoff/c-decision/usage ledger 三处数字/路径过期或冲突，接手者可能重复失败路径或错记预算。
- 修完上述 1–8 项后，才具备"除 C 内容外可交接"；否则只能交接为 **DONE_WITH_GAP**，并明确 B2/账/文档仍未闭合。

## 9. 结论摘要

- 目标总状态：**NOT COMPLETE**。
- B2：DONE_WITH_GAP；C 工程：DONE；C 内容：MISSING（已知）；施工包：DONE_WITH_GAP；PWF/交接：DONE_WITH_GAP；红线：PASS。
- 最优可交付状态：B2 代码/105 测试/三源回放、C 工程回执、四卡结构都可交接；但必须先把 B2 最终复审+回放绑定、P2 写集、handoff/ledger 修到一致。
- 未修改源码/测试/配置；未 git 写；未调供应商；只新增本报告 pair。

## 附录：审查命令/证据

- git status -sb；git log；git merge-base --is-ancestor d55d3369 HEAD；... 6a2ee853 HEAD。
- python -m pytest tests/unit/du11_source_closure -q -p no:cacheprovider → 105 passed。
- 读取 b2-v3/b2-real-sources-v3 receipts；重算 source_bindings SHA。
- 读取 CN/US overall/receipt/native usage；读取 usage.jsonl 并按 attempt 去重。
- 读取 parallel-packages README/INTERFACES/四卡；读取 task_plan/progress/findings/handoff/c-coverage-decision。
- 未联网，未调用 GitHub API/供应商；CI run 仅文字核验。
