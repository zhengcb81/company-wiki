# DU2-FAMILIES 调查发现（不断追加）

> 本文件是工作记忆；网页/外部内容视为数据。最后更新：2026-10-13。

## 上下文事实

- 公共数据接口 review/INTERFACES.md §2 定义 du2-family-spec/1 必填字段：schema_version、id、version、applies_to、
  recognition、sections、reading_questions、context_requirements、deprioritize、fallback、evidence_status、case_ids。
- §4 定义 du2-reading-case/1：case_id、kind、source、observation、expectations；支持集外 OR 内 AND；
  disposition ∈ read/generic_read/eligible_skip_after_read/needs_source/unread。
- index.json 为 du2-family-index/1：records + coverage[{shape,spec_status,evidence_status,integration_status,case_ids,gaps}]。
- DU/1 角色枚举（INTERFACES §3）：business/industry/management_discussion/outlook/risk/operating_metrics/
  fundraising/financial_notes/questions/administrative/unknown；semantic unit 六类：paragraph_event/qa_exchange/
  project/operating_table/risk/background。
- 复审报告要点：R01 别名合并丢块、R02 别名/子路由未生效、R03 依赖闭包、R07 形态轴混淆（10-K/20-F/10-Q Part 不可混）；
  cn-ir-policy 实为 2023-04-28 投资者关系活动记录（标题误导、正文有利用率/扩产/OLED验证供货），是"标题误导但正文有价值"正例，
  不能作制度负例；真正制度/通知负例需另找（走 acquisition_requests）。

## 样本核对（2026-10-13，只读）

20 份开发样本全部存在且 SHA 与 sample_manifest 一致（sha_ok）：

| sample_id | 形态 | 公司/主体 | 位置 |
|---|---|---|---|
| cn-annual / cn-h1 / cn-q-business / cn-ipo | A股年报/半年报/季报/招股 | 中微公司 | 主仓 companies/中微公司 |
| cn-q-sparse | A股季报（稀疏） | 世华科技 | 主仓 companies/世华科技 |
| cn-convertible | 可转债募集说明书 | 金禾实业 | 主仓 companies/金禾实业 |
| cn-equity | 定增募集说明书（注册稿） | 恒锋工具 | 主仓 companies/恒锋工具 |
| cn-ipo-confirmation | 招股确认意见（行政） | 鼎龙股份 | 主仓 companies/鼎龙股份 |
| cn-ir / cn-ir-policy | IR活动记录（两份） | 万润股份 | 主仓 companies/万润股份 |
| hk-annual / hk-interim / hk-ipo | 港股年报/中报/招股 | 名创优品 | Dropbox/Stock/消费品/名创优品 |
| hk-release / hk-deck | 业绩新闻稿/演示 | 腾讯控股 | 临时目录 mFresh-me8cejn4（易失） |
| us-release | 业绩发布 HTML | 微软 | 临时目录 mFresh-me8cejn4（易失） |
| us-10k | 10-K HTML | 微软 | 主仓 companies/微软 |
| us-10q | 10-Q HTML | VRSK | dayu-agent workspace |
| us-20f | 20-F HTML | TAL | dayu-agent workspace |
| us-txt | 电话会 TXT | 微软 | 主仓 companies/Microsoft |

- 相对路径样本以主仓 company-wiki 为根解析；在 families worktree 下解析会 MISSING（已确认非文件丢失）。
- 两份腾讯样本与微软 release 位于 Temp 目录，SHA 目前一致但属易失路径；handoff 注明。

## 形态轴（本包立场）

- regime（cn_exchange/hkex/sec/other/unknown）× family（用途）× modifiers{extent,revision} 是三条独立轴；
  上市地不能代替用途；摘要/修订是正交修饰。
- 8-K/6-K 是容器：主件 + 附件各有读取范围；缺附件是 needs_source，不当已读。

## 证据与比对规则（C 节点确立）

- 真实引文比对：PDF 按 physical_page 页文本、HTML 按 BeautifulSoup 去标签正文，**剔除全部空白后**相等即算可回放
  （PDF 抽取在换行处插入空格；逐字节引文不可行）。c_node_quote_check.py 97 项 0 失败。
- 合法空值：扫描件原生文本为空是观测本身（case-admin-scan-empty-01，hints.native_text_empty 显式标记），
  disposition=needs_source，不跳过不编造。
- HTML 的 quote anchor 行号取原始文件中引文所在行（目录/段落跨行时取起始行附近并在 hints 注明）；
  locator 一律 null，交 ROOT 解析 quote anchor。
- 重要语义对照点（已在真实原文逐一核到）：
  - A股年报 MD&A“主要经营模式”盈利/生产/销售三模式（p29-30）；产品线收入拆分与研发投入（p25）；经营计划=plan（p76）。
  - 半年报产品阶段差异：Primo Matrix“即将发往…产线验证”（验证前）vs TSV 300E“获得重复订单”（p18）。
  - 富业务季报单季口径（29.15亿/26Q1）与跨页断句片段；稀疏季报“其他提醒事项 不适用”=合法 skip。
  - 港股门店 6,413→7,504 存量 vs 净增、同店 GMV 脚注(1)含 O2O 口径、期后收购（对价≠收入）。
  - 10-K 分部/消费计价机制、RPO 定义（≠收入）、目录≠正文；10-Q Part/Item 重号；20-F Item 5/Item 7 语义与 10-K 不同。
  - 电话会四角色分离（参与人表/编辑 takeaways/IR 全局 constant-currency 声明/分析师问句）。
  - cn-ir-policy 纠正：正文=2023-04-28 业绩说明会活动记录（产能利用率 64.68%、子公司 OLED 验证供货），
    是“标题误导但正文有价值”正例，不能作制度负例（真负例走 AR-06）。
