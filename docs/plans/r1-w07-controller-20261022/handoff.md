# W07交接：离线控制器

## 最新优先：独审修复候选 `5a1548e228bfdf231ca624767661ed138c962136`

W02对旧`8b00fd7f`得到7P/2RED：自定义HOLDOUT_AFTER_PAID虽传RETRYABLE，却被原生未知错误分类成TERMINAL_FAILURE。因此旧10P不能证明普通RETRYABLE恢复，该旧结论明确撤回；历史日志原样保留。

当前工具用已注册IO_TRANSIENT模拟**测试本地付费后I/O中断**，不是供应商故障。仅本进程注入的attempt/job/lease/fence marker可触发暂停；必须读到真正已提交的原生RETRYABLE/IO_TRANSIENT后才pause，controller另读取原生记录确认。新增known/UNKNOWN两例先2RED后2P/31.41s，含新lease/fence/PID、旧提交被原生拒且账不变、1POST无post_refused。生产registry/SQL/src无修改。原9例同SHA独立复核交W02进行，未在本作者交接里预签通过。

当前产品逐文件物理/Git LF SHA见`evidence/review-fix/current-fingerprints.json`；机器交接的product_commit已更新，旧宽测标为历史版本。下面为首轮历史交付记录。


- 产品commit：`8b00fd7f8d858ced08f9eb247a76428df977389f`，分支`codex/r1-holdout-controller`，基线`c3b4ebf1`。
- 唯一执行说明：[README.md](README.md)；机器接口和逐文件SHA：[handoff.json](handoff.json)。Windows工作字节与Git LF blob分别记录，不能混用SHA。
- 本线已完成：纯非native预检；真正configured CLI的一次POST、原生paid pin持久化、受控RETRYABLE后新lease真实paid replay、activation_pending恢复、跨run同artifact零计费缓存及公开读；未知费用不释放。正式run和paid operation保持，worker fence可以合法前进。
- RED：初始有效5F、预检合同3F/1P；两个失败native预检实验未改SQL/locator掩盖，最终改为复用现有公开builder的纯预检，无生产新恢复机制。
- GREEN：快速单元/原生反控9P/3.35s；显式integration10P/101.20s；最后加强服务器实际wire相等的两条断言后，受影响当前测试单跑1P/17.14s。实现仅再去一个EOF空行，纯字节映射留证。4工具mypy、6代码文件Ruff均PASS。
- 普通首次commit没有跳过hook，但稀疏检出遗漏了既有.githooks，实际未运行。已补齐本工区既有hook并对全部6个产品文件显式运行原pre_commit，Ruff/host guard PASS，其他规则按原触发范围skip。未改全局Git/hook/CI；交接doccommit继续正常hook。
- 目录恢复：每例owned root/fake原件通过fixture清理；最后清理本工区pytest库、mypy/test/python缓存，保留约0.24MB紧凑证据；没有删除真实原件/旧run或做完整恢复备份。详见evidence/cleanup.json。

## 非作者审查与剩余边界

状态为工程候选，ROOT安排非作者独立审查后接收。本线没有真实供应商调用、没有读真实key、没有真实下载、没有RF消费、没有push/并线/安装。公开read可用不能代签RF已使用。

ROOT需在writer退出后，保留现有scoped wiki/AUTO及MiMo UNKNOWN，重算公司与母预算，用现有配置先纯preview。实际bound超余量即报告，不减输出/不释放UNKNOWN。若可运行，分段停在after_paid并把真实native计量并入现有append_native/mother_totals，再以同attempt/run恢复、激活、cache。最后RF必须实际consume并绑定used参数和分部公式。本线没有第二账/第二任务库。

## 复核命令

快速单元及原生反控：

```text
python -m pytest tests/unit/test_holdout_acceptance_controller.py tests/unit/du11_paid_response/test_paid_response.py::test_paid_usage_survives_lease_loss_and_replay_uses_new_fence tests/unit/du11_paid_response/test_paid_response.py::test_crash_before_envelope_then_reopen_replays_same_paid_attempt tests/unit/du11_paid_response/test_paid_response.py::test_old_hash_without_complete_pin_is_not_replayable_or_free tests/unit/test_narrative_legacy_final_output.py::test_ordinary_single_paid_operation_recovers_then_activates_with_no_new_reservation -q --tb=short
```

显式大节点E2E（不放快速CI）：

```text
python -m pytest tests/integration/test_holdout_acceptance_controller_e2e.py -q -s --tb=short
```
