# Holdout诊断与原生结果隔离根修

状态：工程冻结，等待ROOT安排独立审查与正常发布。未签真实公司C或总目标完成。修复前审计单独冻结，JSON SHA `a6843a45b5bf5a498ff0e9707c26efdbc618bcd0084d8d60c82e1a666d392bac`。

## 根因与接口

- Reuse existing run_bounded ownership, deadline, exit and tree cleanup; remove duplicate Popen/taskkill lifecycle.
- Explicit stdout_cap_bytes=None keeps complete native protocol. stderr_log_tail=True drains only diagnostics and returns true byte counts; defaults and explicit payload caps remain strict. Optional streaming stderr_observer sees chunks before trimming; its own failure is separate metadata, never native failure.
- Remove post-exit stdout2MiB/stderr allowance failure and max_log4096..1MiB hidden range. Explicit positive diagnostic retention controls only bounded display.
- Complete events facts append once without cumulative size admission; append/fsync/serialization failures are observation errors, emitted at exit on stderr, never replacing native outcome or unlocking resend.
- Controller preserves parsed native stage/paid snapshot even if optional receipt/log writes fail; marks observation_incomplete and stops further experiment stages, not native failure/PASS or new POST.
- Do not swallow genuine native nonzero/failure, actual timeout/owned descendant cleanup, changed model input, second POST, explicit after-paid IO_TRANSIENT, missing durable pin or activation fault.

唯一进程owner仍是 `_bounded_process.run_bounded`，无新增Job/后台任务/许可链。新增的显式完整stdout模式由holdout选择；其他消费者默认cap、单deadline和失败传播保留。`max_log_bytes`是正整数的显式诊断保留量，原4096..1MiB任意范围取消。

观察不完整有独立status与原生stage/paid snapshot；不得伪PASS、退款或重发。故障注入仍是真实本地IO_TRANSIENT/RETRYABLE，未知费用和post-once不放开。

## TDD与快速验证

Original nine 7F2P ->9P; one related22P pass; later delta5P (3 genuinely new +2 affected), diagnostic policy2F->2P and marker/observer2F->5P with affected real large protocol/default strict caps. Final new file20 unique cases plus9 existing controls, not presented as one unrun all-29 pass.

- `red`：{'tests': '9', 'failures': '7', 'errors': '0', 'time': '6.073'}
- `green`：{'tests': '9', 'failures': '0', 'errors': '0', 'time': '5.514'}
- `final`：{'tests': '22', 'failures': '0', 'errors': '0', 'time': '8.484'}
- `delta`：{'tests': '5', 'failures': '0', 'errors': '0', 'time': '8.282'}
- `policy-red`：{'tests': '2', 'failures': '2', 'errors': '0', 'time': '6.040'}
- `policy-green`：{'tests': '2', 'failures': '0', 'errors': '0', 'time': '4.653'}
- `tail-red`：{'tests': '2', 'failures': '2', 'errors': '0', 'time': '5.783'}
- `tail-green`：{'tests': '5', 'failures': '0', 'errors': '0', 'time': '5.261'}

Ruff四文件绿；唯一进程owner mypy绿。未重复全仓、690组、真实原件或付费模型。逐次原日志/JUnit、AST实际消费者清单在同名JSON。

## 最终冻结

- `src/company_wiki/_bounded_process.py` SHA256 `0fe1ec07503055932ba9f6b05fa4143b56aaf8ce9861fac914bd581873f241f4`
- `tools/document_understanding_benchmark/holdout_acceptance.py` SHA256 `d5f74bf9bf42f3d2a2690e63ba8526b0090b16f2bc44c58cb216e01412567dfa`
- `tools/document_understanding_benchmark/holdout_acceptance_observer.py` SHA256 `98c1070c8ebacd456d577d24f2470672973602941f48ffd14671d9dfd22f3fc7`
- `tests/unit/test_holdout_observation_isolation.py` SHA256 `a24103a2c4a4f13d1b6ecfad1a457cd4d11b673f6412a444c9886eef7e8876b3`

## 未冒称完成

- No real H1/source reparse, no models/paid/network/download/original reads, no new actual summary/cache/RF adoption acceptance.
- holdout fixture remains selected projection/4/model-request/5; this run does not establish new projection/5/model-request/6 real C.
- phaseC mtime-only preparation and frozen_before_candidate_output recommendations are in immutable audit for ROOT disposition, not changed here.
- No Git/index/hooks/CI/main-PWF/global installation changes; ROOT organizes independent review and normal publication.

## 清理

自有 `tmp/gf7` 初态不存在；上述证据先保存至报告，再按绝对containment与非reparse条件删除整段自有测试目录。最终收据仅更新本报告；不动pytest历史/他人工区/原件/模型。

最终清理收据：已核绝对父目录与全部非reparse，删除自有 119 文件／148015 bytes；tmp/gf7 已恢复初始不存在。原件、生产配置、其他pytest历史与工区未动。
