# investment-dashboard 独立复审

2026-11-25。实际 F4 检出为 `C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv`，分离的 HEAD 与本机远端跟踪引用 `origin/main` 均为 `b57672fd44f95f2fa105dc26c180afcf42a0ec09`，工作树干净。主工作区处于 `main@ead3425` 并有在途修改。现场 F4 为 Dashboard 配置了独立检出和 owner CLI。启动的真实服务进程及其前端构建产物版本本轮未取证。Windows CPython 3.13.9、pytest 9.1.1、Node 24.11.0。实测使用真实 ASGI 路由、合成端口、临时目录和新进程冷读，外部网络、供应商调用、费用和生产写入均为零。 [现场配置](</C:/Users/郑曾波/Projects/company-wiki/.planning/shared-reading-production/feedback-host/settings.json:1076>) · [S5 台账](</C:/Users/郑曾波/Projects/company-wiki/docs/plans/feedback-loop-2026-11-17/s5-verification-20261125.md:17>)

## S1–S5 判定

| 项 | 判定 | 已核范围与缺口 |
|---|---|---|
| S1 | **不适用**（独立卡） | 八张历史 S1 卡无 Dashboard。本仓历史 HTTP 异常及子进程黑洞在 S2/S5 修过。复跑长路径测试时，真实替身子进程退出 43，HTTP 保持 503，原生原因 `schedule_state_unavailable`、stderr 内容和脱敏结果可冷读。原件传输中断的原因链、非正常启动的证据仍按 S2 记缺口。 [S1 清单](</C:/Users/郑曾波/Projects/company-wiki/docs/plans/feedback-loop-2026-11-17/s1-p0-blackhole-plan.md:29>) · [长路径回归](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/tests/test_http_failure_feedback.py:16>) |
| S2 | **部分** | 预响应的 503、400、404 以及作业查询的第一条非缺席 cause 可按相关号冷查。轮转本地日志和观察投影都落盘，证据目录不可用时保留 HTTP 原结果，相关号为空，stderr 有类型告警。普通成功无该身份的开始、终态、步骤或版本日志。原件中途故障和启动前故障无法形成完整追踪，见下。 [HTTP 观察](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/backend/dashboard/transport/http.py:307>) · [诊断投递](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/backend/dashboard/request_feedback.py:317>) |
| S3 | **部分** | 10 个注册器消费具名的窄依赖，历史 41 处 `ops/*` 调用 service 私有方法已解除。RF scope 依赖只读窄接口，FF 两适配器共享回复映射。注册中心与跨 owner 查找仍有下述运行耦合。StockWiki identity 私有回退同属本仓同一 adapter 类，F2 样本引用测试替身只在工程脚本；两处均保留各自原有范围。 [注册接线](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/backend/dashboard/application/service.py:129>) · [FF 映射](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/backend/dashboard/adapters/m8_owner_jobs/ff_job_wire.py:10>) · [identity 回退](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/backend/dashboard/adapters/identity.py:155>) |
| S4 | **部分** | 提交树已有 `feedback-contracts.yml`，触发 main push、PR、手动。Ubuntu/Python 3.12 运行明确列出的 HTTP 和注册器测试，Node 24 运行 shared API 与原件预览测试。Windows 作业只收集三种长路径回归。工作流范围未覆盖传流中断的 HTTP 到 F4 相关号、启动失败和完整成功轨迹。注册器测试检查对象表面属性，未约束 `*args/**kwargs` 的调用形状。私有远端执行结果本轮未独立核证。该工作流与注册器测试在 f4dv 设为 sparse 路径，按同一提交的 Git 对象核对。 [工作流](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/.github/workflows/feedback-contracts.yml:9>) · [注册器用例](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/tests/integration/test_http_operation_capabilities.py:24>) |
| S5 | **部分** | `df39a22` 的可读诊断声明与 `b57672f` 的长路径、FF/RF 接口及作业 cause 修复均已进入实际 F4 检出。本次验证中三种 >260 字符路径（默认、独立观察目录、追加输出）均能用公开 CLI 冷读，引用仍为相对文件名。隔离 SQLite 指标快照可由新建 reader 读回。新复现显示预览修复覆盖响应头前的公开错误，已发送响应头后的中断仍丢 UI 关联。 [S5 本仓记录](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/.planning/unified-dashboard-2026-10-26/modules/m0-platform/s5-f4-diagnostics-20261125.md:11>) · [Windows 路径边界](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/backend/dashboard/storage/filesystem.py:9>) |

## HTTP、前端和冷读实测

同一次三分支复现，每个分支用独占目录。以公开源端口组装 `create_app({"source": fixture}, state)`，在 ASGI 2.4 的 `send` 上观察真正处理的 `GET /api/v1/document-versions/dv-fixture/original`。端口返回 `OriginalStream`，长度 9、ETag 为 `"fixture-v1"`，依次传 `%PDF-` 和 `okay`。每个分支端口调用一次。使用新 Python 进程运行 `python -B -m scripts.feedback_owner --sidecar-dir <临时观察根> get-diagnostic <相关号>` 和实际 company-wiki 的 `python -B -m tools.feedback_loop plan <该次 JSONL>`，另按 F4 正式绑定规则核对 `native_diagnostic_facts`。使用 Node 内存转译 f4dv 的 `api.ts` 和预览读取、错误格式化函数，按相同结果喂只读 fetch 替身，每个分支 fetch 一次。

