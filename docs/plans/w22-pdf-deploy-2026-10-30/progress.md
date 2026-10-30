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
- 独审：两个独立 agent 并行中（代码/规范一致性+反例测试；部署环境/硬链接源保护/磁盘账目）。
- commits: B phase + C phase（见 git log）；push 待独审后。
