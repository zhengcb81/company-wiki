# revenue-forecast-audit · S1–S5 独立复审

运行目录为 `C:/Users/郑曾波/Projects/revenue-forecast-audit`，本地 `main@560ae51c8440a2c226e250df5ed62454d7e56cac`，无远端。`skills/`、`tools/`、`tests/` 与该提交一致，另有三份既有计划文档在途。F4 当前配置的 Audit `reconcile` 使用该检出的 `skills/revenue-forecast-audit/scripts/feedback_owner.py --runs-root <Audit runs>`。实测使用 Windows Python 3.13.9、独占临时运行和状态目录及本地合成子进程。模型请求、费用和生产写入均为 0。安装对齐沿用总控对四个逻辑入口各 52 份文件的独立核对。 [本机 F4 接线](C:/Users/郑曾波/Projects/company-wiki/.planning/shared-reading-production/feedback-host/settings.json:1064) · [S5 台账](../../../s5-verification-20261125.md)

| 项目 | 状态 | 验证范围 |
|---|---|---|
| S1 | 不适用 | 原八仓 S1 无 Audit 工作卡。S2 后用 `audit_run.py capture` 复验真实子进程退出 17 和脱敏错误尾段，机器 stdout 保持 JSON，原子进程只运行一次。仓内 `run_pool_progress_e2e.py:218` 的双 `DEVNULL` 属离线测试协调器，启动失败的诊断仍不足。 |
| S2 | 部分 | 正常 capture、强停、单角色失败的原 run、capture attempt 及 `role/capture_id` 可冷读和重投。已结束的失败保留脱敏诊断，缺终态保留不确定状态和未知费用。强停会丢捕获中的输出。正常 `init` 与 `status` 都退出 0，显式观察目录中 0 条观察，轮转日志未生成。全入口开始、主要步骤及终态覆盖仍不完整。 |
| S3 | 部分 | 财务量纲两入口共享 `financial_measure_core.py`，隔离 CLI 测试验证 evidence 不加载声明 CLI。真实 F4 将 `runs-root` 交给 Audit 公开端口获取结果。Audit 反馈层仍依赖执行 CLI 的事件结构和捕获产物命名，仓内审查证据亦有直接解析路径。 |
| S4 | 部分 | `AGENTS.md:10` 规定全 `unittest discover`。本轮实际收集并跑过 14 项反馈用例和 1 项量纲隔离用例。该提交无 `.github` 工作流和远端，日常自动执行未证。现有降级测试覆盖默认目录、备用 legacy 写入及双写失败，缺两个自定义目录都可写的反例，也未断言强停前输出可查。 |
| S5 | 部分 | S5-04a 默认目录和 legacy 备用目录已验，双可写目录仍能出现已投递却冷读 `unknown`。故障轮转与写不成时保留业务结果已验，全入口范围仍缺。S5-10 正式检出与 F4 运行位置一致，安装一致性由总控验证。 |

## 公开执行和冷读

用 `audit_run.py init --root <tmp> --run-id audit-fixture --company Synthetic --as-of 2026-11-25` 创建运行，再经 `capture --run <run> --role <role> -- <Python 子进程>` 启动本地夹具。正常 executor 退出 0，使用原身份得到 `action-started`、`capture-outcome` 和 `succeeded`。单独的 process 角色退出 17，使用原身份另得 `capture-execution` 和 `failed/child_exit_nonzero`，保存原 `TimeoutError` 文本，脱敏合成 Bearer 值。两个角色各只调用一次子进程，原记录都有起止时间。每个 capture 从清除写端传输变量的新进程运行 `get-capture` 两次及 `--runs-root … reconcile` 两次，响应各自字节一致。`observe-capture` 得到的行与原 ready 批次相同。两次 capture 的公开外层费用字段均为 `unknown`。 [执行写入](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/audit_run.py:878) · [观察投影](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/audit_feedback.py:51) · [公开查询](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/feedback_owner.py:329)

`python -B -X utf8 -m unittest discover -s tests -p test_feedback_ordinary_failures.py -v` 通过 14 项。损坏 SQLite 后重复 `init` 退出 1，stdout 为空，默认或可用 legacy 降级路径保存 `FileExistsError` 原回执。公开 `get-failure` 查回原因，新进程按原观察重复 `reconcile` 均返回 `done/failed/not_applicable`。阻塞回执写入时保留 journal 与 fallback 两个错误类型，0 个 ready 标记。轮转测试确认两个并发失败各一条，旧日志进入 `.log.1`，原退出及 stdout 一致。量纲隔离用例 `test_evidence_cli_runs_without_loading_declared_audit_entrypoint` 另通过 1 项。 [反馈测试](C:/Users/郑曾波/Projects/revenue-forecast-audit/tests/test_feedback_ordinary_failures.py:249) · [量纲测试](C:/Users/郑曾波/Projects/revenue-forecast-audit/tests/test_du8_measure_evidence_cli.py:371)

