# 工具R3：model-input可选观察I/O根修

**作者冻结，待原独审agent增量复审。** 原R2与其NEEDS_FIXES记录不改、不倒签。

## 根因与修复

- Same observer owner observe_model_input is shared by generate and actual HTTP wrapper; no duplicated I/O permission branch.
- Read/write/atomic-publication OSError records observation incomplete and returns unknown; original native execution and usage are not replaced by an observer exception.
- Complete temporary staged snapshot (same model-input.json name) is atomically published; partial failed writes are never installed as a false known-mismatch baseline. Temporary data is cleaned, not another task/data store.
- Successfully read and genuinely different bytes still refuse. Actual post-once exclusive latch/fsync and native paid pin/unknown usage/fault classification are unchanged.
- Missing optional max_output_tokens in mismatch logging no longer throws KeyError instead of the true mismatch error.

## 验证

Only five new source-I/O/mismatch cases:4F1P -> with two original explicit fault/durable-pin controls7P. No repeat20/22/27/56 or actual model/native company run.

覆盖完整write失败、写了部分才失败、read失败，generate与HTTP都继续真实原owner seam且保持单POST拒重复；读成功的真实字节差异仍拒。Ruff两文件绿。完整RED/GREEN与最终11个SHA（仅2增量）在同名JSON。

## 冻结增量

- `tools/document_understanding_benchmark/holdout_acceptance_observer.py`：`acba5095186e5498c997a9f20aa5d96a530bebf8df0da13712fb38ce7e4e2ec0`
- `tests/unit/test_holdout_observation_isolation.py`：`09bc0ee249ad73f80b5f6d4f3a050a7c6757074e1ff8bb45e12f651a58f8f1f7`

## 边界

- All HTTP transport/native generate calls in these tests are explicit in-process synthetic seams; no paid call or company acceptance is claimed.
- Original R2 and independent NEEDS_FIXES reports preserved. ROOT assigns same-node independent incremental review of final11/delta2; no self-review or publication.
- No main PWF/Git/index/config/production originals/global install changes.

自有tmp/to7初始不存在，全部pytest输出/cache已定点放此，先保存证据再精确清理，收据后补本报告。

清理完成：自有40文件/23205 bytes，tmp/to7（含独立pytest缓存）已恢复初始不存在。
