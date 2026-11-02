# R7 RF 发布小补与快速反馈收口

状态：**6文件冻结，待独立增量审查，ROOT正常提交/推送**。基线 `a922305a87e6e5014edcceb4bc394c5b56a3d35a`。原已审29文件与四份 assurance WIP 前后SHA均完全不变；本作者没有 Git写入、生产配置/原件/模型/全局安装操作。精确6文件SHA见同名JSON。

## 根因与改动

正常发布首轮 **84.924s**，pytest **689P1F1skip / 73.53s**（另36 subtests通过）。唯一F把 `register_publication` 新建的 v2独立索引行误当作v1链，期待合法重排必坏。运行时已经按R7自足结果/可重建索引设计正确，不能为了旧oracle恢复全局链许可。

测试现明确分代：v2重排后 audit/lookup仍完整保留两个confidence generations及各自result SHA；显式构造的历史v1链原本可审，重排即拒；v1/v2任一真实行数据篡改而未重算hash均拒。旧反控没有删除。没有修改已审 publication_registry/revenue runtime。

另一共因是“本地smoke”不断追加整文件，实际膨胀为原41文件、约690个行为case，并重复执行commit刚做的mypy。本地默认现在只跑Ruff＋**12个固定已有节点**，覆盖SourceRef默认入口/复用/错误ref、来源record、完整forecast/源绑定/未来信息/单位、强publication回放及伪造output。无AST选测、全仓clean许可或新签收。`local_fast_pass`只代表这12项。

原41文件行为集逐项原样保留为 `CI_TESTS`，`SMOKE_TESTS`保历史alias；workflow显式 `python tools/pre_push_gate.py --ci`，仍运行Ruff、public-contract mypy和完整行为集。没有从CI删失败测试或抬timeout。作者仍应运行变更相关测试。

子进程继续清掉父Git hook的仓上下文；新增真实独立子Git仓测试，不只对源码字符串断言。测试子进程禁dotenv和host signer，避免工程检查调用用户配置的签名服务；不改生产配置或实际签名真实性规则。

## 实际验证

- 策略/原唯一失败真实RED：**7F2P / 24.63s**。其中collect-only量到旧表696项（新增元测试使数量变化），不是重跑696；同时证实旧默认重复mypy、workflow无CI模式及未区分全表。
- 仅registry＋选测计划＋Git环境必要域：**38P / 10.10s**。包含真实main调用计划、完整CI表/类型检查仍保留、子失败仍阻断、unsupported flag不是skip、真实小集合收集、真实独立Git环境。
- 正常宿主真实默认CLI：Ruff绿，**12P / 2.23s**，完整调用 **8.931s**；临时根内gate自己的TemporaryDirectory已清完，余项0。此单次观察比旧84.924s显著缩短，不能许诺每次固定8.931s。
- 4个改动Python AST可解析；全Ruff由真实默认CLI执行通过。未运行 `--ci` 全集或远端CI，也未重复旧29/690域。

命令、原失败publish日志原文/SHA、新RED/GREEN/真实gate日志、原41表和新12节点、四WIP前后SHA都在同名JSON。旧失败记录保留，不能用新快检冒完整CI通过。

## 交接与清理

ROOT只需独立审本6文件增量后正常commit/push；workflow已明确CI全表入口。Owned `C:/Users/郑曾波/Projects/company-wiki/tmp/r7rff` 初始absent，证据归档后精确校验绝对parent containment、root/后代无reparse，仅清理该目录：46文件/67,154字节，exists_after=false，恢复初始absent；实际收据见JSON cleanup。不清理Dashboard/output或不归属临时文件，不让原assurance WIP进入提交。
