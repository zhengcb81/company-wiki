# Progress — DU2-FACETS

## Session 2026-10-13（du2-facets lane）

- 规格阅读：AGENTS 职责边界、review/report.md（R01–R10）、strategy_matrix.md、INTERFACES.md、
  sample_manifest.json、sample_observations.json.gz、root_implementation.md、evidence.json。
- 工作目录确认：_harness_worktrees/document-reading-review-20261013/facets，分支
  codex/du2-facets-20261013，base_sha=5a297244549d54c34f382835b876ec3d181fcd24，工作树干净。
- 真实锚点核实：cn-equity/cn-convertible/cn-ir/hk-annual/us-release/us-txt 原件均存在，
  SHA256 与 sample_manifest 一致；mtime 记录于 bindings.local.json（不提交）。
- C节点引文校验：tools/verify_real_quotes.py 逐条对照原文，20/20 命中（SHA 复算 + 页内/全文
  空白归一化逐字比对 + 读取前后 mtime 不变）。结果：c_verification/real_excerpt_checks.json。
- PWF 建立：.planning/du2-facets/{task_plan,findings,progress}.md。
- RED→GREEN：先写 tests/（308 failed / 3 passed 记录空包防线生效），补 14 records + 14 cases +
  index/coverage/acquisition/README 后 311 passed。

### 测试与命令记录

- RED（数据未写时）：`python -B -X utf8 -m pytest docs/plans/document-understanding-2026-10-13/review/deliverables/facets/tests -q`
  → exit 1，308 failed / 3 passed（结构不变量正确捕获缺失数据）。
- 中间修复（6 failed → 0）：HTML/TXT 载体无页/行时以 carrier 字段+exact_quote 锚定（INTERFACES
  允许 quote anchor 由 ROOT 解析）；mutation 维度枚举对齐卡面六轴（quantity→unit）；
  三个记录补 subject 归因槽位。
- A节点（两份语义规格/反例/合法空值）：`... pytest .../tests -q -k "required_context or semantic_counterexamples or legal_exits"`
  → exit 0，81 passed / 230 deselected，5.9s。结果 .planning/du2-facets/results/A_specs.txt。
- B节点（八面/四机制/正反配对集中数据与反例测试）：`... pytest .../tests -q`
  → exit 0，311 passed，7.0s。结果 results/B_offline_chain.txt。
- C节点（真实原文核对）：`python -B -X utf8 .../tools/verify_real_quotes.py`
  → exit 0，20 quote checks OK，1.0s。结果 results/C_real_quotes.txt。

### 资源与恢复

- 模型调用 0、付费 $0、网络 0（0 官方网页、0 原件写入、0 原件复制）。
- 持久数据 196,871 bytes（records/cases/c_verification/index/acquisition，≤512KiB 建议内）；
  tests+tools 51,926 bytes；本包 planning 16,474 bytes。
- 自有 scratch（_scratch_obs.json 74,620B、_scratch_checks.json）已 finally 删除，git status 干净；
  C 工具 scratch 目录 finally 清理，原件 mtime 未变。

### 合规审计轮（用户要求复查后执行）

- 逐项对照卡片与 INTERFACES §3/§4 复查，发现并修复 3 处差距：
  1. 五类语态（强事实/推测或测算/管理层指导目标/计划/假设性风险）原先散落提及→在两份A级
     语义规格中显式定义统一词表（required_context+confusion『展望/目标≠确定收入』）并加测试锁定；
  2. summary_focus 原为名词短语→14条记录全部改写为原语言业务问句（对齐§3『原语言业务问题』）并加测试；
  3. us-txt（行式TXT）锚点缺行号→补 line 126/128 真实行号，u2 引文改为可唯一定位句；HTML 保持
     quote-anchor 定位（偏差已在 handoff 记录）。
- 契约细节补正：§3『内容变动必须变化』→14条记录 version 1.0.0→1.1.0。
- 复验：全套件 326 passed（新增15项不变量：14问句+1语态词表）；C节点重跑 20/20 引文命中
  （含改过的 u2 引文），SHA 6/6、mtime 未变；A 82 passed、B 326 passed、C 20/20 均 exit 0。
- 复查确认无遗漏项：八个面五要素齐全（保存对象/证据形态/必须随带条件/常见误解/四态行为）；
  五个真实锚点风险全部落实到 case facts+mutations；引文预算全部 ≤8KiB（最大2,156B）；
  交付清单（README/index/records/cases/tests/coverage_matrix/acquisition_requests/handoff）齐。
- 一次性脚本 _audit_check.py/_bump_versions.py 用后删除（scratch 恢复）。

### 待办

- 已完成：handoff.json/handoff.md 写就并随实现 SHA（a58c4e09）提交；本lane停止。
