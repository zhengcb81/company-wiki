# P7-CWP-PROJECTION 交接

绝对路径：`C:/Users/郑曾波/Projects/_harness_worktrees/p7/cwp/.planning/p7-cwp-projection/HANDOFF.md`

## 1. 结果

**engineering_complete** —— 完成范围：source 侧投影构造、存储与回放兼容（确定性
projection identity、深冻结快照、persist 一致性校验、producer 版本分派与 span 记录）。
按施工卡 §5 明确不属本卡（仍待 MAIN）：opt-in 接线选择、AUTO A/B subject、generation、
publish/read/恢复、定点安装、真实公司研究。本卡不证明 AUTO 或真实预测完成。

## 2. base / branch / delivery HEAD / diff

- base：`f8956d299b52849a4beb06e4071816ec72ddc6a3`
- branch：`codex/p7-cwp-projection-identity`
- delivery HEAD：`1c11ef0b5a838655559e91fab9a7bf38f1533d89`（正常 hooks commit，未用 no-verify）
- 实际改动：
  - `src/company_wiki/source_catalog/official_json_projection.py`（唯一生产源改动，+195/-29 行）
  - `tests/unit/test_p7_official_projection_identity.py`（新，18+1 责任测试）
  - `tests/integration/test_p7_official_projection_compatibility.py`（新，8 测试）
  - `.planning/p7-cwp-projection/**`（task_plan/findings/progress 更新 + 4 个证据 attempt 目录）
- 无其他 owner 改动；git status 全部可解释。automation、source reader/CLI、structure/layout/import、
  config/raw/生产DB、旧 sealed、安装副本均未触碰。

## 3. 根因→RED→实现→结果

根因（卡 §1，独立复核确认）：投影构造枚举顺序进入身份、快照浅冻结、span producer 写死。

RED（真实失败保留）：
- `python -X utf8 -B -m pytest tests/unit/test_p7_official_projection_identity.py tests/integration/test_p7_official_projection_compatibility.py -q`
  exit 1（24 failed / 2 passed；2 通过为既有结构 1.0.0 pin）。日志 `evidence/m1_red_20261010/red_new_tests.log`。
- 基线：4 个既有 M3 测试文件 139 passed exit 0（`evidence/m1_baseline_20261010/baseline_m3_tests.log`）。

实现（共同模块，一处集中修复）：
1. `projection_version="1.0.2"` opt-in：可靠声明页号优先、母页 SHA tie-break 的 canonical 页序，
   同页集合任意输入顺序同 ID/payload/export；页内 record/字段真实顺序不重排；缺页/重复页/
   metadata 冲突/重叠 ID/record 冲突/非法 current 仍 partial 且诊断齐全，不猜缺页、不选冲突赢家。
2. `_FrozenDict/_FrozenList` + `__post_init__` 深冻结全部输入输出嵌套容器；to_dict() 返回普通
   独立 JSON dict/list（无 MappingProxy 泄漏）；persist 校验 payload/hash/ID 一致，失配
   `projection_payload_mismatch` 明确拒绝，不自动改 hash。
3. load/replay/export 从封存 `adapter.parser` 分派算法（`_PRODUCER_TO_VERSION`），不按当前默认猜；
   未知 producer → `unsupported_producer_version`，structure 1.0.0 → `unsupported_parser_version`；
   span `parser_version` 记录真实 producer 版本。
4. 1.0.1 默认逐字节不变：golden `df3f6502845450a90d28e82d1690e3bbd42dc326002ee19595917ca50fdbcee5`
   由复审以 `git show HEAD` 内存重放验证等于旧模块输出。

GREEN（集中）：
- 新两文件 26 passed（复审补 freeze 契约后 27），既有 4 个 M3 文件 139 passed → 合计 166 passed
  exit 0（`evidence/m3_final_20261010/green_all_post_review.log`）。未改任何既有测试/golden。
- 静态：ruff 0 问题、mypy 0 问题（`evidence/m3_final_20261010/static_*.log`）。
- 中途两个真实发现（不掩盖）：深冻结列表曾破坏既有 `diagnostics == []` 断言 → 冻结列表保留
  list 相等语义；`_ref_from_dict` 误拒冻结映射 → 放宽 Mapping（见 findings.md）。

