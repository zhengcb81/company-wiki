# W20 施工卡最终独立复核 v2

**APPROVE：三卡可分发并行，本批范围 OPEN=0。** 仅施工卡完整度/边界审查，不等于三个实现已完成或生产验收。已审最终五文件精确 SHA 见 `report-v2.json`；初审两项发现保留在 `report.md/json`。

- F1 已修复：FF R7 冻结 CWP `618df929ffa889424b3346d5299d67b9b1c72709`，ET 在 A 解析后绑定完整已提交 commit。只复用 DU10 **构建方法**；只有 manifest 与本卡冻结 commit 一致才可复用现成视图，明确旧 CWP `900dbf648...` 不能冒充新版本。否则按固定 commit 用只读 archive/show 建必要源码视图，owned 临时状态、同批一次准备、实际 module/SHA 与清理收据，不能绑定 ROOT 可变工区。
- F2 已修复：FF R8 区分 supplemental/partial，记录 selected/completed/skipped；原 mandatory 41-case authority 不缩小，不能改 `required_cases` 分母冒 full PASS，未跑范围 NOT_RUN。现有矩阵 owner 可扩展选择/故障演练，没有新状态库/第二矩阵或额外审批节点。
- 其余初审结论不变：不同 repo/worktree/allowlist，无卡间暗依赖；AUDIT 保四角色与问题 context；RF 只按实际引用链观察，不由摘要存在/词相似推采用；FF durable 后零额外下载是可观测目标，不承诺未 durable 的 exactly-once。复用 W17、DU10 和既有 provider，不重复 W19 三表工程。
- 每卡 A/B 自主推进，C 集中必要短测、真实 CLI、独立 agent 全面审查、修复与复审后交接；实现/受测/独审 commit 和文件 SHA 绑定，无每小节点审查。

本次最终复核只读重看新增 R7/R8 与五卡文件 SHA，没有再读跨仓工区、没有运行矩阵/测试/SDK/模型/网络，没有修改卡、产品、PWF、Git 或其他 owner 文件。主工区 WIP 与三个隔离工区事实沿初审有界只读记录，不把它们假称本次又执行验收。
