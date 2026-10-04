# N4-T1：MAIN 跨层验收

Status: ACCEPTED / INTEGRATED / PUBLISHED。N4C 未完成，N4-T2 尚待交付。

MAIN 已把 71f867a（S5入口退休）、5de9154（T1）、66808ee（跨层E2E及交接）推到 origin/master；pre-push 快速契约集 GREEN。远端代码 CI：[37241977614](https://github.com/zhengcb81/company-wiki/actions/runs/37241977614) 已完成 success；实际一个 job，22:57:45–22:58:57 UTC（72 秒），Unit tests 30 秒、Focused contract tests 2 秒，两个步骤均 success。没有将 push 成功代替 CI 验收。纯文档发布收据随后提交，不重新跑业务测试。

## 提交接口

- 外线 `C:/cw-lanes/n4t1/company-wiki`，分支 `codex/n4t1-model-transport-diagnostics`，base `349d331e64c84e721b45c4c43ac1c58ffa291815`，head `4a53080b737cb98f54473729f5029213e758206e`，远端同 head，工作树干净。
- 六个改动文件均属卡片写集：三个 automation HTTP/caller/summarize 文件及对应三个 unit 测试。未找到独立 handoff，采用 commit 说明和 MAIN 实际复核记录，不增加补签收门；外线 RED 时长未提供，不虚报。
- MAIN 仅 cherry-pick 该提交为 `5de9154`，保留 MAIN 后续 PWF、紧凑模型请求和 S5 入口退休。没有用两个分支 tree diff 覆盖文件，没有修改外线 worktree。T2 可从交付 4a53080 接续；MAIN 后续只取 T2 自己的新提交。

## 验收行为

4xx（429 除外）稳定终态 MODEL_HTTP_CLIENT_ERROR，5xx 可重试 MODEL_HTTP_SERVER_ERROR，429 原有限流语义保持。仅数字 HTTP 状态可穿透安全诊断；错误正文、密钥、prompt、完整 URL 不入异常或持久记录。非 2xx 与缺字段/空正文等 2xx 无效响应区分。

已尝试 HTTP 而无有效 usage 的 reservation 按预留上限计费，不清零；能证明未发请求的凭证前置错误才零结算。adapter 没有增加内部重试。旧未知付费用量的根因仍无法由此次修复倒推。

## MAIN 实际验证

~~~powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -B -m pytest -q -p no:cacheprovider tests/unit/test_narrative_http_model.py tests/unit/test_narrative_model_caller.py tests/unit/test_narrative_summarize_handler.py tests/unit/test_narrative_model_request.py tests/unit/test_narrative_run_store.py tests/integration/test_narrative_batch_cli_e2e.py --basetemp tmp/ptn4t1 --tb=short
~~~

**114 passed / 48.56 秒**，包括紧凑请求兼容、实际 loopback HTTP、正式 subprocess CLI/Worker、持久预算与清理恢复。

MAIN 另增加 `test_cli_persists_safe_http_status_and_unknown_charge_without_provider_body`：完整 CLI 经真实本机 HTTP 400，检查 SQLite attempt 的稳定 error_code 和数字 status detail，budget ledger unknown 仍 charged=reserved>0、无 final；provider error body sentinel/合成 key 不在 stdout/stderr 或库字节中；原件与非本次 jobs 不变，夹具退出恢复原测试目录。单项 **1 passed / 6.59 秒**（`--basetemp tmp/ptn4sql`）。两个测试根只在退出后按绝对包含路径删除。

Ruff 对六个外线文件加两个 MAIN E2E 文件通过，git diff --check 通过。无外网/付费模型/凭证/生产来源操作；HTTP 仅合成本机 server。

## 下一接口

N4-T2 交付后 MAIN 联合验收选择/摘要/verified final，再做有限真实模型运行。旧 unknown reservation 10,325 tokens/$0.005258 原样保留；紧凑招股书预留 49,730 加旧量为 60,055，超过既定 60,000 tokens，发请求前须缩小明确输出上限并重算，不扩预算、不重置旧账本。HTTP 诊断修复不等于 N4C 真实摘要、P1/P2/P4 或 ET live 已完成。
