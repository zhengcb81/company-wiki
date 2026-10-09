# MAIN replay config isolation handoff

工程 PASS，可供 MAIN 正常合并。产品/经济验收由独立实际节点决定。

- Base: `8479b8ad1eae5031ca6d01d5e540824cafa4a60f`
- Runtime commit: `ff4307630f7985898341ea07360d030899957e43`
- Branch: `codex/main-replay-config-isolation-20261009`
- Worktree: `C:\Users\郑曾波\Projects\_harness_worktrees\cmrf-20261008\cwp-formats`
- Preserved selector branch: `760ed472fc002820371da5d622d4540296f680a6`

## Root fix

Replay 不导出 host config/，只生成本夹具 catalog/acquisition 配置并声明 no-OCR/parser1.1.0。Live 维持原 committed HEAD config snapshot，记录 profile、HEAD、local_ocr hash、实际 identity。没有修改 src、OCR 接线、预算/完整度门、生产配置或 MAIN 脚本/PWF。

Probe 在解析/断言/超时前将实际 AUTO 小证据写 JUnit property；runner 将 stage/attempt/error、artifact pin、native budget/reservations、scalar selection/parser、实际 public read quality 收入 checkpoint。SQLite read-only/query_only；9 条上限和总数、32KiB cap；不复制 DB/raw/原文/提示词/密钥/租约。Unknown 不归零；旧绑定未声明 OCR 保持 unknown。现 capability classifier 完全未改，deadline/refusal/未分类 partial 仍 FAIL。

## Evidence

- 真正 RED: 5 failed /1.21s。集中 GREEN:35 passed /5.93s；最后 legacy unknown 边界6 passed /0.89s（CLI deselected），合计36 distinct passing tests。Ruff no-cache/diff-check PASS。精确 commands 见 README/handoff.json。
- actual tiny fixture: official local import→public batch，1页29,620B 合成原件，3.307511s，实际 frozen parser1.1.0/no OCR config。Select PARSER_INCOMPLETE，summary/verify DEPENDENCY_TERMINAL，全3 jobs dead_letter；artifact null；reservations[]；tokens/cost/unknown/unsettled全0。诚实 capability BLOCKED，非完成产品。
- 原件 SHA/mtime/readonly 与 fixture/host config SHA 前后一致，actual native metadata2,170B。两个 owned CLI roots 实际不存在，进程返回后 cleanup。原22页PPTX零读/零改/零OCR；供应商0；未整71回放。
- 首次真实 CLI 后因 reader 错用 parser_component envelope 断言失败；3.914318s 的 native receipt 原样单独留存，parser metadata null、后续保护断言未执行。修 source_inputs reader 后实际成功记录在 tiny-cli-actual.json。不能把首次失败补说成完整 PASS。
- 旧 fixed71 report SHA仍 `38a15df00e1f3b16469279731495a64617b5db772fb8d4fec7c2b916306b14e5`；其 partial/已删除 ledger 明细不被修改/补造。根因只读诊断在 MAIN phase6/no_ocr_fixture_diagnosis。

## Integration

正常合并此 branch（包含 runtime commit 和 handoff metadata commit），无需重签旧 dead jobs 或改原 frozen request。固定 replay 应按 fixture capability 报告 no-OCR PPTX gap；实际 configured 能力由 MAIN 独立真实节点验收。本任务不跑额外 review、full22 OCR 或整71。
