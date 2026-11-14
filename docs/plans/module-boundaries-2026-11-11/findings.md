# 调查发现

## A1逐仓审查与接收（2026-11-11，历史）

完整结果见reconciliation.md及review/repo_reconciliation_20261111三份逐仓报告。范围8仓390分支/remote refs、253工区，另7RF tag和2CWP stash。最重要的纠正是：refs未成祖先不一定漏并（FF job已整合接收）；tracked clean/untracked=0不代表无原件（四个RF Temp仍有msft原文）；release与main确有公开能力差额（RF B37、SW C38/B03、CWP历史CLI），不能说全部已并线。

本轮已受测接收FF明确null发布日期修复与Dashboard边界WIP，均独审、main推送。SID11项WIP的路径子串/跨请求CONFIRMED_EMPTY/空tab全页回退问题已写原卡A0；不直接并入。Dashboard真实stream24-case缺owner入口仍未通过，归CWP T-READ/ROOT组合；静态扫描和mock通过不替代该证明。清理仅限确认测试产物、已吸收副本/空工区/旧生成物，独有账目、原件、业务状态、研究历史保留并分配owner。

## 2026-11-11 初始快照

- CWP HEAD `08dfe8bf1ae97dff34b28976d532b3482d3ba358`，跟踪文件干净；源码最近提交 `54f8b470c` 完成 source stream/parser owner 子节点。
- 父计划 D4/D5 已有局部 ACCEPTED，但 P3 中“所有模块/跨仓 owner 边界”没有有限清单和统一退出矩阵；父计划仍包含更早“全局 ACCEPTED”的完成定义。需要区分历史验收范围与当前全局结论。
- 最新工程证据证明一个 source/parse 子节点，不能代替所有业务入口的依赖和隔离覆盖。
- 本轮只读调查，不执行收费调用、不修改源码、不清理历史运行材料。

三份独立调查已补全，当前静态确认/风险/未运行验证分别记录如下及review/。

## 三路调查归并与采用决策

- CWP已有边界实质有效；剩余共因是消费者依赖protocol未声明的能力、纯类型经具体runtime导入、低层隐藏读配置及实际安装证明不全。CWP-01..05由单一作者覆盖七内部责任，避免多个harness争抢catalog/tests。
- FF已提供WikiConnection/TranscriptTransport/六operation；缺的是全交付形态隔离与请求配置/启动细节的明确归属。测试先行，若已满足则NO_CHANGE_PROVEN，不强制搬目录或创建wheel。
- RF主来源链pathless已有；旧canary随runtime直读上游SQL、core/report聚合依赖仍需收敛。历史B34路径要求是已声明profile兼容范围，不能为可移植性重签旧材料；默认操作不得因此依赖CWP私有布局。
- ET supervisor/provider和worker协议依赖方向需分离；worker固定结果表示帽是静态风险，先RED验证再按实际请求quota归一，不能直接认为已经发生真实生产误拒。
- SID两个同owner根因：fetch丢错误类别/retryable；API反向导入adapter私有metadata。合一张卡修纯domain与typed结果，保留原11项WIP。
- StockWiki/Audit主要公开边界已有，没有为它们强造实现卡。Dashboard两份可见配置使用release code roots与主仓data roots，实际在用tuple尚未核验；不能说主仓缺CLI就是部署坏，也不能覆盖既有4项WIP。
- 新浪三表实际owner为CWP source_catalog/financial_statements，FF是公开客户端；PDF策略/SDK归解析/阅读层。本轮不将金融表移回PDF路径。

三份独立源证据在review/；它们记录静态确认、风险及未验证，完整测试只在后续owner实施和ROOT大节点进行。源清单479项是覆盖清点，不是逐行功能审计声明。

## 避免再次无限收尾

固定boundary_matrix的有限责任项与E01–E09出口；活动入口和交付包覆盖也进入清单。局部测试/代码行数不是完成标准。原主线摘要召回、模型/假设、真实付费恢复与公司循环单独待办，关闭架构后继续。

已有AST规则保留实际越界反例，不继续扩建通用Python解释器。设计本身用pure值、显式依赖、状态单owner、替换实现和无邻仓安装验收隔离；工程检查不变成生产审批/授权/日志大小许可。

## 方案独审发现及修复

1. 原interfaces文字会要求lane等待ROOT新的contract fixture，且仍误称四卡；已改为本仓合同/fixture立即A→B→C，ROOT只在M2选真实组合样本。
2. RF卡原“移动自包含执行包”可能误导作者改B34历史绝对路径身份；已限定历史profile兼容与当前默认隔离，可移动测试只覆盖已声明可移植artifact。
3. 原安装指令不够具体；新增runtime_verification.md，明确CWP wheel、FF/RF canonical installer临时destination，以及ET/SID脚本runtime显式闭包；任何卡不得省略参数同步全局目录。

## 最终方案复核

独立方案复核PASS，全部本轮可行动意见已关闭。安装参数、37个既有测试路径的静态存在已核；没有运行产品测试或实际安装。后续卡完整验收由各owner实施，ROOT最后组合。

## 2026-11-14 继续核查实际边界

- CWP `SourceVersionReader.catalog` 暴露了底层目录对象，调用者也能直接调用读取器内部方法。解析和导出装配把完整读取器交给消费者。导出只使用 `open_version`、`verify_version` 和 `describe_version`，当前运行时却要求解析与流式方法。分别用属性反例、公开读取行为和独立后端证明。
- StockWiki 本地 `master@f2bc73f` 已有 MC-SW 接收的 C38 接口和 B03 assessment。真实主工作区另有 Quick Scan 未提交改动，复验以提交为基线。仍需验证 StockWiki 的 CWP 证明客户端能否使用独立安装的公开命令。
- Dashboard 老测试绕过 adapter，调用 CWP 已移除的私有读取器和锁函数。应该在调用方用真实公开流和已知夹具验证拒绝语义，在 CWP owner 内验证打开字节和事务提交语义。Dashboard 主工作区有另一路正在改动的文件。
