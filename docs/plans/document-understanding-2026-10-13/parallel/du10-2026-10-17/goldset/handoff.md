## ROOT 最终接收 — 2026-10-17

状态：PASS，作者完整历史 faf5e580 已 merge；ROOT 修正与独立复审以 receipts/root-gold-final-review.json 的 17 项实际文件 SHA 为准。下方旧 schema1、raw bindings 命令、旧 PASS 和原始 handoff SHA 均为历史，不能用于当前 schema2。

### 实际修正

- 语义：Verisk 单一 Insurance segment 的分母（552.1+230.5=782.6 million）不再误罚为非总收入；阿里8.60亿与含蚂蚁9.60亿去重口径分开；东方电缆原文 Q3 总额约30.66亿与类别35.49亿的冲突保持未知，不自创包含其他收入/YTD解释；名创电话会按开场创始人/CEO归因；中微21.81%属于等离子体刻蚀设备，XD RIE与YDRIE时间点分开；宁德772保留报告期内，仅321在建为期末。
- 抽象：source_ref 使用真实公开v2身份，source_binding仅用于测试初次登记；临时 SourceCatalog.register_sources → query_ref → open_version 实读验证SHA。HTML严格绑定 canonical unit_id+source_locator 并批量 replay；PDF只查指定物理页，无全篇回退。生产根/配置不改，不复制原文。
- TDD语义先8FAIL；当前71PASS/2.83秒，含5个真实临时Catalog正反控（错误SHA、大小、页码、quote拒绝）。11/11真实来源回放PASS；独立复算10原件SHA/size/mtime保持，生产config SHA保持，隔离目录和sentinel恢复。
- 最终独立复审8项全部闭环、0未解决。旧独审Verisk数字误读保留为历史，由本ROOT结论覆盖。

### 当前复现命令（从 company-wiki 根运行）

```powershell
python -B -X utf8 -m pytest docs/plans/document-understanding-2026-10-13/parallel/du10-2026-10-17/goldset/tests -q -p no:cacheprovider
python -B -X utf8 docs/plans/document-understanding-2026-10-13/parallel/du10-2026-10-17/goldset/tests/verify_anchors.py --project-root . --output <独立测试收据路径>
```

环境需已安装本项目和catalog/PDF依赖；第二条需要当前source_catalog配置中的原件。只在隔离临时catalog登记少量选定路径，不扫描全湖、不写生产库。回放PASS只证明来源/locator，不证明经济语义或摘要质量；语义另由独立实读审查负责。

**这是已被读取和修正的回归标注集，不是盲holdout，不是正式模型摘要质量验收。** case.prior_use仅描述最初选样时的历史；新holdout必须另选未参与调整的来源。新增股发行等完整文档阅读覆盖仍遵循母计划，不以本11例冒称全覆盖。0收费/下载/翻译，原件无变更。

Next Step：ROOT继续共享引擎PDF生产接线，随后配置供应商真实摘要、缓存恢复与新盲样本验收；此数据包不新增生产门禁。


---

以下为历史记录（状态以顶部 ROOT 更新为准）。

# DU10-CWP-SUMMARY-GOLDSET — 交接（handoff）

## 状态：COMPLETE

## 摘要

为 ROOT 正式摘要质量验收准备了 11 个来源定位基准 case（10 份唯一本地原件），覆盖 A/H/US × 年报/半年报/三季报/IPO招股书/可转债募集说明书/交流纪要/电话会讲稿/10-Q 八类文档形态。每例带可回放锚点引文、摘要结论边界、必须保留的限定、易误读反例。全部 case 经独立 agent 实读原件复核并通过。

## 核心交付