| 场景 | ASGI 响应与前端 | 进程结束后的证据 |
|---|---|---|
| 正常成功 | 200，传齐 9 字节，ETag 正确，正常终帧及关闭各一次。前端消费到 9 字节 Blob。 | 无响应相关号，轮转日志 0 行，观察 0 项。公开响应中的 ETag 可证明当次响应内容，事后无法按 ID 找回。 |
| 正对照，发送响应头前失败 | 端口直接抛 `OwnerPortError("company-wiki", "source_unavailable", …)`。HTTP 503 的 JSON 自带相关号，预览显示 503、错误码、责任仓及同一号码。 | 1 条日志与 1 组观察。owner 冷读退出 0，读回同号、`openOriginal/<相关号>`、503、`company-wiki` 及原 typed code。F4 plan 退出 0 并接受同一身份的 `http_503`，原诊断绑定为 available，分诊投影保留 `OwnerException`。 |
| 新反例，已传第一个 chunk 后失败 | 在第二个 chunk 抛 `OwnerPortError("company-wiki", "source_version_unavailable", …)`。响应头已承诺 200，携带 Content-Length 9，实际发 5 字节后断流，未送正常终帧，流关闭一次。前端保留读取错误文本，缺少可抄录的相关号。 | 1 条日志与 1 组观察。需从目录先取得未知号码，再用 owner CLI 退出 0 冷查到 `request_failed`、记录状态 500、顶层 `dependency_owner=null`，异常链仍含原 owner/code。F4 plan 退出 0 并接受 `http_500`，绑定为 available，分诊投影为 `OwnerException`。 |

### DASH-01（P1）原件流中途失败可留档，用户无法用同号定位

JSON 错误响应在发送前取得 `observe()` 返回的相关号。流式响应先发送 200/206，外层捕获生成器的迟到失败后写 `request_failed` 并重抛，相关号无法再随错误 JSON 返回。共享 API 只从非 2xx JSON 取号，流读取阶段的异常走预览的普通错误路径。CWP 的真实原件 adapter 对最终长度、进程退出与最终收据做末尾检查，故障确实可能出现在 200/206 已承诺之后。应以同一流生命周期取号，向调用方暴露稳定的跟踪身份并保留既有“可查诊断”的语义。后续验收应在真实浏览器与公开 HTTP 的 200 和 206 中分别让替身流迟到失败，用 UI 的号码冷查 owner 与 F4，区分已发送状态和传输终态，保留上游 owner/code 和原流关闭次数。 [错误 JSON](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/backend/dashboard/transport/http.py:162>) · [ASGI 结束异常](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/backend/dashboard/transport/http.py:307>) · [CWP 最终收据](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/backend/dashboard/adapters/cwp_stream.py:241>) · [共享 API](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/apps/web/src/shared/api.ts:57>) · [预览读取与错误](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/apps/web/src/features/documents/OriginalPreview.tsx:15>)

### DASH-02（P1）进程启动和正常请求缺少可重建的运行轨迹

将合成文件作为公开启动命令 `python -B -m backend.dashboard.main --mode synthetic --data-dir <临时文件>` 的状态目录。进程只运行一次，在 bind 前退出 1，stdout 0 字节，stderr 为原 Python traceback 和 `FileExistsError`，原文件字节未变，未生成任何 owner 观察。应用组装发生于请求接受前，现有反馈上下文只包住 HTTP。普通 2xx 只有存在子进程失败信息时才记录恢复结果，`observe()` 采用单请求一次终态，详情字段没有时间、输入版本或服务版本，也无步骤开始。即使服务器访问日志显示 200，也无法和 owner 的版本与步骤按统一身份冷查。后续验收用启动失败、普通成功、部分成功和请求中强停，区分进程退出、业务阶段和 F4 分诊。成功路径应能按同一身份查到安全的输入引用、版本、步骤和完成状态，保持原业务次数。强停场景本轮未做进程实测。 [启动入口](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/backend/dashboard/main.py:57>) · [组装](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/backend/dashboard/composition.py:19>) · [实际详情字段](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/backend/dashboard/request_feedback.py:317>)

### DASH-03（P2）注册回调与多 owner 查找的运行耦合

`_bind_operation` 把具体调用抹成同一个 `invoke(*args, **kwargs)`，大部分方法通过字符串登记后由通用 `getattr` 调度。注册处传错参数、端口或方法名可延迟到命中该路线才发现。闭包仍捕获 service 的方法，当前测试只保证注册器拿不到它的常规属性。本次确认 RF scope 和 FF 作业回复映射已经缩权。作业查询仍按配置顺序遍历多个 owner 的公开端口并以无 owner 的 `job_id` 首个命中返回。同一请求的耗时会包含先验 owner 的失败或超时。候选耗尽会保留首条非缺席异常链，遇到后续命中就提前返回，局部保存的先前异常不会成为同请求的结构化步骤。后续用真实 HTTP 入口验证注册器调用形状，补齐前 owner 超时后命中的关联日志，并以两 owner 同 ID 的隔离用例明确解析范围和作业动作路由。 [闭包](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/backend/dashboard/application/service.py:32>) · [动态调用](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/backend/dashboard/application/service.py:264>) · [作业查找](</C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/f4dv/backend/dashboard/application/service.py:456>)

本机定向回归 `python -B -m pytest -p no:cacheprovider tests/test_http_failure_feedback.py -k "long_feedback_paths or unwritable_diagnostics or native_http_failure_denominator or job_resolution"` 为 **9 passed，7 deselected**。原生 HTTP、owner CLI 和 F4 静态计划的对照均已实测。独立验证未运行生产 F4 的分诊和修复动作。