## 仍可复现的缺口

### P1 · journal 降级时观察和失败回执可能分离

在临时状态根将 `feedback.sqlite3` 写为损坏字节。将 `RESEARCH_FEEDBACK_DIR` 设为可写的非默认目录，同时设 `RESEARCH_FEEDBACK_OUT` 为另一个可写目录中的旧式 JSONL，重复 `init`。原命令退出 1，stdout 为空，stderr 报 `exported_without_journal`，旧式 JSONL 有 1 条失败观察。回执只写在自定义 `DIR/failures/<id>.json`。移除写端传输变量后，对同一观察调用 `feedback_owner.py --runs-root … reconcile` 得 `unknown`，显式传旧式 JSONL 父目录仍为 `unknown`，指定写端 `DIR` 才返回 `done`。三种查法各执行两次，响应字节分别一致。业务失败仍被正确报告，但只持有实际投递位置的冷读端无法查回原因。现场同时采用这两个写端配置的情况未核证。 [降级写和寻址](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/audit_delivery.py:74) · [降级投递](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/audit_delivery.py:205) · [冷读实现](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/audit_delivery.py:242)

根因是回执按第一个可写目录保存，而观察根据 `OUT` 投递。后续应让降级回执从实际投递位置可定位。验收使用上述两个可写目录、损坏 journal 及清除写端变量的冷进程，要求按公开观察和公开入口定位回执。重复读取保持同一身份，原退出 1 和 stdout 字节不变。沿用双写均失败时的无 ready 对照。 [发布触发点](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/audit_delivery.py:199)

### P1 · 包装器强停保留开始记录，丢失已经写入管道的诊断

单独启动 `capture --role fetch`，让子进程向 stderr 写 64 KiB 加唯一标记并 flush，然后写入独立的到达标志并等待。在到达标志出现后用 `Popen.kill()` 强停 capture 包装器，随后释放并等待夹具子进程退出。原角色 JSONL 有 1 条含启动时间的 `command_started`，F4 有 1 条同 run/attempt/step 的 `action-started`。原捕获目录中有 0 个产物。新进程两次 `get-capture` 均只回 `unconfirmed/unknown`，`observe-capture` 仍返回原开始行，`reconcile` 保持同一 `job_status=unconfirmed`。终态未观察到，保留该状态正确。停止前输出与已持久化的开始时间在 `get-capture` 中不可用。 [流读取](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/audit_run.py:523) · [结束后写盘](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/audit_run.py:1010) · [开始态冷读](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/feedback_owner.py:82)

根因是执行期间的流数据留在内存前缀或匿名临时文件，最终产物在 subprocess 等待后才生成。后续验收要求同一强停断点能读取原启动事件、时间和有界脱敏诊断，已存在冻结输入时继续提供其原引用。该路径保持未确认终态、未知费用及零重跑。另用正常 `init` 和 `status` 验证同一次操作的开始与终态可关联，并保持原机器输出。 [临时流](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/audit_capture_diagnostic.py:57) · [CLI 成功及失败分支](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/audit_run.py:1283)

### P2 · 仓内冷读依赖执行记录的表示

`feedback_owner` 导入同仓 `audit_run`，复用 `canonical_role_events`，自己按 `command_started`、`command_finished` 和 `roles/.../commands/<capture_id>/stderr*.txt[.gz]` 判断既有诊断。捕获文件布局变更若只改写端，终态仍可读而诊断引用会静默消失。公开执行层的 `review_evidence_reconcile.py` 还经 `review_evidence.load_events` 直接重解同一 JSONL，后者按自己的行数边界读取。边界收敛可让执行记录层返回窄的状态与诊断引用，保留既有公开 V1 入口和旧日志。以原正常、失败、强停和旧路径用例验收，再验证捕获产物布局变动由记录 owner 统一解释。 [反馈读端](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/feedback_owner.py:66) · [产物命名依赖](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/feedback_owner.py:102) · [证据重解](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/review_evidence.py:659)
