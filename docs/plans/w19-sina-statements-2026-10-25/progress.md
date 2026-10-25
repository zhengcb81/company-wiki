# W19 进度

2026-10-25 ROOT建立独立Git工区、文档seed和已审研究输入，未做产品实现/生产下载/库迁移。

初始化过程：--no-checkout未建index，显式暂存清单核对在commit前拦住全仓删除；read-tree初始化后移除了此前已暂存但不属于HEAD的自有seed。ROOT据中央输入重新生成这批文档，保留工作树源码。其间两次存在性检查也在修改/提交前退出。无坏commit、无主工区或原件变化。作者继续时以真实Git记录和本计划当前入口为准。

正常pre-commit首次因用户全局cache数据库只读退出。ROOT改用本任务局部PRE_COMMIT_HOME，保留原hooks及其文件范围选择，不禁用hook、不改全局cache权限；文档seed不触发产品测试。

## 2026-10-25 作者A节点（勘察+RED+BJ）

### 勘察与夹具验证
- 双仓基线核对：CWP a3083502(基线243993d2)、FF c8b0e40(基线e0d9642)，branch codex/w19-sina-statements-20261025，tracked clean。结论冻结进findings.md（含全部接缝 file:line）。
- 18份研究夹具：`.gz`文件SHA与W19-setup.json一致(18/18)；**解压字节SHA与observations.json原始记录一致(18/18)**；解压总2,572,006B。
- 从真实夹具冻结的测试期望：BIZTOTINCO 20260630="6691287327.670000"、BASICEPS="4.330000"(ps4)、20251231 row7=BIZTOTCOST"11006675861.270000"、20231231 publish_date="20250418"(PIT反例)、fzb每期141行含5空field分组行、report_count为字符串、lrb 36期/10+10+10+6分页。

### BJ能力探针（真实有界，共2请求88B，HTTP 200）
- `bj430017 lrb type0 page1 num2` → `{"result":{"status":{"code":0},"data":null}}`，44字节，sha256=2e2fd57f...（两次抓取字节一致）。**BJ是该接口的显式capability gap**；provider对BSE必须诚实返回no_data（与sh999999同形状，不能写成覆盖PASS）。
- 证据已存 inputs/research/capture/bj430017-lrb-type0-page1-num2.json.gz 并追加observations.json记录。

### 真实RED（2026-10-25，均为缺功能而非fixture坏）
- CWP `python -m pytest tests/financial_statements/ -q`：5个collection error（`ModuleNotFoundError: company_wiki.source_catalog.financial_statements` 及 canonical_writer 缺 `ThirdPartyDatasetOriginal`）+ test_cli_subprocess 4 FAILED（子进程同样缺模块）。
- FF `python -m pytest tests/financial_statements/ -q`：collection error（`ModuleNotFoundError: ff_financial_statements`）。
- 均为被测能力不存在导致，fixture路径与SHA已先行验证有效。

### 下一步
B节点按唯一owner实施：contracts/normalize→sina_provider→schema/store迁移→writer入口→repository→service→cli→FF薄客户端+SKILL。

## 2026-10-25 作者C节点（离线/真实E2E、官方对照、空间）

### 离线端到端（tests/financial_statements/test_offline_e2e_full.py，随repo）
- 真CLI进程 FF式入口→fixture重放(12数据页+3终止null页)→canonical原件→两表→公共query→JSON：**income 36 / balance 33 / cash 36 期，总源行 9,729**（含分组/null行），逐期行数77/141/64；锚点 BIZTOTINCO/CURFDS/LABORGETCASH 20260630 精确值且 json_pointer 在对应原件内可解析。
- 重复同请求：0 HTTP、原件字节/版本数/值行数零增长、版本ID一致。原始字节篡改后 reader.open_version 拒绝（SourceReadError），恢复后可读。叙述链零产物（artifacts normalized/summary=0），classify_document_kind 保留 financial_statement_dataset 不落入财报叙述通道。
- 迁移矩阵/并发双初始化/1.2→1.3升级保留旧数据/未知版本fail-closed/只读0写（test_repository_migration.py，15项）全绿。

