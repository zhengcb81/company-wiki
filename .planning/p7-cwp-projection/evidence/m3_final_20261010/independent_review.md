# 独立只读复核 — P7-CWP-PROJECTION 三不变量

复核方式：独立 agent（只读，未修改任何文件）审阅
`src/company_wiki/source_catalog/official_json_projection.py`、两个新责任测试文件，
并对照既有 M3 契约测试；用 `git show HEAD` 内存重放 M3 已验收版模块比对 1.0.1 身份。
复核运行时间 2026-10-10（工程日期）。结论：**NO_BLOCKER**。

## 不变量 1（顺序/canonical identity）：PASS

- `_canonical_page_key` 为 `(0, current, sha)` / `(1, 0, sha)` 全序；tie-break 落 parent SHA。
  2/3 页全排列、同页号双页排列均产生唯一 projection_id。
- 页内 record/字段保持真实观测顺序，两 producer 同一路径，无重排。
- partial 与诊断全部保留：缺页、重复页/页号、metadata 冲突、record 冲突（全不选中）、
  非法 current 均如实报告；无"猜完整/凑完整"路径。

## 不变量 2（深冻结/所有权）：PASS with issues

- `__post_init__` 深冻结 SourceProjection/ProjectionRecord 全部容器；to_dict() 返回全新
  普通 JSON 树；输入 dict、decode 入参、to_dict() 返回值的修改均不能改已发布 SHA；
  persist 先校验 payload/hash/ID 一致再封存。
- issue(minor，已修)：FieldBinding 无 `__post_init__`，手工构造时 list 型 range 可原地
  改写。已补冻结与契约测试 `test_field_binding_ranges_are_frozen_even_when_built_from_lists`。
- issue(minor，保留)：`_FrozenDict._data` 私属性可达，等价 frozen dataclass 的
  `object.__setattr__` 旁路；persist/replay 对漂移对象明确拒绝而非静默重发布。
- 附注(已修)：replay 结果/evidence span 中 dict 型 provider_record_id 曾未解冻，
  实践中 ID 为 int；已统一 `_unfreeze`。

## 不变量 3（旧回放）：PASS

- golden `df3f65…ee5` 非自证：以 `git show HEAD`（M3 已验收版）内存重建同一 fixture，
  旧模块 SHA = 新显式 1.0.1 = 新默认 = golden 常量，canonical_json/to_dict 逐字节相等。
- 1.0.1 保持调用方页序与原哈希输入；adapter parser 常量未变。
- replay/export 按封存 `adapter.parser` 分派算法；未知 producer→`unsupported_producer_version`，
  structure 1.0.0→`unsupported_parser_version`，load 拒绝未知 producer 文件。
- 回归：P7 两套 26/26（复审后 27）、M3 acceptance+projection 56/56、contract 26/26 全绿。
