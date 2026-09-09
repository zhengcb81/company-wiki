# 原 v1–v4 计划目录退役记录

日期：2026-09-03。用户明确要求：v5 新目录启用后，删除原 v1–v4 计划。

## 实际范围

仅移除：
`docs/plans/source-catalog-worker-recovery-2026-08-22/`。

保留：
- `docs/plans/source-catalog-worker-recovery-v5-2026-09-03/` 及其 baseline/history；
- `docs/worker-investigation-2026-08-20.md`；
- 项目源码、配置、数据库、主线计划和 worker 状态。

旧 v1/v2 的 revision 记录与 v3/v4 文件均在同一旧目录内，没有按名称模糊匹配其他计划目录。

## 删除前证据与独立预检

- 精确库存：54 个文件；53 份计划/审查文件与 v5 副本逐字节一致。
- 另 1 个 `__pycache__/plan_consistency_check.cpython-313.pyc` 为生成缓存，88831 bytes，
  SHA-256 `43400901a8c84470a3cb70ed220eb4382249d5b2a2eed4537cf39d1ba208f669`；
  明确列为 DERIVED_CACHE_RECYCLE_ONLY，未塞入已固定的导入 manifest。
- 库存文件：`old-plan-retirement-inventory.json`；其固定 SHA-256：
  `68a039b59dee1a8ad452c0214166f75b10254bb5194da705f4d4bd4642d3632b`。
- 独立 reviewer `/root/v4_test_dag_review` 最初因未备份缓存返回 BLOCK；
  明确缓存例外及回收站策略后，复核54/54 hash/size、53份副本、路径/无reparse、保留范围，
  返回 **SAFE_TO_RECYCLE**。该结论只授权已明确用户请求范围内的回收操作，不是正式v5计划PASS。
- 实际操作前再次核验精确绝对目标位于 workspace 内，且不包含 v5、报告或 workspace 根；
  逐目录拒绝 reparse/.git，逐文件重新核验库存和副本。

## 已执行结果

采用 Windows `SendToRecycleBin` API，只将完整旧目录移入回收站，没有永久擦除或兜底永久删除。
API成功；旧路径随后不存在；Windows回收站中确认找到同名目录，原位置匹配项目的 `docs/plans`。

旧目录共54文件可从Windows回收站恢复；53份文档另有v5内逐字节副本。缓存同样随目录进入回收站。

操作后：
- `verify_import.py`：54/54 PASS，且明确 IMPORT_ONLY；
- 原报告 SHA-256 仍为
  `8e6166ba063bc281ca1fa5da3c0743b895e4d93b6f2957de3cbd0b6938a95be6`；
- v5 import manifest SHA-256 仍为
  `da7d116e8c692d6311411c7390bec4278b59666a771823672f53e9b0f6567e4a`；
- Git显示旧目录38个已跟踪路径删除，新v5目录仍未跟踪；没有代用户stage或commit。
- 没有修改导入manifest或baseline；其中source字段仅作历史来源记录，不要求旧路径继续存在。

## 后续使用

当前仅在v5目录继续计划工作。正式v5版本合同、冻结和技术复审仍为待办，删除旧目录不表示这些
工作已通过，也不授权恢复worker。

如需恢复旧目录，可在Windows回收站选择 `source-catalog-worker-recovery-2026-08-22` 后还原；
不要把恢复操作误当作重新启用旧计划。未清空回收站。

