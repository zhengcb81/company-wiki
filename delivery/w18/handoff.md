# W18-CWP-HOLDOUT 交接（2026-10-25）

状态：**COMPLETE**（全部 H 项 PASS，独立审查四轮闭环，零未解决本范围 finding）。
机器可读版：`handoff.json`；逐项审查：`review.md` + `review/` 三份原报告；
冻结基线结果：`findings.md` + `baseline-summary.json`；恢复/清理收据：
`recovery-receipts/dual-root-receipts.json`、`recovery-receipts/cleanup-inventory.json`。

## 交付物

- **冻结源侧金标**（`tools/holdout_replay/manifest.json` + `gold/w18-*.json`×8）：
  8 份真实原件 / 5 公司 / CN+HK+US 全类型 + 治理负例；96 业务目标 / 116 锚点，
  全部经独立重提取逐字验证。v1 冻结于 5e4488bb（先于任何候选输出 76 分钟）；
  v2/v3/v3.1 修正逐项源侧理由见 `gold_corrections.json`，v1 字节级以冻结提交
  git blob 为准（内容归档 `gold/archive-v1/`）。SHA pin 锚提交 LF 字节，跨行尾
  检出配置一致。
- **可复现回放工具**（`tools/holdout_replay/`，单一入口
  `python -m tools.holdout_replay`）：verify-freeze / bootstrap-lake / run 三个
  子命令；冻结 producer commit 验证（HEAD==commit+生产树干净+import 根断言）、
  bindings/SHA 索引双解析、DU-BENCH native 观察 + configured_preview 零 POST
  任务编译、attempt 不可覆盖落盘、逐目标机械可见性+DUB 评估。选择器代际
  （observe 默认 vs compile 钉 0.9.0）逐工件盖章披露。
- **测试**（`tests/holdout/w18/`，20 项全绿）：manifest 结构/H01 覆盖矩阵/
  重复原件拒绝；中性 PDF/TXT/HTML 夹具、双绝对根（含中文+空格）、外部 cwd、
  污染 PYTHONPATH 拒绝、超时/失败/结果已存在不覆盖、cleanup 只清 owned 目录。

## 冻结基线（ba8f8543 真实链，三个 attempt 完整保留）

8/8 样本回放成功，原件前后 SHA 不变，零模型 POST/零下载/零网络。
机械可见性：10/96 选中 span 支持、16/96 进入编译模型输入、73/96 两者皆无、
0 锚点页未读；DU-BENCH 独立评估 8 PASS/41 FAIL/22 PARTIAL/25 NOT_EVALUATED；
96 目标全部 not_reviewed（无模型响应/无语义审查）。gold v2 修正未改变任何
判定（attempt-3 与 v1 数字逐项一致）。

**交 ROOT 的产品 finding（F1-F4，本卡不修生产代码）**：招股书 675 页批处理
链 PARSER_INCOMPLETE（直连路径可选 160 spans，两路径行为不一致）；海康 DOCX
电话会 SOURCE_LANGUAGE_TEXT_EXTRACTION_FAILED（catalog kind 路由分歧）；
73/96 选择覆盖缺口（候选生成/选择层，页面全部已读）；disposition_context
无 context 层 NOT_EVALUATED。

## 独立审查（四轮，全部原报告保留）

R1 三 agent：gold 审查（113/113 锚点逐字+36 项语义抽查+prior_use+先冻结核实，
1×P2+5×P3）；工程审查（H01-H11 全 PASS+收据哈希复核，6×P3）；独立重放验证
（PASS：重放逐字节确定性、失败/清理/不覆盖链、否定/条件与期间单位错配双反例
确认词匹配不代签）。R2 双 PASS（各 3-4×P3 新发现）。R3 终审双 PASS。全部
finding 修复并经审查员确认；最终代码 commit faa488a7，docs 收尾 28f06a9a。

## 用量与边界

模型 0、下载 0、外网 0；主仓零写入（原件只读）；持久新增 335,741 字节
（git 内）；本地 scratch 证据 ~23MB（attempt/lake/收据，ROOT 验收后可清）。
bindings.local.json 为本机只读配置，不入 Git。真实摘要质量与 RF 采用仍是
ROOT 范围；本卡输出为源侧观察。

## ROOT 接收步骤

1. 修复后候选 commit：`python -X utf8 -m tools.holdout_replay run --producer-repo <候选worktree> --producer-commit <完整SHA> --bindings <本机bindings> --out-dir <新目录> [--lake-config ... --llm-config config.yaml --llm-provider minimax]`
2. 与 `baseline-summary.json` 的冻结基线三个 attempt 对照（旧 attempt 永不覆盖）。
3. 逐目标处理 F1-F4；词匹配/模型输入可见性不得代签摘要质量。
4. 分支 `codex/w18-cwp-holdout-20261025` 已推送 origin；主线并入归 ROOT。