E2E（`evidence/m3_e2e_20261010/`）：
- `python -X utf8 -B .planning/p7-cwp-projection/evidence/m3_e2e_20261010/e2e_projection_chain.py`
  exit 0（`e2e.log`，receipt `e2e_receipt.json`）：真实 import/2→新 builder→persist→
  catalog close/reopen→load→replay→export；official-paged-qa 与 official-flat-list 两 declared
  layout、多 issuer（alpha/beta）、两页全覆盖、三页全排列唯一身份（6 排列）；记录 raw bytes/SHA、
  projection ID/SHA、producer/span 版本、文件数/体积（raw 每页仅 1 份、派生 3 份、catalog 共
  447140 字节）。TEMP 初始 0 / 最终 0 文件，已恢复（43 个测试产物随 root 删除）。
- 独立只读 agent 复核三不变量 NO_BLOCKER（`evidence/m3_final_20261010/independent_review.md`）；
  两处 minor：FieldBinding 冻结不彻底（已修+契约测试）、`_FrozenDict._data` 私属性旁路
  （Python 通用，persist/replay 拒绝漂移，保留记录）。

## 4. 对外 API / 版本兼容

- 旧位置/函数/参数/返回 DTO 全保留：`build_source_projection`、`build_projection_from_refs`、
  `projection_from_dict`、`persist_projection`、`load_projection`、`replay_projection`、
  `build_projection_export`。
- 新增 keyword-only `projection_version="1.0.1"`（两个 builder），显式 `"1.0.2"` 为 canonical 新算法，
  默认不变；未知版本 `unsupported_projection_version`。
- SourceRef 2.0、source-projection-ref/1、source-projection-export/1 字段原义未改。
- producer 常量：`cwp_official_json/1.0.1`（原 `CWP_OFFICIAL_JSON_PARSER_ID` 保留）、
  新 `cwp_official_json/1.0.2`；结构 parser 仍 1.0.1、layout 仍 1.0.0，pointer/byte 范围不变。
- MAIN 最小接线：继续 1.0.1 默认 API 接线 AUTO；最终新 generation 显式传 `projection_version="1.0.2"`。
  MAIN 无需等本卡即可写 RED；接线选择/generation/publish 归 MAIN。

## 5. 保护 / 清理 / 费用

- TEMP：E2E 自有 `%TEMP%/p7-cwp-e2e-*`，初始 0/最终 0 文件，`temp_restored=true`；
  pytest 自有 tmp_path，不落仓。测试目录原状：`repo_status_before_e2e.txt` 与运行后
  git status 一致（STATUS_UNCHANGED）。
- 原件/config/生产DB/旧 sealed/邻仓 ownerWIP：零改动（diff 仅上列文件）。
- 新增文件：3 个源/测试文件（45.0KB+16.0KB+13.6KB）+ PWF 证据 4 个 attempt 目录（短名称独占创建，
  未覆盖旧 attempt；e2e 首跑日志保留为 `e2e_first.log`/`e2e_receipt_first.json`）。
- external provider/model 调用：0 / 0；新增费用 USD 0（harness 自身推理不计项目供应商）。
- 旧 1.0.1 sealed 投影未重签、未重排；旧 fixture 保留，未复制 86 页资料湖。

## 6. CI / 安装候选 / 未解决限制

- remote：`origin https://github.com/zhengcb81/company-wiki.git`，已推分支
  `codex/p7-cwp-projection-identity`（含 delivery HEAD）。
- CI：**not_triggered** —— 仓库 workflow 仅 `push: branches:[master]` 与 pull_request 触发，
  分支推送不触发 CI；exact HEAD `1c11ef0b…` 的 CI 由 MAIN 合入后验证，不伪报绿。
- 安装候选：**空**（本卡不改安装副本，无 runtime 安装候选）。
- 未解决限制：
  1. `_FrozenDict._data` 私属性可达（Python 不可变对象通用旁路，漂移对象会被 persist/replay 拒绝）。
  2. 1.0.1 路径保持历史行为：页序敏感（同一集合倒序产生不同 ID），属封存语义，不能修。
  3. MAIN 的 opt-in 选择、AUTO A/B subject、generation、publish/read/恢复、真实公司研究未做（非本卡范围）。
  4. exact HEAD CI 未在本分支触发，待 MAIN 合后验。
