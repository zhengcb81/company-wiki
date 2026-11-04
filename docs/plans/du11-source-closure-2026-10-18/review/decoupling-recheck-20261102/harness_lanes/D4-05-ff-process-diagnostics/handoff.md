# D4-05 — FF 进程诊断不再否决已完成结果（交付）

状态：**已实现、已提交、已独立复审；两项 PARTIAL 已于 2026-11-04 闭合（POSIX 实跑 + ROOT 追认），待 ROOT 最终接收。**

## 基线

| 项 | 值 |
|---|---|
| 仓库 | filing-fetch |
| 基线分支 / HEAD | `main` / `508aba3`（Handle reaped Linux children in the independent cleanup probe） |
| 交付分支 | `d4-05-ff-process-diagnostics` |
| 实现 commit | `3118126`（Keep stderr diagnostics from vetoing delivered payloads） |
| 文档澄清 commit | `d874e14`（仅测试 docstring，无行为变化） |
| ET usage 用例 commit | `bf7e1da`（仅新增测试，无生产行为变化） |
| 交付 HEAD | `bf7e1da` |
| 环境 | Windows 11 / CPython 3.13.9（Miniconda）；pytest 9.1.1 |

工作树里未跟踪的 `.planning/du11-empty-placeholder-original.py`、`config/FMP_API_KEY.txt`、`pytest-of-ff-*` 属既有他人/历史资料，未读取、未修改、未暂存。

## 修改路径

- `scripts/ff_process_transport.py`（唯一生产改动）
- `tests/test_process_business_exit.py`（本卡真实子进程契约测试，原 3 个函数 → 22 个用例，含参数化）
- `tests/test_p5_process_transport.py`、`tests/test_p5_process_lifecycle.py`、`tests/test_transcript_owner_budget.py`（各改 1–2 处旧断言）

旧断言原本编码“stderr 超限即 `OutputLimitExceeded`”，与新合同直接冲突；只改这 4 处，未新增生产文件，未改 CWP、ET、公司来源、FF JSON schema、预算配置、用户 API、CI workflow 或其它仓。

## 逐项闭合点

1. **stderr 超限不再否决 payload。** 真实独立 child 先写完并 flush 合法 stdout JSON，再写 65,537B stderr：`run_bounded` 正常返回，`stdout` 逐字节完整，`stderr_bytes_read=65,537`，`stderr_truncated=True`，`len(stderr)=64KiB`（最新字节窗口）。另有 65,559B 多行日志用例证明尾部保留，且最终诊断行仍在窗口内。
2. **真实失败语义不变。** stdout 超自身 cap 仍 `OutputLimitExceeded`；stdout 不完整仍由 FF caller 判 `not JSON`；stdin 未完成仍 `ChildFailed(input_incomplete=True)`；deadline 到期仍 `ChildTimeout`（1.5s 用例），进程树在清理宽限内退出（`pid_is_alive=False`、无 `ff-process` 线程）。stderr 先写满管道、stdout 后到也不死锁。
3. **业务状态不被改写。** stdout 业务 `not_found`（exit 2，`allow_nonzero_exit=True`）+ 65KB stderr 仍返回 `not_found`/code 2；未 opt-in 的非零退出仍是 `ChildFailed`，stdout/stderr 保留。ET `--report-usage` 语义有专门用例：完整回执仍返回真实计数（3 / 4096），回执被挤出保留窗口时仍为 `unknown`（`provider_requests/provider_response_bytes=null`、`provider_usage_complete=False`），不编造 0；未改 transcript。
4. **关闭语义按本仓运行环境覆盖。** Windows 上用真实子进程覆盖超限、读错误、非 UTF-8 诊断、单行日志、极小 cap、首尾残缺 UTF-8、deadline、stdin 截断与进程树退出。测试只用 stdlib + `sys.executable`，无 Windows-only API；POSIX 生产路径（`start_new_session` / `kill_owned_group`）未改。

## 公开合同与兼容性

- `run_bounded` 结果新增 `stderr_truncated: bool`（向后兼容的新键）；`stderr_bytes_read` 明确为**实际读取总字节**，截断时大于 `len(stderr)`。
- `ChildFailed` 新增 `stderr_truncated`（默认 `False`，向后兼容）。
- `run_bounded_json` 仍返回三元组；stdout 仍 strict UTF-8；stderr 改为不透明有界诊断（非 UTF-8 原样返回，不再否决成功）。
- `stderr_cap_bytes=None` 仍保留完整流（仅 `_verified_open` 的精确回执显式使用）。
- 真实 deadline、调用者原 stdout/stderr 上限、stdin 语义、退出码、owned-tree cleanup、既有 FF JSON wire 均未变。

## 测试（确切命令与结果）

解释器：`/c/Miniconda/python -m pytest`（PATH 上的 `python` 是 WorkBuddy shim，无 pytest/pre-commit；提交时用 `PATH=/c/Miniconda:$PATH` 让钩子用同一解释器，未跳过钩子）。

