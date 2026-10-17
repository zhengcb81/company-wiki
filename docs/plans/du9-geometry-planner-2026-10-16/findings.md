# 调查

卡内给出ROOT已调查的根因；作者仍须在A自行验证。尚未运行业务测试，不能称组件或生产PASS。

## A节点独立核实（2026-10-16，基线 cb1e4c07 / bf160c8e）

### 核实结论：真实共因是"缺少有界公平的请求规划组件"，不是PDF解析能力

在基线源码中逐点核实：

1. **细几何处理本身无顺序偏好**：`src/company_wiki/document_understanding/layout_hints/fine_geometry.py:291`
   `consume_fine_geometry(doc)` 只处理调用方给定的 Doc 单元；显式指定深页即可被处理，
   与ROOT调查"显式指定深页已经可捕获"一致。
2. **唯一预算是总量型 WorkBudget，无章节公平性**：`layout_hints/contract.py:33-51`
   `WorkBudget.charge()` 只做全局累计封顶（`used + n > max_work_units` 即耗尽），
   没有任何按章节/需求类别预留的机制；`pipeline.py:95` 调用方传入或默认构造单一预算。
3. **请求顺序由上游调用方决定**：基线中不存在任何请求规划/配额模块
   （`grep -rn "geometry_intent\|plan_geometry" src/` 为空；`document_understanding/` 目录
   无 quota/schedule/reserve 类逻辑）。粗关键词+邻页扩展按前部物理顺序发请求，
   前部一个大章节（风险/财务附注）即可吃光 64 页细几何限，深页（金禾223/224一类）
   在预算耗尽前轮不到——这正是本卡要消除的饿死模式。
4. **WorkBudget 协议可只读复用**：`charge(n)` 超限抛 `WorkBudgetExceeded` 并置
   `exhausted=True`，未成功 charge 不做工作；公共入口转 partial 是既有约定
   （`contract.py:28-29` docstring）。本卡直接 `from ...layout_hints.contract import
   WorkBudget`，不复制预算类。

因此本卡实现独立纯组件 `geometry_intent/`：plan 在调用内按需求类别做有限公平配额
+借用+全局硬余额（预留深章节份额），admit 按实际 observed_candidate 事件扣减并
幂等去重；ROOT 保留原生导航/章节匹配/单 TextPage/生产 source 调用。

### 冻结手算用例（fixture_geometry_planner.json，96页，2父文）

- scope `main`（物理页1..70）：目录1..3(context,不可请求)、释义4..9(administrative,p1)、
  风险10..30(context,p1)、财务附注31..55(context,p3)、管理层讨论56..62(operating)、
  未来发展63..65(operating)、公司治理66..70(context, navigation=unknown)。
- scope `attachment`（物理页71..96，第二父文）：募投一期71..80、二期81..88、
  募投章节父窗71..88（嵌套章节，project）、业务与技术89..96(operating)。
- limits 固定 `{max_pages:64, max_requests:64}`（对应真实15秒/64页限，测试不抬cap）。

手算期望（可请求类别4类：administrative/context/operating/project，base=64//4=16）：

| 类别 | 期望页(union) | base | 借用 | 配额 |
|---|---|---|---|---|
| administrative | 6 | 16 | 释放10 | 6 |
| context | 51 | 16 | +10 | 26 |
| operating | 18 | 16 | 0 | 16 |
| project | 18 | 16 | 0 | 16 |

合计64=硬余额。窗口配额（最大余数法，同额按规范序）：风险11、附注13、治理2；
管理层讨论6、未来发展3、attach-op 7；募投一期9、父窗7、二期0(透明，份额已由父窗预留)。

顺序全候选事件流下的冻结期望：
- 前部独占基线（按物理序贪心请求到64页耗尽）：project 类=0、attach-op=0 → **RED**。
- 本组件：project 类≥1（深页85/86可得）、attach-op≥1、admitted 总数≤64且=64、
  重复ACK去重不重复扣、reason 分离(exhausted/cancelled/not_arrived/not_found)。

RED 首次FAIL回执：`receipts/red_first_fail.txt`（在实现前对基线贪心复现冻结期望失败）。
