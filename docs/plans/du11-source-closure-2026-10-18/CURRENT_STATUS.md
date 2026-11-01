# 当前项目状态 — 2026-11-01

**当前在P3药明康德W12完整公司复验。P0–P2有界工程已通过；W12新暴露的配置与恢复共因也已修复、独审并正常提交，H1摘要真实成功，跨run缓存共因已修、真实1token请求复用旧产物0POST且独审通过，正在正常发布。全项目和公司研究循环尚未完成。** 唯一入口为本页及[机器状态](CURRENT_STATUS.json)，接手看[HANDOFF](HANDOFF.md)，实施看[task_plan](task_plan.md)，完成条件看[MAINLINE_LOOP_GOAL](MAINLINE_LOOP_GOAL.md)。

| 节点 | 当前结果 | 真实边界 |
|---|---|---|
| P0 CI | 原3例frontier/lookahead及后续3例版本合同均已根修，CWP精确CI41264855167成功 | 正常commit仅静态检查；pre-push保留32已知文件＋smoke/180秒，部分保护不保证所有远端错先被抓到 |
| P1新版来源 | 华利15完整卡/12业务原子；Berkshire73卡/10业务原子；各1配置POST，激活/同跨run缓存0重复，独审PASS | /5是完整原文卡＋advisory排名，不是生成式概述；Berkshire15项未处理、全文partial，已曝光样本不是盲测 |
| P2实际采用 | 新a466 artifact完整t3出处/理由真实进入华利RF参数/公式/报告/snapshot，v6独立45检查PASS | 条件工程算例，2023IR不是2026新指引；完整公司买方研究未签收 |
| P3 W12 | 11源事实继承、Sina三表、IR两新deck真取得/全页读；配置/恢复根修96unit＋4integration＋8独立探针、0OPEN；H1摘要已完成、5条RF参数草稿真实采用；跨run缓存根修真实GREEN/独审PASS；RF实际链/作者v2引用修正进行中 | 完整RF/报告/snapshot/四路审查尚待实际结果，不能用免费预检或工程绿代签 |

## 本轮已发布与新提交

CWP运行/test基线f98dd54b已远端，[精确CI41264855167](https://github.com/zhengcb81/company-wiki/actions/runs/41264855167)成功，正常pre-push651P/133.64s；后续a8973eaf仅PWF。RF main/远端85054d7b，[精确CI41260918155](https://github.com/zhengcb81/revenue-forecast/actions/runs/41260918155)成功；运行根修535604fa已同步3逻辑技能入口/2物理目标、重复零写和3新进程通过。后续docs-only HEAD不另造运行CI。

新CWP运行提交ce1a603a已通过正常ruff/mypy/config doctor；正常push781P/108.09s已成功、精确CI41267979696于03:12:48Z成功，W12真实链并行，不新增逐小步许可。新[配置/恢复共因验收包](review/mainline-closeout-20261031/p3-config-recovery/README.md)只有约32KB gzip收据，不归档PDF/整库。

## 为什么W12还需要根修

显式传同一canonical配置跳过受管dotenv，误用继承MiMo凭证，造成两次401；修正调用后又被“usage必须known”永久挡新run。现配置层按resolved文件身份统一加载；AUTO run store在同一只读snapshot判断执行/输出/交付是否结束，batch薄适配。已完整失败可显式新run，旧unknown费用不退；未结束/crash/付费pin和待交付仍走原恢复。局部正文诊断SHA不是完整pin，不因此重造死锁。真实失败、错误测试期望和中间实现错误均留证；独审0OPEN，不签W12新结果。

## 唯一下一步

正常发布当前缓存共因根修并核精确CI；与此并行完成W12作者v2正确引用版本的完整RF链/封存，再派四路fresh独审，按共因修复源D&M遗漏/研究幅度依据等实际问题，质量/检测收尾。不扩包。

[缓存根修](review/mainline-closeout-20261031/p3-cache-reuse/README.md)已通过当前source重选＋完整material证明，真实新run/max_tokens1复用旧exact91d5/54ccb...、0新POST/预留/费，12.24s含本地选材/locator。所有旧账、两旧artifact及partial标记不变。137短域/7最终unit/16宿主验证（范围重叠）及独审实际wire重建通过；正常发布/CI后续单列，原失败不抹。

RF新summary的5条used参数已真实采用，主计算/报告/snapshot与同DAG联动stress实际执行；幅度支持诊断仍unsupported，不作经济PASS。executor在封存前发现自身3条Testing引用错落同页TIDES段，保留v1字节并起v2纠正，非改产品取绿。p11 D&M关键段未入summary的召回缺口、研究依据/校准等仍待四审和共因修复，不能用raw补证假写摘要完整。

保留asof2026-10-21，capture/checked用真实Nov1。初始复用0下载；后来通过官方公开UI找到H1/JPM两deck，CWP原生取得、RF登记、21/19页实读，封面/索引/内容定稿日期分别保留。Sina当前snapshot及单位/PIT未知不冒历史可得；Q3publishedOct26排除。GLP1项目份额/外部市场规模不冒公司销售/收入目标，分部subscope不重复相加；原native discovery partial及unsupported callgap保留，不能称无公开材料。

预算配置累计10M tokens/$20，最近已核母账1,955,397tokens/$0.760197（估计非账单），含new_unknown8＋prior_unknown7；两次401保留85,927tokens/$0.017053，纠正loader后的首次native拒绝0新POST/预留。executor新调用以实际native账更新，不能退款/重置。

不扩施工包，不动Dayu/IQS/Dashboard、原件/生产config或外来WIP。W21 canonicalC2、新US监管/HK/US_RPO及长文未处理余项仍按相关P3责任，不由nativefallback/股东信代签。此前自有测试目录清16045737B＋失败hook21158851B，本节点再清18856387B；真实P3当前数据待四审保留，不能提前清。外包只看[PACKAGE_STATUS](PACKAGE_STATUS.md)，目标active不暂停。

旧两次401及一次cache额外POST均为保留历史；最新缓存真实GREEN如上，不用新通过覆盖旧失败。当前仍不新增LLM生成，executor免费完成正确引用v2链并封存。
