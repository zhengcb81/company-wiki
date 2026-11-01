# 节点 B 独立审查 — 首轮不通过

2026-11-01。审查范围为当前未提交 Q03/Q04/Q05/Q06/Q07/Q08/Q13/Q14、Q11 处置及后来加入的 StockWiki Q09 窄传输变更。只读检查产品，运行隔离小反例；没有修改源码、主 PWF、索引、生产配置/资料/数据库，没有模型、采集或完整测试。

**结论：Q04 有两个独立复现的 P2 并发缺口，B 首轮暂不通过。** 已给 ROOT 与作者精确复现并开始返修；以下失败记录对应作者 READY 后、并发返修前的实现，后续修复不能把本报告覆写为原本通过。其他所审项未发现新的具体 P1/P2，限定工程范围可进入 ROOT 集成；不代替新摘要、整家公司或全项目验收。

## B-01 / P2 — 同对象竞争结算可以把实际已记字节降为零

位置：`automation/narrative_run_store.py::settle_storage_object`（观察时643–666行，关键656行）。实现使用调用者的 `new_allocation`：为 True 时直接将 `created_bytes` 覆盖到账，不管另一并发写者是否已经完成了同一 run/object 的结算。

真实临时 AUTO 库反例（只用60字节空间账，不读生产）：

```python
a = store.admit_storage_object(run_id='run-a', store_id='pure',
    object_key='same', byte_size=60, max_bytes=100)  # True
b = store.admit_storage_object(run_id='run-a', store_id='pure',
    object_key='same', byte_size=60, max_bytes=100)  # False
store.settle_storage_object(run_id='run-a', store_id='pure',
    object_key='same', created_bytes=60, new_allocation=b)
# storage_bytes == 60
store.settle_storage_object(run_id='run-a', store_id='pure',
    object_key='same', created_bytes=0, new_allocation=a)
# storage_bytes == 0  (actual observed)
```

对应合法时序：A先预留后暂停，B看见同一预留、先赢 CAS 并记录60；A再创建时 FileExists，作为竞争输家返回0，却仍带最初 new=True，因而抹去 B 已记录的真实新增。这不是重复收费问题，而是同 run 空间账失真，后续可继续写穿原硬界。

根修要求：结算应在同一 owner 事务中保持已确认字节的单调性；最初预留布尔不是独占结算权。覆盖同 run 两写者反向结算、正常跨 run 复用0、首次真实竞争输家0、崩溃 pending 保守界和重复恢复。不要新增人工签收或第二任务状态机。

## B-02 / P2 — 两次不同快照组合会放大原子 admission 的额度

位置：`automation/narrative_batch.py::_BudgetedObjects.put.before_create`（观察时1386–1390），以及 `_write_generation_owner`（2145–2151）有相同公式。

当前逻辑先读取 `current = guard.snapshot()`，再独立读取 `objects = accounting.storage_bytes(run)`，计算 `max_bytes = max_limit - current.persistent_added_bytes + objects`。如果两次读取之间对象账增长，第二次较新的 objects 被加回，而 current 中只减掉旧 objects。即使 admission 内部 SUM/INSERT 原子，传入的总额度已经被放大。

**已用两个真实60字节 CAS 对象和100字节上限复现：**

1. 用真实 `_run_guard(...limit=100)`、真实 `_BudgetedObjects`。
2. 包装 snapshot；A 的 `before_create` 那次 snapshot 先得到0，但返回前临时恢复原 snapshot，用相同 guard 完成 B 的60字节真实 put。
3. 返回 A 的旧 snapshot；A 随后读 objects=60，给 admission 的 max_bytes 变为160。
4. A 的60字节 put成功。观察 `storage_bytes=120`，两个 CAS 文件实际合计120，超过100，未报错。

这是对并发交错的确定性调度，无多线程 timing 假设，保留了真实 owner/文件提交。只创建两个小对象，没有大文件/性能推断。

根修要求：把不包含对象账的稳定本地文件占用传给 admission，并在 admission 同一事务内计算该 run 对象总额。不能在外面拿两个快照相减相加；generation pointer 同公式一起修。还要保留未知空间、旧 baseline floor 与真正的空间硬界，不以删除检查换绿。

## 其他责任的核对结果

