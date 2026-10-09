# 重复授权与审批补漏结果

2026-10-09。当前项目入口与邻仓盘点已完成并实施，详细逐路径30项见[邻仓盘点](neighbors/INVENTORY.md)，机器结果见[归总](main_acceptance.json)。本结果只声明已检查入口，不声称审查过全机器所有未来程序。

## 已取消

| 项目 | 实际修改 |
|---|---|
| company-wiki | legacy计划hash、政策hash、有效期不再作为下载许可；显式目标/资源范围仍生效 |
| company-wiki | proposal→人工approve→shadow写链退役为无IO兼容入口；当前标准facts/prepare负责来源元数据，历史行保留可读 |
| filing-fetch | 每份材料/每个供应商重复授权指引删除；已授权公司任务直接按配置复用或补缺 |
| revenue-forecast | 沿用公司任务和会话授权；不要求额外授权JSON、签收或canary；当前schema2示例取代旧双门说明 |
| earnings-transcripts | README明确实际单一下载意图；旧allow-download兼容参数不是第二许可，历史限制不充当当前待审批 |
| StockWiki | 启动一次已配置scheduler任务时，前后端均不再要求手输RUN_SCHEDULER_CYCLE口令 |

此前已经退役的private/public许可、prompt-injection人工签收阻断、普通机器错误转人工阻塞及发布人工授权文件不重做。HTTP Authorization是API密钥认证，不是新增人工审批。供应商禁用配置/套餐不足是实际能力，不通过“取消审批”伪造可用。

## 保留的是职责校验

- 原件不可变、SHA/类型/路径验真：守住“原始材料不丢”和证据实际存在。
- 公司、财年、信息日：避免错公司、错期和未来数据，不额外要求身份签收。
- 已配置provider/model、实际费用/token/空间/时间：遵守用户配置与预算，不另造许可表。
- 并发锁、lease/generation/outbox：避免重复下载、重复付费，支持中断恢复。
- 用户指定的四个独立质量审查：放在真实研究大节点；不改成每个小步骤等待人签字。

工具平台的自动审批由当前托管session控制。仓库没有关闭它的接口，也没有改写平台安全策略；使用已有明确授权执行，保留真实拒绝原因，不更换渠道绕过。相关机制见[官方说明](https://learn.chatgpt.com/docs/sandboxing/auto-review)。

## 验收与发布

- CWP：9 RED后77个不同责任测试PASS；2个显式真实夹具opt-in未跑，原因原样记录；Ruff/mypy通过。4个独占测试根恢复不存在。
- StockWiki：4 RED后35 PASS，实际前端action/HTTP/runtime及静态检查通过。未启动生产scheduler。
- FF/RF：现有技能/文档责任检查通过，FF执行AST除docstring外未变。正常RF pre-push 126 PASS、Ruff/mypy通过。
- 无下载、无新模型调用、无生产原件/配置改动、无Dayu变更。原先失败历史不改成成功。

| 仓库 | 当前主线集成 | 发布 |
|---|---|---|
| company-wiki | 91f7bb26（含审批及replay隔离） | 已推；CI37893837225成功 |
| filing-fetch | de09787c | 已推；CI37893953324成功 |
| revenue-forecast | 42382c9b | 已推；CI37894025957成功 |
| earnings-transcripts | fa99f468 | 已推；没有Actions配置 |
| StockWiki | c40de214 | 本地master已并且干净；实际remote=[]，未创建猜测远端 |

FF/RF六个安装文件已按精确blob定点同步；配置/output未覆盖，.claude现有junction已核对。邻仓其他owner WIP/密钥文件不纳入commit。表中CI是代码集成精确SHA结果，本结果文档的后续commit/CI另在Git与进度记录。

## 主线下一步

授权清理完成，Phase6研究验收仍进行中。MAIN冻结已有mFresh三家公司环境、当前安装与母账，启动原三家全新RF执行及四独立审查，然后新三家泛化验收，最后继续NVDA公司池loop。预算沿用累计USD20/2,000,000tokens，原件在所有审查结束前保留；不重新询问逐材料外发授权。
