# 三仓架构质量升级交接

2026-10-13。用户要求三仓独立agent全面调查并修复共用根因，ROOT统筹。三仓代码已并主线并推送，精确CI均success；集中跨仓工程验收、必要安装与临时代码副本清理完成，发布记录见本计划progress和ROOT receipt。完整母计划的真实供应商/公司审查尚未关闭。

| 仓库 | 已接代码SHA | 根因收敛 | 独立报告 |
|---|---|---|---|
| company-wiki | 1f9f0673（含d71c8e4f） | 当前根定位；独占临时文件原子提交；配置类型统一；adapter拥有布局发现；有序存储路由实际执行；便携hook | [报告](results/company-wiki/report.md)、[交接](results/company-wiki/handoff.json) |
| filing-fetch | e2efa81d（含5cfad11） | 单一配置/SourceRef/候选投影；日历日期；便携hook；定点安装如实报告完整runtime及scope外drift | [报告](results/filing-fetch/report.md)、[交接](results/filing-fetch/handoff.json) |
| revenue-forecast | f0d694d6 | 共享输入用途与有效收入依赖，input/recognized clock及value/control分开；内容manifest；数值错误；引用≠命题；退休影子队列；便携hook | [报告](results/revenue-forecast/report.md)、[交接](results/revenue-forecast/handoff.json) |

## 验收事实

- 三家公司固定原文/正式预测：中微、腾讯、微软的CWP原文登记/搬根、RF→FF→CWP复用0下载、formal validator/engine/Markdown、快照与数值对照通过；FF→ET→CWP真实进程链用HTTP fixture通过。
- 完整离线回放48 PASS、0 FAIL、14 NOT_RUN、7 NOT_APPLICABLE、2 BLOCKED，247.189秒，独立目录恢复。总体PARTIAL，非全技能通过：HK fresh官方出处与图片PPTX的offline_no_OCR缺口保持母计划事项，不删除、不伪称通过。
- 九种文档真实finite Worker→pathless read→RF消费PASS，原文locator回开9/9；首轮8 loopback POST、同版本复用0 POST，新原件和模型spec各1 POST。真实供应商调用0、费用0；不认证供应商语义质量。单ZIP60,309字节，38份逐字节核对后移除展开副本。
- 原31原生RF组合双向观察精确一致（20 PASS/11 REJECT_OK），三公司完整分部/合并/敏感性/货币单位期间数值不变。独立peer暴露的跨分部及收入确认期问题已在共用依赖层修复，不能用旧peer快照冒充最终代码独审。
- 安装前检查完整owned包，再只补本次文件与明确旧依赖漂移。FF三面fresh CLI、RF三面version/source-lineage fresh进程通过，配置/unknown不覆盖，旧队列不再发货或生产enqueue。

## 下一位执行者

先读[task_plan](task_plan.md)、[findings](findings.md)、[progress](progress.md)，再核对ROOT receipt的精确发布SHA/CI。不要重复创建这三条质量分支、重跑全部慢测试或恢复旧假重叠检查/影子队列。测试只在自有tmp，原件和150份RF WIP保持；独立agent已提交部分由ROOT接主线，作者树仅作验收后清理。

随后回到[文档理解共享引擎](../document-understanding-2026-10-13/README.md)，三个DU harness继续各自独占目录/冻结DU/1；ROOT接线。质量线没有修改这三个工作目录、独占模块或接口。沿原[母计划](../cross-market-rf-e2e-2026-10-08/task_plan.md)G2/G4/G5及审计循环继续，未完成的真实研究不能用本轮离线绿替代。
