# GP后续10项与原痛点对照

2026-09-06。GP计划曾把原117项之后缺口认定为部署/自然时间；本审计的反证表明仍有产品与验收门缺陷。此表保留真正推进，不把后续限定“提交申请”当作已经生产完成。

| 项 | 已解决的范围 | 原痛点仍存及判定 | 证据 |
|---|---|---|---|
| GP-001 | artifact_handle当前拒绝空sourceSHA、producer写sourceSHA，这是实质修复 | PARTIAL：未本轮核49历史产物实际拒绝；绑定读取/journal未贯通，不能证明可信复用全链 | wiki-audit W03，原GP记录A1/A2 |
| GP-002 | v2 scanner有生产flag接线，非仅一个adapter helper | PARTIAL：其他resolve/ensure/close-gap仍默认v1，严格RootPolicy3 loader未统一；v2扫描不等于完整v2消费 | filing-audit ZR401/402/404 |
| GP-003 | SQL receipt/sourceSHA/privacy筛选、禁止研究输出门已生效 | PARTIAL：TTL/当前policy/normalized bytes终检没接，注释错称readiness已保护 | wiki-audit W05 |
| GP-004 | 87收据格式重签、旧legacy备份是历史行为 | PARTIAL：改canonical绑定不证明独立重审；FC903 rawSHA不匹配；证据valid与accepted分离 | filing-audit F-F08、assurance A02、独立复核 |
| GP-005 | registry已有197/197passed和测试映射 | CONTRADICTED（全场景完成）：197 fixture/oracle均缺失，按status跳过旧结果，T1映射不能替T2/T3/T4 | evidence-inventory、assurance A03 |
| GP-006 | Windows sibling job及9个临时fixture测试接入 | PARTIAL：continue-on-error:true、真实roots明确排除；不是原阻断真实roots CI | quality.yml、assurance A06 |
| GP-007 | owner后来决定生产roots全public，privacy字段升级确有变更 | PARTIAL：原schema3.0升级与当前生产1.0/2x loader不一致；public决策不撤销，但严格未知权限合同/doctor尚需闭合 | filing-audit ZR401、wiki-audit W05 |
| GP-008 | 9/5新commit已修注册器参数run-daily，已有新run/period2 | PARTIAL：实际Action/自然触发来源未核实；only SQL代理；R9窗口close_allowed=false。不能再说参数仍坏，也不能只等时间 | daily_manifest、legacy_periods、assurance A04/A05 |
| GP-009 | daily/weekly注册声明和调度代码存在 | PARTIAL：7/2/1/1未满足；未见weekly/monthly当前manifest；停跑告警/正确required skip/生产soak入口未闭 | assurance A05、probe-results-extended |
| GP-010 | 申请后批准，normalized7/7、review7/7、summary6/7、sections5/7已有历史真实记录 | PARTIAL：2列表式未提取；安全拒绝保持；752候选/214写入越过7份cohort的执行门缺失，owner事后保留不修门；非真实worker需求链 | wiki-audit W08/W09 |

## 与现有v5的关系

v5仅是既有隔离计划；本轮不改它、不合并主线、不恢复worker。后续总修复计划会引用v5的性能合同作为输入，但必须重新冻结版本和审查；H01自动prune、P06安全外发、持久queue均是worker恢复前置，不能只做SQL提速后启动后台。
