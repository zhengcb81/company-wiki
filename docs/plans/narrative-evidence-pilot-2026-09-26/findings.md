# Findings：当前事实与证明范围

**2026-10-08｜R3生产与R5完整审计/发布完成。** 当前状态取[task_plan](task_plan.md)；历史完整调查在[6dd5601](https://github.com/zhengcb81/company-wiki/blob/6dd56011a7d49e2b8c147f2163b0708074f9edd7/docs/plans/narrative-evidence-pilot-2026-09-26/findings.md)。

## 架构与精简

来源层负责raw/版本/SHA/locator/质量，消费者通过pathless SourceRef/Export v2/NarrativeRef读来源，不操作底层目录。CWP不保存投资研究state；RF/StockWiki各负责自己的语义。一套AUTO、独立模型子进程、有界多文档P4，不重造reader/队列。G2十四组及A/B全发布：人工许可、review receipt、签收、private/public、canary、固定SHA人工许可表退出；保留真实SHA/身份/期间/历史公开日/locator、路径归属、事务与资源限制。[完整对账](r5_full_closeout_2026-10-08.md)。

## R3真实生产

既定正式请求r3-20261008-production-deepseek-01成功：微软原语言TXT106792B final、真制度1457B skip，只有1实际DeepSeek POST；20claims、49原文证据、16管理层/4分析师问题、13actual/3forecast/4question。所有claim逐条受引用支持；六个重点经营主题均在短摘要，仍非全文穷尽质量声明。原件provenance legacy_unverified和未知公开日期没有被伪造。[生产](r3_production_acceptance_2026-10-08.md)、[语义](harness_lanes/results/r3_production_semantic_review_2026-10-08.json)。

真实CLI首次暴露nullable采集时间、登记语言被误当身份冲突。三个读取层现保持未知原登记值和独立派生语言，不依靠新开关或来源白名单。有值错误/已知冲突仍拒绝；显式null当前阅读与ISO历史公开日规则分开。三仓公共read/list/search/exact、49定位、同证据DTO与制度skip都通过，历史unknown均拒绝。同run恢复6任务终态、0新attempt/POST/token/费用、相同工件/hash。[总收据](harness_lanes/results/r3_production_acceptance_2026-10-08.json)。

累计199534tokens/估算110737microUSD；220000/$10已授权，余20466tokens/9886499microUSD（扣旧FX2764），历史unknown7不退。既有DeepSeek/MiMo配置、价格与资料范围不变，现金账单未知。不会为消费重跑付费摘要。

## 空间与归属

历史S5/S6生产净释放5659443210B、raw0、DB222408704B。新R3主DB不增，仅WAL+57680B、AUTO389120B/SHM32768B、两个final108249B、work212B及锁1B，共588030逻辑B；CLI内部报588029B，差1B为owner lock。scratch峰106792B。当前每final2MiB/持久1GiB/scratch2GiB均通过，实际allocated未知。[测量](harness_lanes/results/r3_production_space_protection_2026-10-08.json)。

R5A清8根119913476B；R3A清工作树91161217B；本次R3清自己2工作树+16文件94840547B。三项是测试/代码副本，单列不重复加到旧生产净释放。26原件/config/侧录/历史pilot SHA保持，formal AUTO/成功final与未知费用历史保留。邻仓owner只能检查归属不覆盖：StockWiki独立交接提交753dfca/6d1dddb并清自己runs；旧342基线不能再宣称全未变。我们的四消费者提交只改接口/测试，与owner不重叠。SID/SQA等独立WIP保留，Dayu/IQS0写。

## 有意保留的边界

S7九原件仍29/33/761定位零错、optional2/17、重复6。四miss是纯金额、另页canonical产能定位、正文外provider、纯guidance，原golden/分母保留；不称33/33。R4实读重复extra34.5MiB/allocation未知，证据决定不对象化。FMP真实402只证明当前套餐限制；Koyfin/SeekingAlpha调查不等于自动化provider或购买。P4计算3/模型1，不称实测四模型并发；Windows POSIX skip不计通过。原scope是有界来源平台能力，不是全历史已处理或投资研究自动化。

## 发布

CWP6cd9b6d精确CI37736338454全success；RF7cf337e依赖当前producer、精确CI37737193724全success；实际消费测试343e2de源码与7cf相同。SW1ebe012被独立6d1dddb推进，consumer源码逐字相同，无远端。[八仓只读状态](harness_lanes/results/r5b_final_repository_state_2026-10-08.json)。最终文档检查点34141d3d已推送、实际远端相等、CWP干净，最终状态提交复用这些源码绿；关闭原目标。
