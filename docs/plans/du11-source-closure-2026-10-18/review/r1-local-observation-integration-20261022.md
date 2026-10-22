# 本地读取诊断：三仓根因修复与实际联调

状态：**三层已独审并线，RF/FF已推送安装且远端CI成功；CWP正常推送待本节点完成。** [机器收据](r1-local-observation-integration-20261022.json)。

## 修复内容

- CWP的预算owner报告实际阶段、限制、已接受读取与已观察尾块、触发项；失败前完成的操作和诊断跨递归保留。未知旧失败不回填假计量，不把本地I/O当下载/供应商费用。
- 已证实不相关的来源只在本call记忆，避免重复读取、解析日期/侧车；错误文件名和声明不算证明。现有reader已做的资格拒绝统一转结构化结果，未增加第二身份/字节校验。
- FF/RF透明传递有界pathless机器观察，保留原safe cause、真实退出码、companion状态和unknown。超过64KiB的合法诊断不再被旧小错误窗口丢弃；坏诊断不冒充完整结果。
- 独审抓到发现路径漏记录实际成功写入，ROOT令两条路径共用同一记录器并固化真实案例。旧5个contract断言全部保留，未靠删测、放宽资格或提高读取配额修复。

## 验证与发布顺序

| 层 | 证据 | 当前发布 |
|---|---|---|
| RF消费 | 非作者16项；正常push582P/1既有skip/+36subtests | main/origin10bf6111，CI39849781120 SUCCESS；唯一runtime定点安装，566其它文件元信息不变 |
| FF中转 | 非作者18项；正常重推931P/7既有skip/+78subtests | main/origin7f6a9268，CI39850675373 SUCCESS；5runtime×2物理安装，45其它文件元信息不变 |
| CWP owner | 最终产品27be00fb非作者49P；ROOT相关44P（重叠不相加） | 已merge69a5490b；下一步正常push及精确CI |

实际3进程链使用隔离合成目录触发真实257/256 group限制，原生owner计量经过CWP CLI→已安装FF→已安装RF完整保留，0网络（child socket guard）/0下载/0LLM。旧CWP同一测试真RED（缺owner预算操作）；候选7.43秒PASS，合并主线8.19秒PASS，不能合称一次两项测试。用例固定在`tests/integration/test_local_budget_observation_rf_e2e.py`；大wire、其他历史操作保留由各层独立套件覆盖，不夸大单例覆盖面。

FF首次push本地拦四个旧测试缺required limits实参；只适配这些直接helper测试，保留并加强原断言，整模块19P。生产runtime未改，随后正常推送及远端CI均绿。没有绕过钩子或新增人工门禁。

## 仍开放

真实W07生命周期已另有65项有限独立复核，但summary仍partial/needs_review。W06正在实际预测与四路质量审查；此工程包不代签财报内容或收入预测合理性。新公司HK/US泛化仍待执行。所有旧unknown预留、原件和初审FAIL保留。
