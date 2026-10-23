# W11-CWP-SOURCES 独立实施计划

唯一施工卡：[W11-CWP-SOURCES](C:/Users/郑曾波/Projects/company-wiki/docs/plans/du11-source-closure-2026-10-18/harness_lanes/20261023/W11-CWP-SOURCES.md)。本目录是本包唯一PWF执行队列，父母仓状态由ROOT维护。

## 目标与责任

官方材料发现的离线分类、漏解析与覆盖状态根因诊断和修复。详细输入、允许写集、真实命令、测试矩阵和输出字段以卡及共享INTERFACES/INPUTS为准。代码base `a2f99db676846b7f475def253c541e12c49ae5fe`，start HEAD `0d7ada2138d41053598fcbfab5ac1e2bbd6684f5`（文档提交，非产品代码变更），支线`codex/r1-w11-source-recovery-20261023`。

## 边界（最高）

0 新联网 / 0 模型调用 / 0 下载 / 0 生产写入；不改共享 transport/budget/DTO；不为单公司/域名/年份写分支。

## A/B/C 大节点

| 大节点 | 状态 | 完成条件 |
| --- | --- | --- |
| A 恢复和冻结 | done | 输入/版本和真实问题及正反期望；有缺陷保存实际RED，无缺陷诚实记未观察到 |
| B 实施/研究 | done | 卡要求全部内容、真实离线运行和共有根因修复；不同情形泛化 |
| C 交付 | in_progress | 公共入口E2E、临时资料恢复、独立agent完整度/质量审查、修复及最终复审、commit/handoff |

### A 细目
1. ✅ 工区核对：HEAD `0d7ada21`、tree clean、`official_discovery`/`official_source_cli` `__file__` 全落本工区 src。
2. ✅ 实读证据：W11 原卡、fetch.md（FETCH-002/003）、faa5bf… input/consume/stdout、events.jsonl line 9–10、web_discovery.json、attempt/execution_request。
3. ✅ 486789B 正文有界查找（两条已配根）：精确大小 0 命中、400–600KB 全 hash 89 文件 0 命中、holdout sqlite+WAL needle 0 命中、catalog.sources 90 条无 f1e822a8…；`body_available=false`。
4. ✅ 基线回归：`-k 'discovery or official_index_http or cn_fundraising'` 7 passed → RED_not_observed（现有套件）。
5. ⬜ evidence_inventory.json + 期望表 + 缺陷假设验证。

### B 细目（候选缺陷假设，须中性反例证实后才改产品）
1. 隐私/条款 PDF 进入候选 → 法律导航 vs 业务材料语义。
2. "earnings" 一词把 release/presentation 标成 `investor_call_transcript` → 卡 §4-B 判定误分类。
3. 日期窗口边界：start/as-of 当天、非法/未来/无日期；检索时间≠发布日期。
4. URL/去重：相对链接、多锚、query/fragment、同标题不同原件。
5. item_limit break 的 scope/limitation 语义。

### C 细目
- 真实 subprocess CLI pages 分支 E2E（≥2 中性 issuer、顺序/名称交换）；
- 清理核验 + cleanup.json；
- 独立审查×2（初审修复后终审），绑定最终源码 SHA；
- delivery/w11/ 六件套 + commit/push 本支线。

## 非重叠写集
`src/company_wiki/source_catalog/official_discovery.py`、`official_source_cli.py`（仅 discover 分支）、`tests/integration/test_official_source_flow.py`（发现回归）、`tests/integration/test_official_discovery_offline.py`（新增）、本 PWF、`delivery/w11/`。

## 环境事实（实测）
- 解释器 `C:/Users/郑曾波/Projects/company-wiki/.venv/Scripts/python.exe`（3.14.2 Windows）；pytest 9.1.1；PYTHONPATH=`工区/src;工区/tests`。
- pytest.ini 带 CW-BASETEMP-DECISION；测试后 basetemp 自动恢复不存在。

独审放C大节点，不添加小节点门禁。真实外部资料不可得如实external_limit；不得伪造本包或全公司PASS。
