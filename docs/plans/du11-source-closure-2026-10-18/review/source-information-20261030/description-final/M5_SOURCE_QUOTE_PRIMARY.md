# M5：保真来源卡优先，而非继续堆提示词

## 证据与决定边界

真实 /7 已生成20条/8任务，但独审仍4P2/2P3：问句关系混入公司回答、报道事项扩大、拆条丢报告来源、常识阶段解释冒充原披露。输入角色、合法引用和有限程序诊断均不能证明改写蕴含。因此先比较现有 /5 完整support引用卡路径；本文件记录有界实验及后续接线，不宣称已切全局生产默认。仍一个共享引擎/阅读策略，CWP只管来源资料，下游RF/StockWiki负责研究解释。

## 已完成与下一步

1. 来源准入8个业务检查点已恢复，selection仍partial；不回到全PDF重复解析。
2. /7原响应精确恢复170748B和原generation，正式Store恢复/公共读取/同run及跨run0POST通过；原AUTO历史未恢复，原失败记录保留。
3. /5离线8完整quote/5719B、8gold全部原词保留，19限定测试通过；没有模型完成/正式产物声明。
4. **下一步**：已完成：使用实际配置MiMo mimo-v2.6-flash，在同一已锁IR原件与8gold上只跑一次显式/5完整正式链；50k tokens/$0.05上限，母账沿用当前10M/$20含unknown，保存prepare字节和generation，验证activation_pending恢复及同/跨run零重复POST，独审每卡support/context/归属/限定。该调用是方法比较，不是付费重跑工具错误。
5. 实验已独审通过（8完整support/独立context/0新增关系数字，6272tokens/$0.001076）；正在TDD决定quote-primary的新请求模板选择及旧batch缺省resume兼容；旧/4/6/7产物与历史请求按原版本读取，不能静默换版本或伪造旧generation。模型rank只辅助排序，不能删除合法卡、替换文字或增加数字。无模型生产路径若另需，必须明确程序producer/版本/缓存身份，不冒充真实模型。
6. 在另外A/H/US实际保存源上复验完整引用、归属和长文本整卡defer；不靠公司词表/额度提升。context必须单独可见，引用仍仅为来源陈述，不是外部真值。partial/uncertain/needs_review只是诚实资料标记，不增加人工许可。
7. RF已独审可选summary-use血缘接线另行发布；寻找同公司同来源真实native模型（中微H1已有候选），以经济理由绑定实际used parameter/formula，正式计算与快照，独审采用，不拿单纯context read或挂来源ID当采用。数字假设需要独立依据，不能由定性quote证明精确数值。

## 大节点验收

A：方法实验+真实内容独审；B：生产选择/兼容短域+独审；C：真实缓存和RF数值链/新holdout。小节点不新增签收。保留原件、配置、RF三WIP/147output和外来hook；不碰外包工区、Dayu/IQS/Dashboard，不创建第二数据库或授权文件。

## 未完成

/7四P2未因引用式方案自动销号；等待正式新路径证明。生产默认仍/4。RF实际采用、W21 canonical SDK C2/长路径、US RPO、跨市场holdout及完整八步公司循环仍OPEN。