### 真实有界端到端（独占测试根，费用0/LLM0，共~25公开请求）
- 中微三表全历史（真实网络）：首次 lrb 5请求/705KB（直连CWP CLI），随后FF薄客户端：fzb 5请求/1.10MB、llb 5请求/648KB、**lrb直接命中本地复用0 HTTP**；合计 complete，36/33/36 期。完整三表复用请求：**全部0 HTTP**。
- 招行(金融,SSE) fzb 年报+中报 2023-2025：2请求，6期 complete。美的(SZSE泛化) lrb 2024-2026：2请求，5期，BIZTOTINCO≠BIZINCO 保留两科目。
- BJ（北交所）：`诺思兰德`名称查询 → `company_identity_ambiguous` + candidates [430047,920047]（新旧两代码，真实主数据歧义）；ticker `430047` 解歧后 provider 1请求 → **no_data → statement not_found（显式capability gap，不假装覆盖）**。

### 官方原件逐值对照（独立财务正确性验证）
- 用既有工具（CWP ensure + StockInfoDL CN适配器）在第二独占测试根真实下载中微 **2025年年度报告** PDF（9,168,457B，downloaded_new，费用0）。与Sina 2025-12-31逐值对照（expected/actual/locator）：
  | 项目 | 官方年报 | Sina API | 结果 |
  |---|---|---|---|
  | 营业总收入 | 12,384,638,268.11（p142合并利润表） | 12384638268.110000 | 一致 |
  | 基本每股收益 | 3.40 元/股（p25） | 3.400000（CNY/share） | 一致 |
  | 货币资金 | 7,951,400,258.31（p68） | 7951400258.310000 | 一致 |
  | 销售商品、提供劳务收到的现金 | 14,122,161,977.48（p146合并现金流量表） | 14122161977.480000 | 一致 |

### 空间测量（中微全历史根）
- canonical原件+sidecar 3,578,895B（12原件+12sidecar+3 JSON响应）；catalog.sqlite3 6,680,576B；合计 10.26MB ≤ 16MiB 目标。security_master快照2.29MB为测试脚手架非产品数据。重复请求后文件数/DB版本行/值行零增长（离线E2E断言）。
- 测试根恢复：两真实根保留至独立审查结束，handoff后删除并记录收据。

### 期间真实响应总字节（wire）
lrb 705,179B + fzb 1,104,886B + llb 647,868B + 美的397,408B + 招行(~2页) + BJ no_data 44B + 早期BJ探针88B + 官方PDF 9,168,457B（另一工具另一预算）≈ 12MB+9MB < 20MB上限。

## 2026-10-25 独立审查轮次记录

- **首轮**（agent_2d649eaf，对 CWP e583904d/FF a211d3a）：PASS_WITH_FIXES，9 findings（R1 范围放宽谎报 complete、R5 未提交改动为 blocking）→ 全部根修于 CWP ae317ca9 / FF 7d9bb85。
- **第二轮**（同审查者，对 ae317ca9/7d9bb85）：PASS_WITH_FIXES，新增 R10（T2b/T2c 无 from/all_history 仍谎报、T3b 供应方新增更近期不重抓）与 R11（replay 跨实体污染）blocking，R12 continuation 三缺陷，R13/R14 low；同时确认 R1-R9 修复与 R9 字节账精确相等 → 根修于 CWP 71e98ed0 / FF d396fe7（coverage 表 fetched_from/fetched_to 抓取包络 + 方向化 _needs_fetch；_source_owner_security 归属闸门 fail-closed；token 按表作用域；replay 分支前置 + 完整信封）。
- **第三轮补审**（对 71e98ed0/d396fe7）：进行中；结论将回填 delivery/w19/review.md 并随 handoff 提交。
- 每轮审查报告原样保留在 delivery/w19/review.md|json，未用作者转述替代。
