from pathlib import Path

root = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop-root")
p = root / "tests/test_pool_progress.py"
t = p.read_text(encoding="utf-8")
t = t.replace('obs("query_result", role="fetch", state="active")',
              'obs("query_result", run_id="run-1", execution_attempt="initial", role="fetch", state="active")')
t = t.replace('self.assertEqual(action3["action"], "dispatch_missing_reviewer")',
              'self.assertEqual(action3["action"], "reconcile_possible_charge")\n        self.assertFalse(action3["args"]["resend"])')
old = '''        state5 = chain(state3, obs("retest_done", refs=["run-3::E01"],
                                   evidence_ref="run-3/reports/retest-1/summary.md"))
        state5 = chain(state5, *[review_done("run-3", role, attempt="retest-1")
                                 for role in PP.REVIEW_ROLES])'''
new = '''        state5 = chain(state3, run_started(entity, "run-3", "retest-1"),
                       executor_sealed("run-3", "retest-1"))
        state5 = chain(state5, *[review_done("run-3", role, attempt="retest-1")
                                 for role in PP.REVIEW_ROLES],
                       expert_report("run-3", [], "retest-1"),
                       obs("retest_done", refs=["run-3::E01"],
                           evidence_ref="run-3/reports/retest-1/summary.md"))'''
assert old in t
p.write_bytes(t.replace(old, new).encode())
p = root / "tests/test_pool_progress_cli.py"
t = p.read_text(encoding="utf-8")
old = '        self.assertFalse(Path(str(self.state) + PP.LOCK_SUFFIX).exists())'
assert old in t
t = t.replace(old, '''        with self.module.StateLock(self.state, timeout=0.1):
            pass  # Kernel ownership released despite the persistent tiny file.''')
p.write_bytes(t.encode())

# Wiring is a small skill update; detailed protocol stays in one reference.
p = root / "skills/revenue-forecast-audit/SKILL.md"
t = p.read_text(encoding="utf-8")
heading = "## 一次完整运行\n"
insert = '''循环进度使用 `scripts/pool_progress.py` 的 `init/plan/apply/migrate-preview`，详见[进度与恢复契约](references/pool-progress-contract.md)。先保存选样再派工；状态只引用既有执行包和累计预算。恢复先读当前 run/attempt，补缺失角色；旧轮次或旧有效版本的报告不能计入本轮。该工具仅给原生 harness 下一步建议，不启动 agents、不证明质量或增加许可。\n\n'''
assert heading in t
p.write_bytes(t.replace(heading, insert + heading).encode())
p = root / "skills/revenue-forecast-audit/references/company-pool-loop.md"
t = p.read_text(encoding="utf-8")
heading = "## 2. 每轮实际执行\n"
insert = '''### 进度工具与恢复入口\n\n使用[进度契约](pool-progress-contract.md)中的 `pool_progress.py init` 创建新活动状态，再按真实观察调用 `apply`；`plan` 和 `migrate-preview` 必须使用新的输出路径，均不覆盖正式状态或旧报告。活动已有状态时读取并继续，不重复 init/随机抽样。角色的 `attempt` 是审查输出版本，`execution_attempt` 绑定实际执行；审查重试可换输出 attempt，仍引用原执行及其冻结有效版本。未知费用持续引用原账且保持 null，查询无结果不解锁新的付费派工；免费诊断可继续。最后一家公司也要 apply `advance_round` 记录收尾，池耗尽不等于质量通过。\n\n'''
assert heading in t
p.write_bytes(t.replace(heading, insert + heading).encode())
p = root / "skills/revenue-forecast-audit/references/pool-progress-contract.md"
t = p.read_text(encoding="utf-8")
t = t.replace('锁：`<state>.lock`（O_CREAT|O_EXCL，内容 pid+时间戳；默认 10s 等待、30s 过期接管）。崩溃遗留的锁可被过期接管；短时持有，不是许可或 lease。',
              '锁：`<state>.lock` 是可复用的小文件，由 Windows msvcrt/POSIX flock 内核互斥保护；默认最多等待10s，进程结束自动释放。文件年龄不决定所有权，活写者绝不被抢锁，释放不删除文件以避免分裂锁域。旧 `--lock-stale` 参数仅兼容，不再按年龄接管；这只是数据一致性。')
t = t.replace('四结论的 versions_digest 与当前有效版本一致；',
              '四结论绑定当前 run/执行 attempt，report_ref 非空且 expert 完成并有 refs；versions_digest 来自 run_started 的冻结版本，与当前有效版本一致；')
t = t.replace('原子写：staged 文件前缀', '输出创建：init/plan/migrate-preview 使用原子 create-if-absent，已有路径全部拒绝覆盖，不能让 preview 写穿 state/pool/旧报告；apply 才替换自己 state。\n- 原子写：staged 文件前缀')
t += '''\n## ROOT 接收后的因果与费用规则\n\nexecutor/expert 用 run_id + execution attempt；review 的 `attempt` 可是独立复审输出名，另用 `execution_attempt` 绑定对应执行。同名默认仅在 attempt 与当前执行相同时兼容；角色重试须显式 execution_attempt。query_result 必须携 run_id/execution_attempt，迟到观察只记诊断，不能清当前 writer 状态。新 run_started 冻结 versions_digest，收到旧报告时不贴当前版本；版本改变后建议重跑同公司。\n\nreport_ref 或复测 evidence_ref 缺失不会形成 clean/关闭义务；记录工具不自行实读这些引用或证明来源真伪，协调员仍须验证真实报告。cost_usd 为 null 的调用一直需要对账，包括 reconciled_unknown 或 known 但无数值；不把查询过当费用已知。已知金额必须有限、非负且不是 bool。抽样停止只证明记录中的范围，不等于整个 PWF 完成。\n'''
p.write_bytes(t.encode())
print("Updated invalid old assumptions, explicit role/execution binding and skill wiring")
