# RF 与 Dashboard 独立复审

2026-11-26。受验对象是总控工作区的隔离候选 `.planning/r25/rf` 和 `.planning/r25/dash`。RF 基线 `49a4013d`，Dashboard 基线 `b57672fd`。使用合成原件、真实本机子进程、可控 owner 端口及回环 Chromium。远端供应商、真实下载和费用均为零。

| 仓 | 原问题复验 | 最终判定 |
|---|---|---|
| RF | 3 项通过。真实迟到子进程只改自己尝试的结果、Markdown 和注册表。整个作业成功后仍可用原 F4 观察查回旧中断。新旧两种归档布局通过正式入册、重复调用及新进程只读查询。归档读取未加载写入准入。 | **FAIL**。RF 作业 F4 查回接受与原尝试不相符的父运行号或尝试号。 |
| Dashboard | 10 项真实 ASGI、强停、启动、查重与显式 owner 回归通过。真实 Chromium 的 200 和 206 迟到故障均显示与冷读一致的相关号。 | **FAIL**。无 owner 的 mutating 路由可能在一个 owner 超时后修改另一个 owner 的同名作业。 |

## RF · F4 终态归属

问题代码在 `scripts/rf_job_feedback.py:169–192`。公开 lookup 根据 evidence_ref 和步骤找到持久尝试。同一尝试的已存 `feedback_run_id` 和 `feedback_attempt_id` 尚未参与这个分支的对账。日周和普通 CLI 失败已经按本仓索引校验这两个身份。

在 RF 候选的现有 `tests/test_rf_job_facade_cli.py::_deployment,_request` 合成夹具中，设当前运行号与尝试号为 `audit-orig-run` 和 `audit-orig-attempt`。执行正式 `rf_job_cli submit`，确认作业成功和费用 USD 0.00。取其 `compute-1` 的 `action-started` 观察，使用 `tests/test_f4_failure_coverage.py::reconcile_observation` 封装真实新进程。启动三个独立 lookup，每次按送入的新 payload 重算协议摘要。

| 查询 | 结果 |
|---|---|
| 原观察 | `done / succeeded / known` |
| 仅将 `run_id` 改成合成的另一个 run | `done / succeeded / known` |
| 仅将 `attempt_id` 改成合成的另一个 attempt | `done / succeeded / known` |

所有 owner 字节查询前后完全一致。第二、三条须回报未匹配，原证据仍可查。历史尝试缺身份字段时，回退语义按该格式实际持有的身份信息逐条验收。单纯接受任意附带身份会把另一个运行归成已完成。受验 `rf_job_feedback.py` SHA-256 为 `c0e754cf41b8117c7d9c244266515e5677a8c791dfa4819c209f30d09cbf8e61`。

正向命令为 `pytest -c test-env.ini --rootdir . --confcutdir . -p no:cacheprovider -q tests/test_rf_job_attempt_lifecycle.py tests/test_report_catalog_rf_job_import.py -k "late_compute or registers_completed"`。在候选根关闭 pytest 自动插件，使用独立短状态目录和 `PYTHON_DOTENV_DISABLED=1`，结果 3 通过，41 未选中。

## Dashboard · 未知匹配的作业变更

问题代码在 `backend/dashboard/application/job_resolution.py:62–83`。无 owner 的动作询问所有端口，多个确定命中时返回冲突。某个端口在查到身份前失败时留下异常，后一个端口命中后仍直接发送动作。作业归属只有部分证据。

沿用 `tests/test_http_failure_feedback.py::test_owner_scope_keeps_overlapping_job_ids_from_mutating_the_wrong_owner` 的真实 HTTP、两个 owner 端口和合成 `shared-id`。给第一个端口增加一个 `online` 标记。置为 false 时令其 `get_status` 抛本仓现有 `OwnerPortError(owner, "timeout", "fixture owner not queryable", True)`。第二个端口仍正确实现公开接口。每个分支对同一路由只提交一个 `cancel` 请求，观察端口调用次序。

| 请求 | 已观察状态 | 已观察变更 |
|---|---|---|
| 两 owner 均在线，无 `owner` | 409 `job_owner_conflict` | 0 |
| FF 超时，RF 命中，无 `owner` | 200 `cancelled` | RF 收到一次 `cancel` |
| FF 超时，显式指定 RF | 200 `cancelled` | 只查询和变更 RF 一次 |

未指定 owner 的读请求仍可返回下一家的确定命中，并留下第一家故障轨迹。对变更动作，第二条须保持零次变更，并可据返回相关号查明未能排除 FF 的原因。明确指定 owner 继续直接路由现有动作。受验 `job_resolution.py` SHA-256 为 `2097cc4477b15afc0056eee0cae2583513dd98e76bb7aefcbd4b9fa0d49e1cc5`。

ASGI 定向为 `pytest --rootdir . --confcutdir . -p no:cacheprovider -q tests/test_request_lifecycle.py tests/test_http_failure_feedback.py -k "original_stream or real_startup or real_process_kill or overlap or first_owner_fault"`。实际浏览器执行 `tests/e2e/preview_isolation/test_f4_stream_correlation.py`，使用候选已有前端产物、固化好的 listing 查询夹具、Windows 本机 Playwright 缓存和 Uvicorn 回环。一条测试分别验证 200 与 206 的前端错误和冷读号，合成原件每个分支各打开、关闭一次。当前浏览器夹具 SHA-256 为 `aa94ea96ba5d0a34696a7fedd9ce4726d242061af71d2a3a6437ba47757ec214`。

## 修复后独立复验

| 模块与受验补丁 SHA-256 | 正向、负向结果 | P1 判定 |
|---|---|---|
| RF `1545fbe4bc8bfdb48e3ae513fb7a3d6362067ea60b759bf89b9dad4a200114d9` | 通过正式 CLI 提交合成零费用工作，用三个新进程冷读。原身份为 `done/succeeded/known`。改变父运行号或尝试号均为 `unknown/native_attempt_mismatch` 且无费用结果。查询前后原 owner 文件字节一致。 | PASS |
| Dashboard `b7afd40994da2c2a59be11636951d998a2fadd5e28ba28cd22b1a73c74bad11e` | 真实 HTTP 同 ID 双命中与第一 owner 超时均为 409，收到动作的端口数均为零。显式 RF 为 200，只查询和取消 RF 一次。无 owner 的普通读仍为 200，命中 RF；未触发动作。 | PASS |

上述二次判定仅替换前文两个原 P1。其余确证范围仍沿用原测试表，生产部署和远端状态由总控另行验收。
