# W22-PDF-DEPLOY 进度

2026-10-30 ROOT预置独立稀疏工区，基线662f821e749bc221c8c308986e54e00465834332。只有计划seed；未启动施工、实测、独审或收费操作。作者接手后更新本文件，勿改ROOT共享PWF。

## 作者进度（2026-10-30）

- A done：证据判读与部署设计见 findings.md（根因=非ASCII部署资源路径，判别变量已由W21对照冻结）。
- B done：tools/pdf_runtime_deployment（plan/deploy/verify/status/constructor-probe/warm-cache CLI +
  deployment 库 + 2 probes + 合成PDF helper + 对齐诊断）。unit 19 个 TDD（先 RED 后 GREEN）。
- C1 done：真实部署 C:/cwp-runtime/w22-pdf-sdk — plan 327891cf…（104 dist/36,121 env 行/6 模型行，
  源配置=bcc42711…=W21接收review冻结的 profile 字节）；deploy 36,127 hardlinks 零复制，417s；
  verify L0+L1 PASS，零写复核 true；no-document constructor CONSTRUCTOR_OK 22.748s/30s。
- C2 done：canonical 配置真实 E2E — 首跑如实记录（china-s 夹具 mojibake→accepted0；pycache 冷编译
  120s 封顶一次）；换 ToUnicode 夹具后 **status=enhanced, accepted_groups=2, rejected_groups=0**，
  completed [1,2]，worker 17.04s/120s，峰值 3.10GiB/4GiB，负对照拒绝，源文本保持。收据在
  delivery/w22-pdf-deploy/receipts/。integration 4/4（显式opt-in），unit+既有节点 62 passed，
  mypy/ruff 全绿。部署协议层发现：.venv python.exe 带 Low MIC（复现AGENTS既有记录）。
- 独审：两轮完成。代码独审初判 NOT READY（D1 repo-src off-by-one / D2 工具身份漂移 / D3 收据缺字段）
  + samefile 恢复契约反例；环境独审 ACCEPTABLE。全部修复已提交（见 findings.md 独审与修复节）。
- D2 最终绑定（第三轮，最终代码）：退役中间版部署（收据存
  review/deployment-intermediate-revision-99a5d250.json，退役后模型源 SHA 复核未变）→ 重新
  plan `1cba5f2e…`（行集与前两轮完全一致）→ deploy 36,127 links COMPLETE → 收据工具 SHA
  `302bf87d…` == HEAD deployment.py 逐字节 → verify PASS+零写+recorded_in_receipt → 生产形态
  constructor CONSTRUCTOR_OK 22.95s/30s（bare 形态冷态两次 >30s 超时如实记录，未抬封顶未改收据；
  L2 重绑到生产 child launch 形态）→ L0-L3 集成 4/4，L3 E2E enhanced accepted2/rejected0。
- 复审（两 agent 第二轮）：环境 **ACCEPTABLE**（新树 A-F 全过、工具 SHA 四向一致）；代码
  **READY_FOR_ROOT**（D1/D2/D3 全闭合、重绑无弱化）；遗留非阻塞 R3（REUSED samefile）已按审查者
  最小修复采纳（2562d3b4）并由审查者核验 **PASSED**，最终判定 READY_FOR_ROOT。
- 最终绑定链（R3 修复后 HEAD）：plan `498b7555…` → deploy 36,127 links COMPLETE（110.6s）→ 收据
  工具 SHA `be7dcf34…` == HEAD `deployment.py` 逐字节 → verify PASS+零写+recorded_in_receipt →
  生产形态 constructor CONSTRUCTOR_OK 12.708s/30s → L0-L3 集成 4/4（L3 E2E enhanced
  accepted2/rejected0，worker 15.99s/120s）。
- 交接：`delivery/w22-pdf-deploy/handoff.md` + `handoff.json`（harness-handoff/1，OPEN=[]）；
  status=READY_FOR_ROOT，pushed_to_remote 待推送后更新。
- 后续：STOP 等 ROOT 接收（集成 ATOMIC+本工具、正式配置采用、真实 C2/摘要/缓存/RF 均归 ROOT）。
