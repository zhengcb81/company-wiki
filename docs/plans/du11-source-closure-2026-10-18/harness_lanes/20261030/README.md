# W22 独立施工总表（2026-10-30）

状态：READY_TO_DISPATCH。仅表示卡和独立工区已准备，不表示用户已发出、作者已开工或工程通过。主线仍为 M8 来源准入/限定/上下文根修 → 真实摘要/缓存恢复 → RF 实际采用；本批不改变该顺序。

本批两张新卡，均处理 W21 接收报告已确认的未完成基础设施问题，不重复已完成的 W20/W21 工程。两张都在 company-wiki 项目，**工作目录、分支、可写文件均分开**，可同时启动。

| 卡 | 独立工作目录 | 独占写入 | 交付 |
|---|---|---|---|
| [W22-CWP-ATOMIC-IO](W22-CWP-ATOMIC-IO.md) | `C:/Users/郑曾波/Projects/company-wiki-w22-atomic-io` | `_atomic_file.py`、pre_push_gate 的临时目录布局、相关专属测试 | `delivery/w22-atomic-io/handoff.md/json` |
| [W22-PDF-DEPLOY](W22-PDF-DEPLOY.md) | `C:/Users/郑曾波/Projects/company-wiki-w22-pdf-deploy` | 新 `tools/pdf_runtime_deployment/`、专属测试、独立部署目录 | `delivery/w22-pdf-deploy/handoff.md/json` |

共同代码基线：`662f821e`，精确 SHA 以 `setup.json` 为准。工区使用该提交的稀疏工程 checkout，不含 ROOT 未提交的 M8 实现、不复制 companies、历史 .planning、环境、模型或 CodeGraph 库。各自计划位于 `docs/plans/w22-atomic-io-2026-10-30/` 与 `docs/plans/w22-pdf-deploy-2026-10-30/`。卡的完整副本在各自计划 `TASK_CARD.md`。

## ROOT 的接线责任

1. ROOT 在两卡交接前不修改上述独占实现。两作者都不得改 M8 来源策略/选择器/QA/actor、缓存/LLM/RF/FF、全局技能或共享 PWF。
2. ATOMIC 不启动真实 SDK，也不修改 PDF 部署工具；DEPLOY 不修改 shared atomic/gate 或 W21 的 runtime/worker/environment 实现。二者不读取对方在途工区，不需要相互等待。
3. ROOT 主线继续原生阅读与摘要；真实增强 SDK 测试这一资源由 DEPLOY 单一负责，ROOT 不同时启动 SDK。测试结束后释放进程并在交接注明。没有收费 API 或新文档下载预算分配给这两卡。
4. 作者按各卡 A/B/C 自行推进，不需逐阶段 ROOT 签收。C 交接前必须调用真正独立 agent 审查完整度、设计、差分、测试与资源清理，修完范围内问题再复审。独审不可用或实测未完成就如实报告，不作者换名自签。
5. ROOT 核对最终实现提交与独审绑定字节，再各做一次必要短域验收。ATOMIC 先集成（共享基础设施），DEPLOY 后集成（工具/部署配置）；这是合并顺序，不是施工依赖。保持现有测试断言和 CI 范围，不新加庞大门禁。
6. DEPLOY 的新配置仅用于该卡 owned 验收；ROOT 在主线集成时显式选定部署配置，才跑 canonical C2、主线摘要/缓存/RF。作者不得自行改生产配置或把合成转换成功当 M8 召回/公司预测通过。

## 简洁交接接口

每张卡的 `handoff.md` 给人读，`.json` 给 ROOT 检查；schema/必需字段在独立卡内完整列出。包含实现提交、最终代码 raw/LF SHA、实际测试与命令、独立审查目标和报告、清理与磁盘收据、范围内 OPEN、PARTIAL 和未运行事项。不要求人工授权 JSON、审批签收链或逐节点报告。

作者正常提交并推自己的分支，不合主线、不安装全局技能、不改他人工区。ROOT 负责集成、当前版本回归、精确远端 CI、共享 PWF 更新与后续真实业务验收。

## 后增独立试验 W23-XIAOMI-OCR

用户另要求比较新OCR，新增[独立施工卡](W23-XIAOMI-OCR.md)和[调查依据](W23-SOURCE-NOTES.md)。工区 `C:/Users/郑曾波/Projects/company-wiki-w23-xiaomi-ocr`，分支 `codex/w23-xiaomi-ocr-20261030`，setup见[W23清单](W23-setup.json)。仅新增 `tools/ocr_comparison/` 与专属测试/PWF/delivery，不改任何生产src、W22两包owner或ROOT M8。可独立开工；重型测速记录主机负载，与W22 SDK实测错峰，繁忙时先做轻量工具/测试，不把竞争造成的延迟当模型结论。

这不是W22第三卡或生产OCR切换。当前CPU RapidOCR与小米page/region、原生提取控制分开比较；固定真实样本/gold、版本与资源界，最终独立agent全面审查并修复后交接。ROOT在比较结果接收后决定是否另在阅读抽象层接入，未经试验不替换生产。
