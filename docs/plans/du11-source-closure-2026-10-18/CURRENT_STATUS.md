# 当前项目状态 — 2026-11-01

**当前在P3药明康德W12的r1-remediation-04补偿复验：原3例CI及后续版本合同失败均已根修；前版真实摘要、缓存恢复和RF采用工程链已跑通；来源规则29已独审发布，新规则正式产物/恢复已原生完成，完整RF采用与公司质量仍在验收。完整公司研究尚未通过独审，继续修复共因，不扩发施工包。**

唯一入口为本页及[机器状态](CURRENT_STATUS.json)；接手看[HANDOFF](HANDOFF.md)，实施看[task_plan](task_plan.md)，全部完成条件看[MAINLINE_LOOP_GOAL](MAINLINE_LOOP_GOAL.md)。

| 节点 | 已完成 | 仍有边界 |
|---|---|---|
| P0 CI | 原3例frontier/lookahead、后续3例版本合同和Windows嵌套夹具已根修并独审 | commit仅静态检查，pre-push32已知文件＋smoke/180秒为部分保护，不保证所有CI问题都提前捕获 |
| P1来源/摘要 | 华利15完整卡/12原子；Berkshire73卡/10原子；各1配置POST，激活/同跨run恢复独审通过 | /5完整原文卡＋advisory排名，不是生成式全文概述；Berkshire15项未处理，全文partial，非盲测 |
| P2真实采用 | 新a466 artifact完整t3进入华利RF参数/公式/报告/snapshot，v6独立45检查通过 | 历史IR与条件工程算例，不冒2026新指引或完整买方研究 |
| P3 W12 | 新H1正式artifact；真实1token新run复用旧exact91d5/54ccb，0新POST/预留/费；5条完整出处进入RF已用参数、主计算/报告/snapshot和真实联合压力 | R3/v2已封存、四路fresh独审全部完成。源遗漏共因已发布，经营幅度/反证、旁表/背景事实正于R4复验，未签全公司质量通过 |

## 当前代码与精确CI

