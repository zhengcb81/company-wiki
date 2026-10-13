# DU2-FAMILIES 进度日志（append-only）

## Session 2026-10-13（本 session）

- 记录 base/status：分支 codex/du2-families-20261013，base_sha=5a297244549d54c34f382835b876ec3d181fcd24，
  `git status` clean，sparse checkout（17% tracked files）。目标路径 docs/plans/document-understanding-2026-10-13/review/deliverables/families/** 与 .planning/du2-families/** 均未被 .gitignore 忽略（git check-ignore 无命中）。
- 已读：本 checkout AGENTS、review/report.md、review/strategy_matrix.md、review/INTERFACES.md、
  原 design.md、原 INTERFACES.md、sample_manifest.json、review/README.md、inspect_samples.py。
- 20 份开发样本只读核对：全部存在且 SHA 与 manifest 一致。解析根注意：相对路径样本以主仓
  company-wiki 为根；hk-release/hk-us-release/hk-deck 位于 Temp\mFresh-me8cejn4（易失路径）。
- 建立 PWF 三件套（task_plan/findings/progress）。付费模型调用 0；网络调用 0（官方网页研究推迟到需要时）。
- Phase 1 complete；Phase 2（节点A）进行中。

### 测试与节点记录

- 节点A RED（2026-10-13，测试先行）：命令
  `python -B -X utf8 -m pytest docs/plans/document-understanding-2026-10-13/review/deliverables/families/tests -q`
  → **16 failed, 14 passed**。失败项均是数据包尚未补齐的真实缺口，不是测试自身错误：
  - test_index_coverage 全 4 项 FAIL：index.json 未写（覆盖清单缺失，正是"不能只列 profile 名"要防的形态）；
  - test_cross_market_counterexamples 全 6 项 FAIL：缺 hk_annual_report、prospectus 三态、offering 三态、
    lifecycle 修饰记录、行政负例记录；
  - test_cases 6 项 FAIL：初版 case 校验把连字符 case_id 当非法（测试口径过严，已修为
    CASE_ID_RE 允许连字符；这是测试自身缺陷，记为 3-Strike 第 1 次修正），其余 case 结构待整包后复验。
- RED 仅证明结构不变量检查有效；语义召回/含义判定不在此测试范围（NOT_RUN_ROOT_INTEGRATION）。

- 节点A 完成：cn_annual_report、sec_10k 两代表规格 + 6 个真实 case（中微公司年报×3、微软 10-K×3）+ 失败反例；
  index.json 覆盖清单 28 行（24 已实现 + 4 提案）逐形态独立状态。
- 节点B 完成：24 份规格 + 39 case 全量落地后
  `python -B -X utf8 -m pytest docs/plans/document-understanding-2026-10-13/review/deliverables/families/tests -q`
  → **85 passed**（exit 0，3.6s）。覆盖唯一ID/引用/枚举/非空理由/scope与生命周期（always_for_assertion 必绑 period）/
  同role别名合并不丢/每source≤8KiB 配额（实测远低）/跨市场反例显式差异（年报三市场、招股三市场、10-K/20-F/10-Q Part 不混）/
  生命周期正交（overlay 不复制章节策略）/行政不按文件名跳过。
- 测试修正 2 处（记录在 task_plan Errors）：case_id 连字符、公司名子串误报。

<a id="C-node"></a>
### C 节点原文对照（2026-10-13）

- 工具：`tests/c_node_quote_check.py`（非 pytest；只读原件；用未提交 bindings.local.json 定位）。
- 结果：**97 项检查 0 失败**（exit 0，16s）：31 个真实 case 的引文逐条回放原件页/行 + 空文本单元核对 + SHA 核对。
- 比对规则：PDF 按 physical_page 页文本、HTML 按去标签正文，剔除空白后相等（PDF 抽取在换行处插空格）。
- 应读/不读含义逐形态对照原文的结论写入 deliverables/families/README.md「C 节点核实结论」。
- 原件保护：20/20 样本构建后复核 SHA 与 sample_manifest 一致；无写入、无复制、无 scratch 残留。
- 两家公司验证：中微公司（A股年/半/季/招股）与名创优品（H股年/中/招股）上分别验证
  存量vs净增、计划≠承诺、测算≠实际、期后≠期内、问句≠事实；微软/腾讯/TAL/VRSK 佐证美股/港股形态。
- 资源：模型调用 0、付费 0、持久数据 357,012 字节、scratch 0。
