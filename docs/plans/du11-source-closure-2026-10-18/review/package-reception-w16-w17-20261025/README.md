# W16/W17 ROOT接收完成（2026-10-25）

## 当前判决

两卡工程接收、主线合并和安装同步完成；**整体来源→摘要→RF→四审→公司循环未完成**。

| 包 | 作者交付 | ROOT修复及主线 | 发布/安装 |
|---|---|---|---|
| W16-RF-BASIS | 611b1d62 | 695dc7493cd5a1d3e10f7d9d1d5436f5447a3861 | RF origin/main一致；精确CI40209029594 success；RF全部owned runtime匹配 |
| W17-AUDIT-COVERAGE | 7c71c811 | 33200f8c947f35be75a77de38040982724e033a7 | Audit无remote，仅本地主线；.claude/.agents各41运行文件全匹配 |

作者工区始终只读，保留作者提交祖先；RF主仓三份assurance运行WIP逐SHA未变。证据见w16/w17-publication.json、mainlines-before-merge.json、installation-final.json、reviewed-to-main-byte-proof.json。Git换行规范化前后LF内容逐项一致，不把物理CRLF差异当新逻辑变更。

## 共因修复与验收

- W16：相同重述/原表标签不再冒充可比；共享owner统一比较组、业务边界及既有policy claims来源，组件显式口径冲突不再被忽略。实际报告参数可以明确采用持续经营口径；旧未声明参数保持total兼容。回测沿用同一判断，明确不可比或依据不足时不计算历史CAGR/MASE/RMSSE，保留flat-base及普通误差。无元数据旧输入保持数值行为并明确非核实比较；未增审批/签收/数据库。
- W17：观察使用各carrier自身schema/来源/run/attempt，不把另一文档、另一运行或旧选择结果标成本次覆盖。选择SHA、来源关联链和嵌套scope一起检查，未知载体不升级；空列表为零、缺失为未知、非法坐标不算几何可用、非法可选JSON不终止其他维度。RF同run多文档索引只观察逐文档prepared/read/use，不等同bundle已采用。模型语义不产生总体PASS。
- 真RED、初审REQUEST_CHANGES及中途失败保留。W16 ROOT50定向、157相关（含50）；独立18次真实CLI/快照/evaluate、10断言和60测试通过。原提交钩子通过，pre-push595P/1既有skip/36subtests通过。W17 ROOT59定向、176相关（含59）及16subtests通过；独立14条CLI命令/断言与最终真实载体回放通过。两项最终独审均0 OPEN，受审SHA与主线Git内容对应。
- 安装收尾：RF另两项既有旧Git阅读契约差异已溯源，85项已发布v3阅读测试通过后定点补齐；所有owned runtime零drift。两个RF安装副本各做legacy/有来源比较真实CLI，共四次通过，测试目录恢复。两技能UTF-8结构校验valid。

## 历史失败与当前状态

Audit同步最初venv两次errno13，使用本机默认Conda执行同一原同步器后完成，**当前没有安装写入阻塞**；旧w17-installation-blocked.json为当时快照，当前以installation-final.json为准。未修改ACL、权限或审批控制。RF首次Git MSYS命名对象启动失败；直接正常重试暴露venv缺pre_commit，换既有Conda后原hooks全通过。RF测试首次本体50通过但Windows只读registry清理失败，随后只对自有临时根恢复写属性删除；最终测试收据均恢复不存在。无生产registry/config/catalog写入。

## Next Step（唯一）

回到[CF1–CF4实施细则](../local-flow-root-causes-20261025/implementation_plan.md)：先用中性RED修HTML业务父级、跨片段闭句与IPO选择效率，在共享责任层实现，再用三市场真实材料验收；来源合格才跑正式v4摘要、缓存恢复零重复费用和真实RF采用。annual14精确金融、摘要语义、公司循环仍OPEN。W18尚未正式交付，W19为独立READY卡，不臆测完成或写作者工区。

本节点0新付费调用、0下载、0原件副本，母账不变。最终受审/运行报告、发布、安装和清理收据均在本目录；根目标仍未完成。
