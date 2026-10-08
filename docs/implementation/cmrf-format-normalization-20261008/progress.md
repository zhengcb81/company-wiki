# R6-FORMAT Progress

## 2026-10-08

- 建线:确认工作树/分支/基线与 worktrees.json 一致(eaad25a4,干净,sparse 27%)。
- sparse-checkout 增加本线 docs 目录。
- 只读核实:Worker 拒绝点(narrative_select.py:300)、NarrativeUnit/DocumentStructure/
  EvidenceSpan/QualityFlag 合同、narrative_replay 语义、source_reader 只读性。
- 定位并 SHA 验证两份真实原件(微软 SEC HTML 8.1MB;MSFT PPTX 4.0MB),登记 findings。
- 写 task_plan/findings/progress。
- 实现包 `src/company_wiki/document_normalization/`:`__init__`(冻结入口 +
  normalize_document 路由)、`errors`、`limits`、`assets`(OpaqueAsset + 具名缺口)、
  `text`、`units`(unit_id 身份绑定 + verify)、`document`(NormalizedDocument)、
  `html_parser`(cwp-html-dom/1)、`pptx_parser`(cwp-pptx-shape/1)、`replay`。
- 修复实现期发现:所有权双计、cell 内 `<p>` 包装归属、external rel 的
  target_partname ValueError、cell 坐标 O(n²)、空/非 HTML 输入空成功、
  Package→Presentation、PNG fixture。
- 测试包 `tests/document_normalization/`:conftest(HTML/PPTX 构造器)+
  test_limits / test_html / test_pptx / test_replay_and_determinism +
  run_real_originals.py CLI。
- 大节点:64 测试全绿(11–18s);RED(移除包)exit=4;真实原件运行 exit=0,
  报告 real_originals_report.json;原件 SHA 退出复验未变;__pycache__ 清除;
  git status 仅三个独占目录。
- HANDOFF.md / handoff.json 写入;提交分支。

## 状态

- implementation_started: true(已交付)
- RED: exit=4(基线无包,ModuleNotFoundError)
- GREEN: 64 passed / 0 failed / 0 blocked
- 真实原件大节点: PASS(HTML coverage complete;PPTX 诚实 partial)
- model_calls: 0;网络: 0;原件删除: 0;生产配置改动: 0