| 阶段 | 命令 | 结果 |
|---|---|---|
| 基线（改动前） | 4 个进程测试文件 | **48 passed in 19.59s** |
| 失败优先 | `pytest tests/test_process_business_exit.py -q`（旧实现） | **9 failed**，全部 `OutputLimitExceeded: stderr exceeded its byte cap` |
| 契约文件（交付） | 同上 | **22 passed in 12.88s** |
| 受影响域（交付） | 23 个进程/传输/消费者/矩阵/FF 合同测试文件 | **600 passed, 1 skipped, 38 subtests in 93.13s** |
| 离线全量（交付 HEAD `bf7e1da`） | `pytest -q --ignore=tests/test_real_tool_conformance.py --ignore=tests/test_e2e_download.py` | **1407 passed, 6 skipped, 15 failed, 3 errors in 413.42s** |
| 静态 | `ruff check scripts tests tools e2e`；`compileall`；唯一测试符号门禁 | 全部通过 |

离线全量的 15 failed + 3 errors 与本卡无关且已证明为既有问题：4 个 config/policy/vendored 用例、5 个 `test_fc803_minimal_download`、6 个 `test_du11_transcript_reuse_e2e`（同一 `transcript_lookup_failed`）及其 3 个 teardown error。前 10 个节点在 `git stash` 掉本卡改动后逐字复现；du11 代表节点在基线与改动后同样报 `upstream_error/transcript_lookup_failed`；整文件在并发负载下无法跑完（SIGTERM），未计为通过。

交付 HEAD `bf7e1da` 已包含 ET usage 测试并在其上复跑全量（1407 passed）；契约文件 22 passed，受影响域 600 passed。

未运行：`test_real_tool_conformance.py`（会读生产 catalog，卡片禁止扩大范围）、opt-in 真实下载 E2E。产品路径未访问网络、未调用模型、未下载、未读 FMP key。

## 独立审查

- 审查者：独立 Explore agent（只读，未参与实现），2026-11-02，5m03s。
- 首轮结论“需修复”，提出 7 条：行对齐可能丢掉最多 64KiB 窗口；stderr 非 UTF-8 仍否决；stderr 读错误仍否决；`run_bounded_json` 不透出截断；凭据扫描只看保留窗口；消费者把截断窗口当完整 stderr；`None` 无界。
- 首轮已修 3 条：删除行对齐，改为纯“最新 cap 字节 + 起始残缺码点裁剪”；stderr 非 UTF-8 与读错误只置 `stderr_truncated`，不置 transport error。均新增测试。
- 首轮未改 4 条（复审确认可接受）：`run_bounded_json` 三元组是六消费者解包面，改签名违反“既有 wire 不改”，`run_bounded` 已透出标志；凭据扫描只看保留窗口（transport 不知道凭据；stderr 不返回用户，stdout 与 base64 payload 仍全量扫描）；消费者只把截断窗口用于诊断/产物，不参与业务判定；`stderr_cap_bytes=None` 是 `_verified_open` 既有显式上限。
- 复审：第二个独立 Explore agent 结论“可接收”，仅剩 1 条低危（首尾同时残缺的 UTF-8 起始字节），已按建议修复并加 `test_partial_utf8_trim_handles_both_cut_ends`（合计修复 4 条）。

## 六消费者核对（独审逐项）

| 消费者 | 成功路径 | 失败/资源路径 | 结论 |
|---|---|---|---|
| `scripts/fetch_filing.py`（query / ensure） | 只用 stdout JSON，stderr 不参与 | `ChildFailed` 用保留窗口分类；stdout 超限仍 `upstream_error`；deadline/stdin 不变 | 成立 |
| `scripts/ff_financial_statements.py` | 只用 stdout envelope | `ChildFailed` 从 stdout 透传业务拒绝；stderr 不参与 | 成立 |
| `scripts/ff_local_source_prepare.py` | 只用 stdout receipt，stderr 丢弃 | 超时/超限/启动失败映射不变 | 成立 |
| `scripts/transcript_tool_transport.py` | `_run_json` 不用 stderr；`_verified_open` 仍 `stderr_cap_bytes=None` 精确回执 | ET usage 截断时 `unknown`（不编造）；`_credential_exposed` 仍全扫 stdout/base64，stderr 只扫保留窗口 | 成立，凭据窗口见外限 |
| `tools/offline_contract_matrix/runtime.py` | `CompletedProcess` 适配，stderr 仅入产物 | `ChildTimeout`→`DeadlineExceeded`；非零退出原样返回 | 成立 |
| `e2e/run_p5_ff_real_source_acceptance.py` | 默认 cap，小回执 `json.loads` 不变 | 仅手工验收，不参与业务判定 | 成立 |

## 已证明 / 未证明的边界