| 交付 | 路径 | 说明 |
|---|---|---|
| cases/ | `goldset/cases/` | 11 case JSON + index.json，schema `du10-summary-goldset-case/1` |
| 结构校验 | `goldset/tests/test_goldset_structure.py` | 58 项 pytest（字段/枚举/覆盖/锚点格式/支持与反例不冲突/引文预算/无绝对路径） |
| 锚点核对 | `goldset/tests/verify_anchors.py` | 只读原件 SHA+mtime+引文空白归一化回放（需本机 bindings，不进 pytest 收集） |
| A 节点收据 | `goldset/receipts/node_a_freeze.json` | 11 case SHA 冻结 + 缺口矩阵 + 先用核查 |
| B 节点收据 | `goldset/receipts/node_b_tests.json` | 测试/验证命令退出码 + 施工修正记录 |
| C 节点收据 | `goldset/receipts/node_c_*.json/.md` | 首轮审查（1 FAIL→修复）+ 修复复核（PASS） |

## 逐例覆盖

| case_id | market | doc_type | narrative_focus | bound_failure_mode |
|---|---|---|---|---|
| du10gs-cn-annual-catl-industry | CN | annual_report | industry_change | 第三方行业数据当公司收入；预测当实际 |
| du10gs-cn-annual-catl-capacity | CN | annual_report | project_progress | planned/actual（在建≠投产）；混表借数 |
| du10gs-cn-interim-sugon | CN | interim_report | main_business | 预测（IDC全年）当实际（H1）；第三方归属 |
| du10gs-cn-q3-dfc | CN | quarterly_report | main_business | 单季vs累计；类别收入当总收入 |
| du10gs-cn-ipo-hrjc | CN | ipo_prospectus | industry+project | 拟建当已建成；行业规模当公司收入 |
| du10gs-cn-convbond-mlkw | CN | convertible_bond | new_business+project | 测算当已实现；拟建首个别当已有业务 |
| du10gs-cn-ir-amec-minutes | CN | ir_minutes | industry+new | 订单当收入；预测标注丢失；在研当上市 |
| du10gs-hk-ipo-baba | HK | ipo_prospectus | overseas+main | 同页不同TTM混用；去重口径丢失 |
| du10gs-hk-interim-miniso | HK | interim_report | overseas | 存量vs净增；品牌vs集团口径 |
| du10gs-call-miniso-q4-2024 | HK | call_transcript | overseas+plan | 量词丢失；计划当已实现；说话人归属 |
| du10gs-us-10q-vrsk | US | form_10q | main_business | insurance范围当总收入；non-GAAP当GAAP |

## 未覆盖（NOT_AVAILABLE）

1. **新的 CN/US 电话会 TXT**（本仓 configured roots 内唯一 TXT 为 us-txt gold 已覆盖的 MSFT；earnings-transcripts 仓不在本卡边界内）
2. **H/季报公告新原件**（du5 已覆盖金山雲季度公告）

## 复跑命令

```bash
# 结构校验（离线，0 网络模型）
cd C:/Users/郑曾波/Projects/company-wiki-du10-summary-goldset
python -B -X utf8 -m pytest "docs/plans/document-understanding-2026-10-13/parallel/du10-2026-10-17/goldset/tests" -q --ignore-glob "*verify_anchors*"
# 预期：58 passed

# 锚点核对（需本机 bindings）
cd docs/plans/document-understanding-2026-10-13/parallel/du10-2026-10-17/goldset
python -B -X utf8 tests/verify_anchors.py --bindings "C:/Users/郑曾波/.du10-goldset/bindings.local.json" --output receipts/anchor_verify_final.json
# 预期：exit 0，11/11 PASS
```

## 交给 ROOT 的边界

1. case 与 index 是只读数据：ROOT 消费后不得修改再回写 goldset/。
2. 原件 bindings（`~/.du10-goldset/bindings.local.json`）为机内未提交文件；ROOT 需在自己的 checkout 重建。
3. 本包不实现生产摘要、不接 catalog.db（本机该库为空）、不调 LLM。
4. 10 份原件 SHA 在 `receipts/node_a_freeze.json`；ROOT 验收时复算 SHA 确认原件未变。
5. 重复既有 case 的情况：宁德时代 2025 年报、阿里巴巴招股书、名创优品、中微公司均与既有 gold 同公司但不同原件，每个 case 的 `prior_use` 字段已说明新增证据。