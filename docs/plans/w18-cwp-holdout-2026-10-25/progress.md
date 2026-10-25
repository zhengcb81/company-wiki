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
