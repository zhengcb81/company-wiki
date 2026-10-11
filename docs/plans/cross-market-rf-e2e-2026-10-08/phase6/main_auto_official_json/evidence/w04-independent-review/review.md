# W04 独立工程边界复核

## 结论

**通过，可进入 MAIN 正常提交与发布。** 本次没有发现 W04 产品阻断问题。此结论只覆盖工程边界接收；不核销真实配置供应商调用、公司资料处理与研究审查任务，也未重新执行已有 public3 / 168 / 56 大包。

实读 `w04-main-reception/HANDOFF.md`、`OWNED_DIFF.txt`、`FINAL_SHA_RECEIPT.json` 和所涉实现后，新增六项独立最小探针。调用实际 `FailedFinalDiagnostic`、`fit_failed_final_result`、HTTP 响应解析器、真实 SQLite AUTO / NarrativeRunStore 与预算 caller / batch 恢复判定；没有替换产品实现。这里的 DecoderOnlyModel 仅把准备好的响应交给真实解析器，未调用供应商或模型。

## 六项结果

| 探针 | 实际新验证 | 结果 |
|---|---|---|
| 既有 envelope 与 JSON escape 开销 | 包含非 ASCII 主错误、既有 result、已付费 metrics、NUL/引号/反斜杠/emoji/组合字符；完整 canonical HandlerResult 为 16,382 bytes，增加一个 codepoint 后恰好 16,384；既有结果/错误/metrics 保持 | PASS |
| 精确 metadata 边界，None 与空 final | 两者的 metadata candidate 均在 16,384 bytes 被舍弃，16,383 可保存；None 仍未知，空字符串仍真实 0 bytes / e3b0 SHA | PASS |
| 真实 ledger + malformed partial usage | prompt=73/completion=True 不被当成有效 usage；None/空 final 两者均真实结算 reserved 219 tokens / 124 microUSD，unknown=1/unsettled=0；正式 output=0/SHA=None；同 attempt 再入不增加 decoder 调用，完整 SQLite dump 不变 | PASS |
| raw wire SHA 与 decoded final SHA | ASCII escaping 与真实 UTF8 JSON 原实体 SHA 不同而 final SHA 相同；NFD 与 NFC final SHA 不同；CRLF/BOM/NUL 与组合字符严格保持，隐藏 reasoning sentinel 不进入诊断 | PASS |
| 多 owned jobs / foreign run / scoped outbox | 25 个更早 foreign pending/leased/failed outbox 不干扰本 run；真实 FK scope 在 LIMIT 前过滤；owned effects 即使 FAILED/CANCELLED，实际 owned pending/failed（future not_before）仍使 readonly-idle=false；owned delivered 时 foreign 工作不妨碍 readonly；DB/待处理 jobs 不变 | PASS |
| 真实 persisted storage 与真实超用量状态 | 三种实际落库 storage reason 均返回 storage_exhausted；真实 reserved output cap64 收到73+65 usage 后 ledger 自主 block 为 MODEL_USAGE_EXCEEDS_RESERVATION、budget_exhausted，收费138 tokens，verify 仍 PLANNED | PASS |

精确 metering/hash/error 结果在原生 JSON receipts 中，可复查所有细节。storage 三项是对实际持久化 block reason 的状态映射验证，未声称本次造成真实磁盘配额耗尽；超用量项则确实走真实 admission/settlement。恢复项调用实际读 API 与判定函数，未重复整条 native public CLI 恢复；该完整 public 路径仍沿原交付大节点证据。

## 驱动错误与原记录

首次集中小包为 5 PASS / 1 驱动错误，耗时 4.9655871s。边界探针用 `dataclasses.replace(base, error=...)` 重用了已冻结的 `result` mapping，违反真实 HandlerResult 构造必须传 fresh dict 的约定，在进入产品 fit 前报 TypeError。原 `receipt.json` 和 `attempt-01/{probes.py,receipt.json,classification.json}` 保留，不改写为全绿，也不把它归为产品缺陷。

仅修自有驱动为 fresh dict，并只重跑失败的精确边界探针：1 PASS / 0.0051428s，另存 `boundary-receipt.json`。最终六项唯一探针为 6 PASS；未把此前五项重复跑一遍。`summary-receipt.json` 逐项归总两个真实运行记录。

## 保护与恢复

两个运行均核对交付所列 7 个源码 + 3 个既有测试的 SHA 与 FINAL_SHA_RECEIPT 相等，前后完全一致。原 HANDOFF / OWNED_DIFF / FINAL_SHA_RECEIPT、生产 config/source_catalog.yaml / config.yaml、环境变量保持；每次只创建独占 TEMP SQLite，结束删除并确认不存在。W03 的 narrative_candidates.py / narrative_evidence.py 单独记录为其他 owner 归属，本次两次前后也完全一致，不误报为 W04 写穿。

只写本目录的驱动和接收证据，没有源码、既有 tests、PWF 共享、安装目录写入，也没有 commit / merge / push / reset / stash。network connect 被测试驱动拒绝，尝试数为 0；provider / LLM 外部调用 0，新费用 $0。

## 复现

从 isolated CWP MAIN 树运行（不带 selection 会跑六项；带 selection 仅跑指定项，并使用独立 receipt 名）：

```powershell
python -I -X utf8 -B docs/plans/cross-market-rf-e2e-2026-10-08/phase6/main_auto_official_json/evidence/w04-independent-review/probes.py "C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki" exact-16384-metadata-none-versus-empty fresh-boundary-receipt.json
```

driver 要求当前 W04 源 SHA 匹配已交付 stable snapshot；后续源码改动时应在新节点明确新的基线，不能修改旧 receipt 的 SHA。复现请用新的 receipt 名保留历史运行记录。

## MAIN 接口

接收现有 FailedFinalDiagnostic typed optional diagnostic 与 scoped outbox read API，保持原主错误/费用/正式产物语义；不增人工许可或小节点门。ROOT 可按既定正常提交与精确 CI / 发布流程继续。真实供应商 / 真实公司研究任务保留为未完成，和本工程验收分开记录。
