# DU2-FACETS 覆盖矩阵

状态定义（相互独立）：spec_status=规格是否写完（implemented/proposed）；evidence_status=证据形态
（real=真实原文锚定 / synthetic_only=仅合成 / missing=无）；integration_status 恒为 not_integrated
（生产接线由ROOT执行，本包不声称已接）。语义反例的生产执行一律 NOT_RUN_ROOT_INTEGRATION。

## 1. 八个共用面（facet_*.json）

| 面 | 规格 | 证据 | 锚定case | 缺口 |
|---|---|---|---|---|
| 主业与商业机制 | implemented | real | real_hk_annual_store_network, real_us_release_subscription | — |
| 行业与竞争 | implemented | synthetic_only | syn_exit_low_information | 缺带署名/统计期的行业章节真实片段 |
| 新产品/新业务 | implemented | real | syn_stage_ladder, real_cn_ir_premise_denial | 缺募投变更/延期公告对第二曲线影响的真实片段 |
| 海外/新市场 | implemented | real | real_hk_annual_store_network, real_us_release_subscription | 缺出海建厂/许可/渠道推进独立片段 |
| 客户/订单/履约 | implemented | real | real_cn_ir_premise_denial, syn_negation_scope, real_us_release_subscription | 缺正式订单/框架协议/里程碑合同原文 |
| 产能/募投 | implemented | real | real_cn_equity_capacity_phasing, real_cn_convertible_capacity_funding, syn_capacity_project | 缺募投变更/延期/终止公告 |
| 经营指标 | implemented | real | real_hk_annual_store_network, real_us_release_subscription, syn_quantity_slots, syn_financial_numbers | — |
| 业务风险/明确否认 | implemented | real | real_cn_ir_premise_denial, syn_negation_scope, syn_exit_no_answer | 假设风险→已发生事件的年报对照为合成 |

## 2. 两份A级语义规格

| 规格 | 覆盖的关键语义 | 证据 | 锚定case | 缺口 |
|---|---|---|---|---|
| semantic_stage_progression（第二曲线阶段） | 阶梯不跨级；计划≠实际；主体/产品绑定；药物阶段独立 | real | syn_stage_ladder, real_cn_equity_capacity_phasing, real_cn_ir_premise_denial, syn_exit_no_answer | 缺生物医药阶段真实原文 |
| semantic_capacity_project（产能项目） | 项目不互串；原有/新增/替换口径；分期条件；资金三分口径；测算≠实际 | real | real_cn_equity_capacity_phasing, real_cn_convertible_capacity_funding, syn_capacity_project, syn_quantity_slots | 缺项目变更 delta 真实样本 |

## 3. 四类可组合经营模式（mechanism_*.json，通用机制、无公司产品名单）

| 机制 | 轴 | 规格 | 证据 | 锚定case | 缺口 |
|---|---|---|---|---|---|
| 软件订阅/消费 | subscription | implemented | real | real_us_release_subscription, real_us_call_roles | 缺队列指标（NRR/续费率）定义原文 |
| 软件订阅/消费 | consumption | implemented | real | real_us_release_subscription | 缺纯用量计费真实片段 |
| 零售店网 | store_network | implemented | real | real_hk_annual_store_network, syn_quantity_slots | 缺同店/开关店明细 |
| 制造认证/利用率 | manufacturing | implemented | real | real_cn_equity_capacity_phasing, real_cn_convertible_capacity_funding, syn_stage_ladder | 缺认证/利用率经营表 |
| 生物医药/CDMO | biopharma | proposed | synthetic_only | syn_stage_ladder | 全缺：临床阶段/获批作用域 |
| 生物医药/CDMO | cdmo | proposed | synthetic_only | syn_stage_ladder | 全缺：订单/里程碑/版税 |

机制组合不变量（自动测试）：四记录的机制轴两两不交叠且并集恰为六轴；机制记录内不出现公司/产品
专名；不同机制记录不得重定义同一 confusion/assertion（防互相覆盖）。

## 4. 市场与经营模式（C节点真实核对覆盖）

| 市场 | 真实case | 载体 | 经营模式 |
|---|---|---|---|
| CN/A股 | real_cn_equity_capacity_phasing | PDF募集说明书 | 制造（工具/装备），募投分期 |
| CN/A股 | real_cn_convertible_capacity_funding | PDF可转债募集说明书 | 制造（精细化工），产能/资金缺口 |
| CN/A股 | real_cn_ir_premise_denial | PDF投资者关系记录 | 精细化工/新材料，问答否定/主体分层 |
| HK/港股 | real_hk_annual_store_network | PDF双语年报 | 零售店网（门店模式×地域） |
| US/美股 | real_us_release_subscription | HTML业绩发布 | 软件订阅/消费（商业vs消费口径） |
| US/美股 | real_us_call_roles | TXT电话会 | 软件订阅/消费（角色/全局限定） |

三市场（CN/HK/US）× 三种模式（制造/零售/软件订阅消费）已覆盖；生物医药/CDMO 缺真实样
（见 acquisition_requests.json），其余缺样均已单列，不用“专家常识”补公司事实。

## 5. C节点：真实原文核对记录（单列）

- 记录文件：c_verification/real_excerpt_checks.json（20条引文检查，全部 normalized_match=true）。
- 方法：PyMuPDF 按声明页取只读文本（PDF）/全文归一化（HTML/TXT），空白归一化后逐字比对；
  逐条复算原件 SHA-256 并在读取前后核对 mtime（raw preservation）。
- 结论边界：C记录只证明引文与原件一致、来源身份正确；不证明引擎语义正确（属ROOT B/C）。
- 复检命令：`python -B -X utf8 docs/plans/document-understanding-2026-10-13/review/deliverables/facets/tools/verify_real_quotes.py`
  （依赖未提交的 .planning/du2-facets/bindings.local.json 提供本机路径）。

## 6. 合法退出与防膨胀

| 退出类型 | case | 行为 |
|---|---|---|
| 低信息 | syn_exit_low_information | generic_read，仅存来源属性，0公司业务事实 |
| 无业务 | syn_exit_no_business | eligible_skip_after_read，facts=[] |
| 无回答 | syn_exit_no_answer | 记『未回答』，不升级为否定/肯定/失败 |
| 纯财务 | syn_financial_numbers | correctness_if_emitted：不要求选，选了不可错 |

## 7. 测试命令

```
python -B -X utf8 -m pytest docs/plans/document-understanding-2026-10-13/review/deliverables/facets/tests -q
```

结构不变量范围：记录schema/枚举/条件式required_context（quantity_emitted→unit、
project_emitted→project、explicit_condition_present→condition；always不强制数字）、支持组引用
完整性（组内AND、组间OR）、正反配对维度（主体/时间/单位/范围/语态/删条件/错项目/缺否定）、
引文预算（每source ≤8KiB）、可移植性（无绝对路径、0原件复制）、持久数据 ≤512KiB、
机制组合不互相覆盖、C记录与真实引文一一对应。**不含**自然语言蕴含判定与摘要生成。
