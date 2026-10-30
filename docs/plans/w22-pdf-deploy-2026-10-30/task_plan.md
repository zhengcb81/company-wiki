# W22-PDF-DEPLOY

PLAN_ID=w22-pdf-deploy-2026-10-30; PWF_PLAN_ROOT=docs/plans.

唯一入口 TASK_CARD.md；独占范围/测试/交接协议以该卡为准。

## 当前状态

READY_TO_DISPATCH。ROOT只建独立工区与四个计划seed，未运行实现或测试。本目录四个未跟踪seed是已知脚手架，可纳入作者首次提交。

## 阶段

- A 调查/冻结行为：done（2026-10-30，证据与设计见 findings.md）
- B TDD与实现：in_progress（tools/pdf_runtime_deployment/ + unit tests，TDD RED→GREEN）
- C 短域/实际入口/清理/真正独立审查：pending
- 交接：pending，只有最终代码与审查一致才READY_FOR_ROOT；否则PARTIAL。

## B 阶段实施清单

1. `tools/pdf_runtime_deployment/_describe_probe.py`：源解释器内 metadata-only closure/RECORD probe。
2. `tools/pdf_runtime_deployment/deployment.py`：plan/deploy/verify/status 纯库函数（probe 输出作为数据
   注入，便于故障注入单测）。
3. `tools/pdf_runtime_deployment/__main__.py`：plan|deploy|verify|status|constructor-probe CLI。
4. `tests/unit/test_w22_pdf_deployment_plan.py`：ASCII 校验、目标分类、plan 构建、诊断不升门禁。
5. `tests/unit/test_w22_pdf_deployment_recover.py`：中途失败恢复、源变更、外来冲突、重复执行零写。
6. `tests/unit/test_w22_pdf_deployment_config.py`：输出配置与生产 `ParagraphRuntimeConfig` 往返、负对照
   （错配 proposal 必被对齐拒绝）。
7. `tests/integration/test_w22_pdf_deployment_entry.py`：显式 opt-in（env `W22_PDF_DEPLOYMENT_E2E=1`），
   L0/L1 验证 + no-document constructor + 合成 PDF 真实入口 E2E。

## Next Step

先写 unit tests（RED），再实现 deployment.py（GREEN），短 basetemp 记录耗时。
