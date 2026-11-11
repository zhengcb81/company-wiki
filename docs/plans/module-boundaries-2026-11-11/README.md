# 模块化与解耦：一次有明确出口的收口

当前阶段：**M0规划完成；A1逐模块Git核销、有限接收与清理已执行；五张架构卡仍待派发。** 当前入口是本目录，父计划 `../du11-source-closure-2026-10-18/CURRENT_STATUS.md` 只归总。本轮已受测接收FF、Dashboard小修并推送，未启动五卡的大规模架构实施或恢复业务循环。详见 [reconciliation.md](reconciliation.md)，它是支线/未提交材料的唯一处置表。

先读 [task_plan.md](task_plan.md)，再读 [architecture.md](architecture.md)、[interfaces.md](interfaces.md)、[acceptance.md](acceptance.md)。并行安排和卡片见 [dispatch.md](dispatch.md)，交接格式见 [handoff_contract.md](handoff_contract.md)，机器对照见 [boundary_matrix.json](boundary_matrix.json)。

## 为什么一直没有收尾

已有成果是真实的：D4/D5冻结接口与组合、P3 source stream/parser都已完成各自范围。但过去有四个收尾问题：

1. 用局部接口通过来表述全局完成，随后又发现仓内或分发入口遗漏，完成口径不断变动。
2. 从一个失败顺着私有helper/AST反例继续修，缺少覆盖所有活动入口、配置、状态和安装产物的有限矩阵。
3. 同一“解耦”队列混入摘要召回、资源工作量、研究质量、CI环境及历史工区整理，无法按一个清楚的出口关闭。
4. 源码目录测试允许src/scripts/PYTHONPATH共存；主流程接口已公开，旧工具、隐藏配置、协议外属性和实际部署版本仍可落在盲区。

调查也纠正了误判：退休的CWP launcher不是当前产品故障，RF主线少某些Dashboard入口也不等于部署故障，因为可见配置使用独立release代码根。这些不作为修复数量膨胀的理由。源证据见 review/root_baseline.md 及三份架构报告。

## 路线图

```mermaid
flowchart LR
  A[当前位置：A1已核销/受测接收\n余项已归五卡与ROOT] --> B[M0已完成：接口/写集合/验收矩阵]
  B --> C1[CWP：隐式能力与安装边界]
  B --> C2[FF：六operation与请求组装]
  B --> C3[RF：交付工具与计算报告边界]
  B --> C4[ET：纯协议/进程/表示限额]
  B --> C5[SID：错误语义与反向依赖]
  C1 --> D[M2：ROOT一次组合与独审]
  C2 --> D
  C3 --> D
  C4 --> D
  C5 --> D
  S[ROOT接收StockWiki差额并验证Audit\nDashboard原owner接续] --> D
  D --> E[逐仓主线/远端/PWF关闭]
  E --> F[恢复原R4→摘要→缓存→RF公司循环]
```

五卡可在不同工区并行，彼此不写对方repo。CWP内部七责任由一个作者顺序完成，避免多作者同时改同一个catalog/边界测试。ROOT管理接口、集成和并线，并在StockWiki自己的隔离工区接收C38/B03差额，不与五卡作者同时写其生产代码。

## 可以交给harness的五份独立文档

| 卡 | 预计相对工作量 | 工区（Projects下） |
|---|---|---|
| [MB-CWP](harness_lanes/MB-CWP.md) | 大：七责任、四确认缺口、安装验收 | mb11-cwp |
| [MB-FF](harness_lanes/MB-FF.md) | 中：真实CLI隔离；无缺陷允许NO_CHANGE | mb11-ff |
| [MB-RF](harness_lanes/MB-RF.md) | 中到大：分发/计算报告/历史profile隔离 | mb11-rf |
| [MB-ET](harness_lanes/MB-ET.md) | 中：协议依赖方向和结果限额 | mb11-et |
| [MB-SID](harness_lanes/MB-SID.md) | 中：11项旧WIP接收、typed错误与纯metadata | mb11-sid |

不承诺未跑过基线的日历工期。关键路径是CWP owner收口→ROOT组合；其他卡可覆盖其等待时间。每卡A完成直接继续B/C，不增加人工停等。所有卡交付前必须独立审查并修复本卡问题。

## 完成的含义

本计划关闭表示：当前登记的活动入口只能通过公开接口通信，纯域/配置/存储职责清楚、真实交付包可独立运行、替换实现和越界反控能稳定验收、已并入各自正确主线。后续新的业务缺陷仍归所属模块；不会因为出现研究或摘要质量问题再把这次架构结论说成从未完成。

本轮没有初始化索引、真实下载、模型调用或全局技能部署。按新增授权做了精确清理、FF隔离候选接收（工区已回收）、Dashboard有限修复及离线/回环测试。历史真实来源/收费验收没有重跑。
