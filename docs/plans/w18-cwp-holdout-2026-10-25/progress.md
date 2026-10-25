# W18-CWP-HOLDOUT Progress

## 2026-10-25 ROOT seed

- 新建独立工作树，HEAD绑定ba8f8543c0351f6857e1ce24e943ad9da1b664ef；代码/测试没有改动。
- 本目录保存完整施工卡、共同接口、模板和PWF，不依赖其他harness的施工。
- A/B/C均未执行，产品测试/真实样本/独审结果均NOT_EXECUTED。
- 下载0、模型0、API0；未复制原始库；只提交本目录文档seed。
- 下一步A调查与冻结预期，然后自主B/C，按COMMON最后独立审查并修完所有问题。

## 2026-10-25 A节点：manifest+源侧gold冻结

- 逐源阅读8原件关键章节（海康DOCX与百济IR全文，其余有界窗口，阅读范围记录于manifest）。
- 96目标/113锚点全部通过schema校验与独立重提取锚点验证；未运行任何候选选择。
- manifest（版本化SourceRef+身份证据+prior_use+阅读范围）与8个gold冻结提交；本机bindings.local.json不提交。
- 模型0、下载0、网络0；主仓companies/只读，未写生产库。

## 2026-10-25 C节点：真实冻结baseline回放完成

- ba8f8543 只读分离worktree部署验证通过；隔离湖登记8原件+8边车（bootstrap.json）。
- 两个attempt完整保留：observe-only（113758Z）与observe+compile（144804Z），8/8样本ok，原件前后SHA不变，零POST/零下载。
- compile 6/8成功；招股书parser_incomplete与海康DOCX语言抽取失败保留原始原因（F1/F2）。
- 机械可见性10/96选中、16/96入模型输入、73/96两者皆无、0锚点页未读；DUB评估8 PASS/41 FAIL/22 PARTIAL/25 NOT_EVALUATED；96目标全部not_reviewed。
- CLI级双根（ASCII/中文+空格）外部cwd重放ok，污染PYTHONPATH decoy被拒（rootC failed）；收据delivery/w18/recovery-receipts/dual-root-receipts.json。
- 逐目标finding见delivery/w18/findings.md与baseline-summary.json；产品缺陷F1-F4交ROOT，不在本卡修生产代码。

## 2026-10-25 独立审查修复轮

- 三agent审查结论：gold审查PASS_WITH_FINDINGS（113/113锚点验证、1×P2+5×P3）；工程审查PASS_WITH_FINDINGS（H01-H11全PASS、6×P3）；独立重放验证PASS（重放逐字节确定性、失败/清理/不覆盖链、双反例词匹配不代签）。
- 修复（351ba6ae）：gold v2（F1禁令方向反转/不再增设无锚句依据的禁令、F2引句补全、F3五处锚点扩展或同伴锚、F5恢复原文措辞、F6真值对照移出禁令串）；v1 oracle逐字节归档gold/archive-v1/；corrections逐项源侧理由gold_corrections.json；manifest v2（gold_sha256+gold_version+紫金prior_use补FC-504 sighting）；工具D1-D6全部修复+2项新测试（20/20全绿、ruff 0）。
- attempt-3（gold v2，冻结ba8f8543全链）8/8 ok：机械可见性10/16/73/0与DUB 8/41/22/25与v1完全一致——修正为oracle正确性卫生，未改变任何判定。
- 最终SHA 351ba6ae已回传gold审查与工程审查两agent复审。
