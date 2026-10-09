# 当前授权与过度审批补漏

## 决策

用户2026-10-09要求取消逐材料授权及类似过度审批。项目沿用既有明确授权，不增加新的许可文件；平台自动审批不受项目配置控制，不能伪称关闭或绕过。API HTTP Authorization 是密钥认证，不是人工审批。

## 一次集中施工

1. MAIN检查CWP当前source ensure、reader、prompt diagnostics和AUTO机器错误。私有/公开标签、prompt人工review、普通错误人工阻塞已退役，保留兼容旧记录；不重复已完成施工。
2. 旧`authorization.py`只有legacy数据对象进入coordinator，build/validate没有生产调用。移除计划hash/政策hash/TTL许可条件；保留明确provider/accession范围、实际item/byte上限和旧字段读取。先写取消许可反例，再实现；不删资源边界测试。
3. 旧`remediation.py`提案/批准流程只有专属测试调用，当前元数据入口用facts/local_prepare。退休旧写流程为无IO兼容入口，旧数据库记录可读，不删除生产记录；证明不会新增proposal/shadow assertion，不用自动签字替代人工签字。
4. 邻仓owner独占FF/RF技能说明及相关docstring，盘点ET、StockWiki、audit当前入口。删“每次明确授权才可执行”等过时指引，说明任务请求/既有授权沿用和配置预算；只对明确残留阻断写责任修复。MAIN接收、并主线、定点安装，不动其他owner WIP/Dayu。
5. 一个集中验收：legacy scope与退休writer责任测试、已有公共source-chain责任包；必要静态检查和当前技能安装SHA。无需付费/再跑22页OCR/全71/每个小节点人审。正常commit/push并更新三份主PWF。

## 保留措施与原因

| 保留 | 目的 |
|---|---|
| 原件不可变、SHA、真实类型/路径验真 | 不丢原件、不把坏文件当证据 |
| issuer/period/as-of资格 | 避免错公司、错期次与未来资料 |
| 配置provider/model及资源上限 | 按用户配置、防账目及空间重新膨胀 |
| lease/generation/outbox与目标锁 | 并发去重、丢包恢复、不重复付费 |
| 用户指定4独立质量审查 | 真实研究大节点验收，非授权许可 |
| 工具平台审批 | 外部执行边界，项目无法关闭；使用既有授权处理 |

历史报告的拒绝/失败/unknown不得改成成功。旧canary样本工具只有测试调用，不能作为运行许可；词语匹配不等于真实阻断。最终盘点须逐项给代码链与实际状态，不声称全机器/所有未来路径均已审查。

## 并行接口

MAIN独占CWP代码/主PWF/预算和合并安装；neighbors owner只写`phase6/permission_residue_cleanup/neighbors/`与FF/RF独立工作树。现有replay-config owner仍独占`tools/cross_market_suite`，launcher owner只写自己的启动卡。研究执行在本集中收尾后启动，避免安装漂移。