- 已证明：默认 64KiB 与显式 cap 只约束保留量，不约束业务结果；stdout 与 stderr 额度互不借用；stderr 先洪泛、stdout 后到不死锁；deadline 不被续期；超限/读错误/非 UTF-8 诊断都不否决已交付 payload；进程树及时退出。8MB stderr 洪泛实测 8,388,608B 全量读取、仅保留 65,536B、0.2s 返回且 stdout 完整。**POSIX 实跑已于 2026-11-04 补齐（见下方偏差闭合记录）。**
- 未证明：真实 CWP/ET 生产子进程的 stderr 洪泛（只用合成 child，未写生产 catalog/网络）；凭据只出现在被丢弃 stderr 字节中的情形无法检测（该流不返回用户）；`run_bounded_json` 调用者看不到截断标志（需 `run_bounded`）。

## 完成度审计（对照任务卡）

第三个独立只读 agent 逐条核对任务卡后判定：核心目标、行为验收 1–3、保留项、六消费者、独审、handoff 字段均 **PASS**；2 项 **PARTIAL**，均已在交付中披露、不推翻合同：

1. **POSIX 关闭语义未实跑**：本机 WSL 被主机安全策略禁止，且无 Docker/Podman/Vagrant；测试只用 stdlib + `sys.executable`，在 Ubuntu CI 会执行同一组用例，POSIX 生产路径（`start_new_session` / `kill_owned_group`）未改。未声称已跑 POSIX。→ **已于 2026-11-04 闭合，见下方。**
2. **写域字面只允许 1 个契约测试文件，实际改了 4 个测试文件**：多出的 3 个仅更新旧“stderr 超限即失败”断言（4 处），无生产行为，需 ROOT 追认；若不改则这 4 个旧断言必红。→ **已于 2026-11-04 经 ROOT 追认闭合，见下方。**

审计确认 handoff 无与事实不符之处。

## 偏差闭合记录（2026-11-04，独立复审人执行）

两项 PARTIAL 均已闭合，闭合过程由独立复审人（未参与实现的第四方）完成：

1. **POSIX 实跑已补齐。** 复审发现本机 WSL 实际可用（此前“被主机安全策略禁止”的判断不成立；首次冷启动约 60 秒，曾被误判为被拦截）。在 WSL2 Ubuntu（Linux 内核，CPython 3.12.3，pytest 9.0.3）中实跑 4 个进程契约测试文件：**62 passed, 3 skipped, 0 failed in 65.62s**。3 个 skip 全部为 Windows 专属门控（`win32api/win32job` importorskip、Windows job 分配 ×2、Windows 族 process-tree reaper），这些路径已在 Windows 侧覆盖；POSIX 生产路径 `start_new_session` / `kill_owned_group` / `wait_owned_group_stopped` 在本轮真实执行且全部通过。任务卡行为验收第 4 条的 Windows 与 POSIX 两翼现已均有实跑证据。
2. **写域扩展经 ROOT 追认。** 2026-11-04，ROOT 接收方（用户）确认追认 `tests/test_p5_process_lifecycle.py`、`tests/test_p5_process_transport.py`、`tests/test_transcript_owner_budget.py` 三个相邻测试文件的写域扩展（4 处旧断言翻转，纯测试、无生产行为）。追认已记录于本节。

### 独立复审复核清单（2026-11-04，均由复审人独立执行）

- Git 事实：`main..HEAD` 恰好 5 文件（1 生产 + 4 测试），3 commits 与基线 `508aba3` 核实一致；未跟踪文件 mtime 均早于交付日。
- 契约文件实跑：**22 passed**（与交付记录逐秒一致）。
- 受影响域实跑（复审枚举 24 个引用 transport 的测试文件，为交付记录 23 文件的超集）：**638 passed, 1 skipped, 38 subtests**。
- 离线全量实跑（`--ignore=tests/test_real_tool_conformance.py --ignore=tests/test_e2e_download.py`）：**15 failed, 1407 passed, 6 skipped, 3 errors**，失败清单与交付记录的分解逐字吻合。
- 基线复现：在 `main@508aba3` 独立 worktree 中复跑同 15+3 节点，**逐字复现**；du11 节点失败原因同样为 `upstream_error/transcript_lookup_failed`，与本卡无关。
- 六消费者逐一读码核对（非转录独审表格）：`fetch_filing` 的 `producer_output_exceeded` 现仅可能由 stdout 触发；`_verified_open` 精确回执（长度 + SHA256、`stderr_cap_bytes=None`）未变；矩阵 runtime `ChildTimeout→DeadlineExceeded` 不伪造结果；ET `_provider_usage` 截断回执诚实返回 unknown。全部成立。
- 静态：`ruff check scripts tests tools e2e` 与 `compileall` 复跑通过。
- 生产 diff 逐行核对：改动严格限于 stderr 保留窗口、移除 stderr UTF-8 否决、新增 `stderr_truncated` 透出；deadline/spawn/cleanup/stdin/stdout 探针字节逻辑未动，无缓存、内存恒有界。

## 临时资料清理

- 未创建 canary、授权文件或临时目录；pytest `tmp_path` 自动清理；deadline 用例显式断言子进程与 `ff-process` 线程均已退出。
- 未覆盖原件、生产数据库/配置、他人 WIP；未跟踪文件保持原样。
