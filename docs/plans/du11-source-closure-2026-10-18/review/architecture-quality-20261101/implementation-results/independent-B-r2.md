# 节点 B — R2 定点独立复审通过

2026-11-01。接续 [首轮FAIL](independent-B.md)，只复审 B-01/B-02 的根修及相同 owner 的 generation locator、真实锁竞争和硬崩溃恢复。没有重跑首轮44项、旧P5大E2E或公司模型链；没有改产品、主PWF、Git或生产资料。

**结论：首轮两项实质 P2 已闭合，节点 B 在本次工程范围内通过。** Q03/Q05–Q09/Q11/Q13/Q14 沿首轮已核范围；本次不将其扩大为全库性能、真实供应商摘要、公司收入经济验收或整个PWF完成。

## 根修核对

| 首轮问题/边界 | 当前实现与独立核对 |
|---|---|
| B-01 已知60被迟到0覆写 | `NarrativeRunStore._settle_storage_object` 对已有创建量取max，迟到0不能降账；未知pending保守上界不退款。实际旧交错保留为直接owner反例，修后保持60。 |
| 同 run 同对象存在两个可并行结算者 | `account_storage_write` 是唯一生产admit/write/settle入口，在现有OS file-mutex内覆盖短scope。raw方法内部化，当前生产调用没有绕过该入口。真实两线程用同对象验证第二个物理writer不能进入，首个挂起时60仍记账，后续另一60对象不能使用虚假释放额度。 |
| B-02 两次objects快照放大100上限 | `StorageSnapshot.run_file_bytes`是该次local-only不可变观察。CAS只从原总上限扣local字段，owner对象SUM与新对象比较在admission同一事务完成；删除原 `current_total - newer_objects` 双快照公式。原两个60/100的确定性真实CAS交错，修后第二个对象在创建前拒绝，账和实物均60。 |
| generation pointer同公式 | `_write_generation_owner`也只扣snapshot.run_file_bytes，并通过同一个account_storage_write；独立定点反例在取快照时插入另一60字节对象，locator按当前总额拒绝且没有落下pointer。没有仅修CAS而留下另一公式。 |
| 崩溃/恢复 | 独立执行真实子进程os._exit(23)，确认OS锁随进程死亡释放，pending60保留；原对象恢复后只有一份CAS，仍记60。没有等待人工解锁/签收或把未知空间清零。 |
| 并发与复杂度 | 只有每个AUTO DB一个一字节锁文件；模型HTTP、源解析和目录采样均在锁外。锁内是bounded对象/locator提交及AUTO短事务，不扩成整个文档/公司独占，不新增inflight表、授权字段或第二任务库。单个本地提交短暂串行是上述原子责任，模型工作仍可并发。 |

此处“硬界”指现有owner对象账与已观察的run私有文件占用；私有目录按既有5秒低频和提交前强制采样，共享SQLite/WAL仍是诊断而非伪精确run归属。没有把修复说成文件系统物理元数据也已逐字节计量，或任意外部写者均被原子纳入。

## 独立定点执行与版本

正常宿主 `C:/Miniconda/python.exe -B -X utf8`，`PYTHONPATH=src;tests`，禁自动pytest插件并显式加载pytest_asyncio，初始absent的短测试根 `tmp/qb-r2-review`。

只执行：

1. `test_late_cas_loser_cannot_erase_another_writer_actual_bytes`
2. `test_cas_admission_does_not_mix_two_owner_usage_snapshots`
3. `test_same_object_has_one_short_writer_scope_and_holds_pending_capacity`
4. `test_killed_writer_releases_os_mutex_without_refunding_pending_space`
5. `test_control_locator_uses_local_only_snapshot_for_atomic_admission`

实际结果 **5 PASS /3.62s**。这些覆盖首轮真实失败及相邻共因，不将作者28项或1个loopback参数累计为独立数量。

逐文件SHA只读核对当前 [Q04-Q06-seal.json](Q04-Q06-seal.json)，`revision=R2_after_independent_concurrency_findings`：**11/11实现及测试文件一致**。旧 [R1 seal](Q04-Q06-seal-r1.json)和首轮FAIL保留；不把现在通过倒签给原实现。作者R2完整public raw-v1 loopback44.78s属于作者证据，本复审没有再次运行或冒称独立实跑。

测试结束经绝对路径/父目录/唯一名称核对，仅删除本复审新建的qb-r2-review，已恢复absent。没有完整恢复备份演练或生产迁移；没有修改源文件、配置、原件、外来WIP、索引或主PWF。ROOT可按上述seal集成，后续有效代码若改变相关owner，应评估受影响范围而非机械重复全部测试。