CWP master/远端运行版本 **7e10973e**：正常pre-push **1867P/48.92s**，
[精确CI41279280653](https://github.com/zhengcb81/company-wiki/actions/runs/41279280653)成功。
前一配置/终态恢复ce1a603a正常781P/108.09s、CI41267979696成功；原CI根修f98dd54b的CI41264855167成功。历史失败、费用、原付费签名保留；后续PWF-only提交不另造运行CI。

RF main/远端运行8eb8fe08，[精确CI41282340171](https://github.com/zhengcb81/revenue-forecast/actions/runs/41282340171)成功；normal690P/1skip/36subtests/44.89s。新长卡证据两runtime＋说明3文件已定点同步3逻辑/2物理6写，repeat0、3fresh入口实际8卡/519字PASS。旧535604fa/85054d7b作为历史保留。

## 本次共享根修与真实验收

- [配置/恢复共因](review/mainline-closeout-20261031/p3-config-recovery/README.md)：相同canonical配置不再因参数写法漏载受管凭证；执行结束与账单unknown分开，AUTO单snapshot判定。未完成、可恢复paid pin、待交付仍归原run；旧unknown不退。96unit、4integration、8独立探针及独审通过。
- [缓存共因](review/mainline-closeout-20261031/p3-cache-reuse/README.md)：Worker与cache用同一canonical选材服务。快速dependency不完整时，以当前实际材料等价证明复用，不把unavailable当重复付费理由。原partial、generation与账保持。真实GREEN12.2436s含本地重选/原文locator；没有新摘要body，旧额外1POST仍计费。137域/7最终unit/16宿主验证范围重叠，不相加。

W12执行根为audit原run的`execution_replays/r1-remediation-03`；734件/115059812逻辑字节，manifest SHA **6e8051f6…616d8**已逐件核对。active input为authoring-v4，主forecast/main-v2 SHA **d78fcdc6…21b1**，snapshot **ada03b4f…740**。作者v1三条Testing误摘同页TIDES的引用已用新v2纠正，旧字节保留。实际195claim、232参数、主/联合压力链已执行；54个幅度诊断unsupported，不能由计算正确升级为经济合理。

四路fresh审查输入及报告在`revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/reports/r1-remediation-03`，现已全部封存：storage一项P2选材遗漏；process两项P2旁表期间/背景事实血缘；analyst两项P1经营校准/反证；fetch一项P2外部电话会能力缺口，未发现FF路由错误。ROOT已归集73项检查和全部六个原issue，专家已将六原issue归并七根因并交内部实施细则，R4正在执行。记录型coverage声明gap0不代表质量通过；混合说明的locator等机械定位缺口另行分诊，原报告不覆盖。

## 最新来源共因节点与R4

新来源修复已完成同预算真实选材与集中独审：[收据与复现](review/mainline-closeout-20261031/p3-source-scope/README.md)。37新例、698相关例/28.88s、mypy408源/ruff通过，独审268例与本域有重叠。D&M原文完整入选；p14两技术段在519字符native range中逐成员SHA/坐标精确保留，8/8连续、未来限定未丢。旧检查只认单独span造成ROOT误判，已按原生成员复核，不改预算。三rounding独立卡0；112/16M不变，全文仍partial。新代码7e10973e已正常发布并取得精确CI41279280653成功；不冒用c405的旧绿。

四审六issue已由专家归并七根因，实施细则在AUDIT同run/remediation/r1-remediation-03/implementation.md。R4正在真实native研究接线；已原生取得法院原意见、官方会议信息和主办Q&A三源608016B/$0，Q&A公开日期未知、原生资格unknown如实保留，不能改名电话会。旁表/背景事实和实际季度交付桥推进中。已放行按当前配置做一次新版H1正式摘要，实耗以新attempt账本为准；尚无正式经济验收。RF新增monthly_manifest外来WIP保留；不扩包。

## R4当前真实观察（独审尚待）

新版H1仅1次配置MiMo POST：10236tokens/1885microUSD估计，正式artifact `narrative-229074ddf042496d92ebf0959ceb2bab`、SHA `9f014cff0e2ce19dcdb0c186ef4933e91a42e3465df15b99c288b6c63423b2bd`、485241B。实际paid-prepared失败边界随后同request恢复、完成后同run与独立cross-run/max1均native exit0，exact同artifact，0额外POST/跨run预留/token/费。两次测试launcher/observer作者错误原样保留，不冒生产根因；未额外注入activation锁。8卡已actual consume；519字原文触发普通短引用限制后，RF所属证据合同已TDD/独审并正常发布CI成功。当前在新客户时点图上重新consume同artifact以更新实际formula_refs，正式模型/报告/snapshot与新四审未签。

独立专家确认期间补集统一owner缺口，ROOT去公司化10向量先固化4F/6P；当前181参数主DAG不依赖13历史旁表，不在运行中途改RF版本，归原内部PWF第7步补齐。同比倒推须显式比较关系，不能靠放开日期或改annual。

## RF长卡合同与语义分离收口

RF误把完整519字原文卡当500字手工短引，旧说明还要求上层切源卡。根修在RF证据owner：普通500保持，完整adopted quote复用既有128KiB proof界、UTF8及完整source/support/context/原quote/used-formula仍验证，普通路径不import可选模块。11新case、91域/1.77s、独立110项通过（范围重叠），8真卡input原样PASS。已8eb8fe08正常提交推送/精确CI成功/定点3入口native验证，0额外POST。证据在RF/docs/plans/p2-summary-lineage-20261031/review/v7-long-anchor。

法院取消/延期事实不证明净E或永久恢复率，100m只为归一化压力。5个条件支持角色并非新RF缺口；第6个公布日改history_base，不冒未来机制。采用更清楚的无数值source支持假设＋原driver/context反证，旧v1/v2/失败保留；专家只读诊断在AUDIT同run/diagnosis/r1-remediation-04/evidence-role-readonly。P3经济质量仍待四审。

## 唯一下一步

按已发布CWP7e10973e/RF8eb8fe08完成R4新图的同artifact重接、正式主模型及客户时点压力compute/report/snapshot并封存，随后四路独审与原第7/8步质量/检测收尾。期间补集已固化RED，归原质量收尾；不扩施工包，不重复模型。

后续才是药明合联/Snowflake泛化、固定八家公司及同一有效版本连续三家clean；W21 canonicalC2、新US监管/HK/US_RPO与长文余项仍按原责任，不用fallback或股东信代签。来源漏召回不能由RF另读raw改写成摘要完整；未来假设不足不能靠编数字、公司特判或抬额度解决。

## 数据、预算与清理

asof保持2026-10-21，读取/采集为真实Nov1；Q3于Oct26发布故排除。11个既有来源事实通过原owner继承，初始复用0下载；随后H1/JPM公开deck经CWP原生取得、RF登记、21/19页实读。Sina三表为当前snapshot，单位/PIT未知保留；GLP1项目份额不冒销售份额、第三方规模不冒公司目标、TIDES子范围不重复相加；unsupported电话会不冒不存在。

配置累计 **10M tokens/$20**，150k/$1为公司软目标；母账 **1965633tokens/762082microUSD**为估计非账单，new_unknown8＋prior7保留。401两次85927/17053、缓存多一次9773/1808均未抹除。当前四审无新增收费调用。

本节点7个已绑定日志的pytest目录检查后删除剩余 **2003113逻辑字节**；原P3数据待四审后恢复，原件/生产配置不动。只读盘点封存执行包发现54.0%逻辑字节为相同内容重复，尚未清理/改存储；在已有质量收尾中处理，不能篡改已封存证据或宣称已释放物理空间。

不动Dayu/IQS/Dashboard、RF四assurance外来WIP、CWP hook mode。不新增人工许可/小节点签收，不用no-verify/reset/clean。外包仅看[PACKAGE_STATUS](PACKAGE_STATUS.md)，目标active，主线继续。
