# DU10-ET-TXT-FIDELITY — 电话会文本抽取与定位保真

## 工作区与目标

- 仓库：`C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts`
- 独立 worktree：`C:/Users/郑曾波/Projects/earnings-transcripts-du10-txt-fidelity`
- 起点：`main` / `7d06777e250ee3f7ae58f0be2cee62944bd2c104`
- 建议分支：`codex/du10-et-txt-fidelity`
- PWF：`docs/plans/du10-txt-fidelity-2026-10-17/`
- ET 主树现有 `.workbuddy-ai/`、`eval_results.json` 未跟踪文件保持原样；在独立 worktree 工作。

目标是验证并修复 ET 已下载 TXT/JSON/HTML 转写文本被解析时的内容、说话人和段落边界丢失，使 CWP 可从原语言文本形成可靠叙述摘要。此前 DU9 的旧算法兼容与性能改进已经验收；本卡不重做 comparator，也不能把字节相等当作语义正确。

## 范围与保护边界

允许读取并在必要时修改仓库根目录 `transcript_extraction.py`；新增测试仅放 `tests/test_du10_transcript_fidelity.py` 和 `tests/fixtures/du10_transcript_fidelity/`；新增交接只放本卡 PWF。`transcript_tool.py`、下载/provider/HTTP、预算/限流、翻译、CWP、FF 均只读。不得引入翻译代码或自动翻译字段。

检查实际导出接口后再定测试入口，不假定函数签名。优先复用已有 parser/locator，不复制旧 parser、不建第二套抽取框架。允许极小合成 TXT/HTML/JSON fixture；真实本地转写只读验证，不复制整份生产文件、不提交 raw transcript。没有可用真实样本就明确写 `NOT_RUN`，不下载补样。

覆盖缺口至少包括：管理层陈述与问答分界、说话人标签/角色与相邻文本绑定、多说话人连续轮次、中文/英文或中英混合、标题/免责声明/主持人过场、缺失 Q&A 标题、换行/标点/时间戳、截断与畸形输入。每个定位都能回到原始行/片段，正文次序稳定；文本不翻译，原币种/期间/口径字面不被 parser 改写。

## A/B/C 节点

### A — 基线和行为 RED

冻结 main 的源码 SHA、现有 DU9 goldens 和相关测试结果。挑选小型输入，先写会失败的行为测试并保存 RED；以实际 parser 输出与原始行逐项比对，识别丢失/错绑/重复根因。

### B — 最小根因修复

只在 `transcript_extraction.py` 修复有证据的问题；保留现有版本/hash/标题/compatibility 契约。新增回归只针对真实根因，旧 goldens 必须继续匹配；按仓库实际指令运行必要 lint。

### C — 完整样本和恢复清理

运行本卡全量专属套件、已有 DU9 比较套件及必要相邻 ET 回归；最少验证一个中文和一个英文来源样本（若已有本地样本），记录覆盖分母和未测项。故障/截断路径不生成貌似完整 transcript。结束后精确删除本卡 owned temp 并核对原始 TXT/JSON SHA、ET 主树未跟踪物不变。

## 独立最终审查与交接

作者冻结最终 HEAD 后，必须由不同 agent 审查代码、测试、原文定位、角色/问答边界、翻译未引入、旧 goldens、目录保护和 PWF 完整度。所有发现修复后，审查员按最终 SHA 再审，报告须 `PASS` 且零未解决问题；否则不交接。独立 agent 不可用时保持 `IN_PROGRESS`。

交付完整 commit、PWF、`handoff.md/json` 和小型 receipts：最终文件/SHA 清单、RED→修复→GREEN、golden 比较、覆盖分母、真实数据是否运行、清理/原件保全、独审 reviewer 与所审最终 SHA。无真实样本时可以交付代码测试，但须把真实泛化结论标 `NOT_RUN`，不能声称完整语义覆盖。