| 责任 | 本轮结论及边界 |
|---|---|
| Q03 候选投影 | 当前 tokens 为目录/legacy/verified assertion/source-fact 的候选超集；最终身份/期间/as-of仍原 owner 判断。原生 SQLite triggers 只标 dirty，不依赖 schema UDF；readonly含dirty/旧库SQL兼容，不迁移；writer同事务刷新。稳定 document_id 游标和 lookahead 区分20k EOF。15个新候选测试独立通过；没有把首次 writer backfill 或旧库兼容扫描说成零成本。 |
| Q05 一次性 prune | 已查 S5 完成记录，旧 DELETE 实现确实删除；API无I/O退休结果，CLI在配置/selection读取前退出。保留inventory/vacuum，不是补一个可伪造许可文件。 |
| Q06 CAS 现存/竞争读 | 两分支都共享 `read(expected_size+1)`；独立运行2个小损坏对象负例通过。无界 read_bytes 已移除，atomic create-if-absent、不覆盖损坏对象保持。Q04结算缺口不等于这里的磁盘验证失败。 |
| Q07 旧 CLI | 固定物理路径、默认真实公司、复制和原地清理实现已删除，退役壳不依赖 sitecustomize。 |
| Q08 架构检查 | AST识别当前 imports、相对/qualified/别名/包入口/常量动态调用；注释不误报，owner豁免精确路径。不是全Python运行时依赖证明，也不能凭四个历史root tokens证明所有企业特判不存在；报告已明确范围。轻量unit真正执行，不搬回全部历史门禁。 |
| Q13 错误分类 | digest wire在catalog初始化前检查；invalid_request与配置/存储unavailable分开，失败无原文字节。必要pathless拒绝保留。 |
| Q14 rollout | 默认scan按root.adapter_id，不读旧snapshot；伪两轮门槛移除，旧解码在compat且符号alias兼容。日常activation/runtime-policy CLI退休，真实source/narrative事务未一并删除。 |
| Q11 保留SHA | 同意保留公开后端接收字节的SHA。本轮独立3个port用例通过，含正确ID/hash/长度但错bytes的替身；不能只比DTO字段。原文读、传输接收和跨时间重开是不同边界。为消除小额CPU重复新建trusted许可标志/具体实现绑定会增加复杂性。接受“处置为保留必要边界”的理由，**不写成所有重复CPU已优化**，也不据微基准推断全链性能。 |
| Q09 StockWiki | 仅3文件，复用已有run_bounded/ProcessTree，无跨仓私有import。实际 drain 以limit+1读并立刻abort、共用deadline/cleanup；stdout原配置，stderr单receipt 256KiB；wire/hash仍校验。独立2个持续超量＋孙进程marker反例通过5.12s。仅少量测试加入既有SHORT_TESTS，无全仓E2E常驻。未改四个foreign quickscan文件；整仓研究语义不在本次验收范围。 |

## 独立执行

使用正常宿主 `C:/Miniconda/python.exe -B -X utf8`，禁自动pytest插件，CWP显式加载pytest_asyncio；两个仓分别保持自身PYTHONPATH。

- `tests/unit/test_source_identity_candidate_projection.py tests/unit/test_maintenance_quality_remediation.py`：**37 PASS /27.94s**。
- `tests/unit/test_narrative_storage_ownership.py::test_cas_existing_object_validation_never_reads_beyond_input_bound tests/unit/test_source_contract_reader_port.py`：**5 PASS /2.38s**。
- StockWiki `tests/test_source_export_v2_bounded_transport.py`：**2 PASS /5.12s**。
- 合计44个不同定点用例，不与作者报告累加；它们通过不覆盖B-01/B-02，所以首轮结论仍FAIL。
- 两个新的纯 owner/CAS并发探针确认 B-01/B-02，结果分别60→0、100限额下实际120。

初始一次探针复用测试 helper 中的 sqlite context未显式close，临时库在cleanup时WinError32；这是本探针清理问题，不当成产品缺陷。进程退出后只清理经绝对路径核对的 `tmp/qb-review-00wpzzd7`；后续探针先collect释放连接，新的独占根自动恢复。额外读取中两次猜测非实际文件名失败，改为报告指定的准确路径，未作为任何缺陷证据。CodeGraph 混入历史`.planning`及缺caller，不用其无边推断dead。

三个测试根 `tmp/qb-core-review`、`qb-transport-review`、`qb-small-review` 初始absent，结束后仅删除这些自身根并核对恢复。没有完整恢复备份、扫描生产原件、关闭平台审查或改ACL。

## 下一步

只针对 B-01/B-02 的正确新RED与共用根修复查，随后再决定B验收；无需重跑全部44例、所有旧P5长E2E或公司收费链。此报告不修改主PWF，不抢ROOT集成权。
