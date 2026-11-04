# D4-01～D4-06 收口记录 — 2026-11-04

## 结论

**D4 六项解耦缺口：COMPLETE / ACCEPTED。** 五个实现包各自交付后由 ROOT 接收；独立审查覆盖 D4-06 与 ROOT runner。审查发现的误报路径已修复并回归；最新审查结论 PASS。D4 的定义范围已闭合，不宣称真实摘要、缓存恢复、RF业务采用或固定公司审查循环完成。

## 组合验收

- 命令由 [机器状态](../../CURRENT_STATUS.json) `d4_closeout.test_command` 精确记录。
- 结果：27 passed / 0 skipped / 0 failed / 0 errors，46.623 秒；RF、FF、ET、StockWiki、AUDIT 五类consumer都有实际通过用例；AUDIT 两个指定 node id 都出现在JUnit。
- CWP `e7469d684b10a4cd37772e045eb3e588254c5ab8`；RF `96713029df63d384b9e97d2217dff4513e5d37e7`；FF `bf7e1dab4aebcfe671554a4fda59705eb7fe1765`；ET `003c1c065109d0b02c7bd4de09ad3e8461a99c0e`；StockWiki `23d84586dc2425961e953f5ab28aef867de6cb87`；AUDIT `2449df4a57636d3d8fb5beca2cfc5a8872835f4a`。六仓源码快照在运行前/后一致。
- `scratch_restored=true`；仅本地合成夹具、离线 fake provider 和 loopback；没有真实供应商调用/下载，也没修改生产原文、配置或DB。
- 固定 pytest 配置有一条非阻塞 `Unknown config option: asyncio_mode` 提示；27个测试均通过。
- CWP push hook 的 17 项 fixed smoke 通过（11.80秒），D4代码提交已推 `origin/master`。远端 GitHub exact-head CI #41919818618 与 Source system integration #41919818624 均成功，head 为 `e7469d68`。

原始机器报告、JUnit、stdout/stderr在 [`run-1/`](run-1/)；独立审查和交付边界见 [D4 root任务](../decoupling-recheck-20261102/harness_lanes/ROOT-D4-final-integration.md)。

## 六项交付/并线状态

| 卡 | 验收/发布状态 |
|---|---|
| D4-01 | StockWiki 本地主线 `23d84586`；无remote。 |
| D4-02 | RF main `96713029`；已与origin同步。 |
| D4-03 | CWP master已并入，随 `e7469d68` 推送。 |
| D4-04 | CWP master已并入，随 `e7469d68` 推送。 |
| D4-05 | FF main `bf7e1dab` 已推送。 |
| D4-06 | AUDIT两项producer/importer测试已迁入CWP ROOT；AUDIT本地删除commit `2449df4a`，无remote；AUDIT剩余portable测试42 passed。 |

## 独立审查反馈已修复

1. D4 test override/collect-only 假阳性：禁止用 `--tests` 覆盖强制清单，也禁止D4 collect-only。
2. consumer误报：路径规范化并限制在CWP ROOT；consumer报告以JUnit实际通过的测试文件为准，所选文件都须至少有一个passing case；D4各必需文件设置最低case数，并要求AUDIT两个明确node id。
3. 源码版本未绑定：版本指纹纳入Git根级Python模块，并检查运行前后相同。
4. ET私测fixture依赖：电话会集成测试在CWP自有临时目录提供fake provider，不再导入ET/tests；新增原件 `source_ref.content_sha256` 和 `source_id` 直接断言。

非阻塞边界：电话会集成仍通过ET内部worker注入缝替代provider session，证明实际ET处理/监督器和CWP入库/复用，不覆盖ET常规provider配置加载。此范围与D4合同一致，未把测试支撑扩大成外包改仓。

## 下一步

恢复 T4 source-note-parent + SEM-QUAL-01 来源语义根修：冻结通用正反例、沿 source owner 修父链与计划/条件限定语，然后单份真实H1定点复验和集中独审。接着做新版真实摘要、缓存中断/恢复、同摘要实际RF采用。RF/AUDIT业务计划改为 READY_NOT_STARTED；不自动开工。
