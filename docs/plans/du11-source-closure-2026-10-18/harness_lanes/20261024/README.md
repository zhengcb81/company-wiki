# 2026-10-24 三张可同时开工的独立施工卡

> **交付状态（2026-10-24）：** 三卡已完成ROOT接收。W13采用有界策略适配、待本批CWP push后的精确CI；W14已进入RF主线并推送；W15已进入Audit本地main并由ROOT修复可移植性问题。详细状态见[ROOT接收总记录](../../review/package-reception-w13-w15-20261024/README.md)和当前[dispatch](dispatch.json)。本页后续原始说明为发卡时快照。

总控唯一入口：[CURRENT_STATUS](../../CURRENT_STATUS.md)。本批**只有三张卡**。W09/W11已交付，不重开；W12最终公司审查仍归ROOT。这批解决测试等待与可复现性，不代签annual14内容或公司PASS。

| 卡片唯一正文 | 独占工作目录 | 交付目标 |
|---|---|---|
| [W13-CWP-GATES](W13-CWP-GATES.md) | `C:/Users/郑曾波/Projects/company-wiki-w13-gates` | 日常push只做有界快反馈；全量单测留在完整本地模式及远端CI，失败如实回传 |
| [W14-RF-CLEAN-CHAIN](W14-RF-CLEAN-CHAIN.md) | `C:/Users/郑曾波/Projects/revenue-forecast-w14-clean-chain` | 改造既有RF三仓离线E2E，去掉生产湖依赖、旧人工门和固定源码许可pin，真实子进程可移位复现 |
| [W15-AUDIT-PORTABLE](W15-AUDIT-PORTABLE.md) | `C:/Users/郑曾波/Projects/revenue-forecast-audit-w15-portable` | 工程工具按显式清单导出必要采用证据，搬家后调用现有join CLI回放，保留差异和unknown |

给每个harness：进入指定工作目录，完整读本卡及[共同接口](INTERFACES.md)，再读自己 `docs/plans/<PLAN_ID>/START_HERE.md`。设置卡内PLAN_ID/PWF_PLAN_ROOT；按A/B/C一路实施。**不等ROOT签A，不逐小步索取许可。交接前必须实际调用未参与实现的独立agent全面审查，修完全部内部发现并对最终代码复审，才能交接。**

## 为什么能并行

- W13只写CWP测试调度/hook及其专属测试；ROOT继续写CWP来源/选材/摘要业务代码，不写W13调度文件。
- W14只写RF既有E2E入口、专属support/测试，不写RF生产消费或研究模型，也不写FF/CWP。
- W15只写Audit工程工具/专属测试，不写W10生产join、EvidenceReader、SKILL或中央运行树。
- 三个工作目录不同。W14读取FF/CWP时必须从冻结Git对象部署到自有scratch；ROOT母仓后续改动不会改变其输入。无共享数据库、费用账或可写测试湖。

## 总控接收顺序

各包可独立完成；ROOT逐包核对交付版本、独审及测试清理。先并W13，然后W14，最后W15；组合时再把W14接到ROOT届时最新源码，W15接到新的真实矩阵。遇到跨边界产品缺陷写具体 `interface_requests`，不越界补丁、不把未运行算通过。ROOT拥有最终跨仓验证、技能定点同步和主线推送。

## 工作区和资源

实际基线、分支、启动文档及交接路径见[dispatch.json](dispatch.json)。独立worktree共用Git对象，不复制生产湖/venv/安装技能。W14的tracked旧`.planning`约806MiB只在**新worktree**使用sparse checkout省略，原RF工区和Git对象保留；不要关闭这个省略再复制旧运行树。所有包0模型/供应商网络/原件下载；Git推送仅发布自身codex分支。Audit当前无remote，提交后按无remote如实交接，不虚构推送地址。

交付只保留代码、少量夹具、必要日志和最终收据，目标每包≤16MiB；大日志去重，不打包生产PDF或整棵run。新临时测试文件完成后精确清理，复核测试根原有文件不变。作者不得清理既有主工区未提交文件。

这些文档是工程分工说明；不添加生产授权JSON、人工签收、hash许可表或新的运行门禁。
