# DU4-STATE 交接（DU4-STATE lane / du4-interfaces/1）

2026-10-15。分支 `codex/du4-state-20261015`，基线 `8206e78d4087531b1d7ed57c45a73c942cc702e3`。
机器可读版本见同目录 `handoff.json`。本包是内存语义组件：不落库、不改来源角色、不打投资分、不决定选择。

## 交付物

| 路径 | 内容 |
|---|---|
| `src/company_wiki/document_understanding/operating_states/` | `detect_operating_relations` + 保偏移匹配视图 + 有界谓词模式 |
| `tests/unit/du4_operating_states/` | 集中单测/契约测试（86 项） |
| `docs/plans/du4-state-2026-10-15/results/` | 语义 RED、最终结果、静态检查回执 |

入口：

```python
from company_wiki.document_understanding.operating_states import detect_operating_relations
result = detect_operating_relations(observation, work_budget=budget)  # budget 为现有 WorkBudget 实例
```

输入 `du4-operating-observation/1`（`unit_id`、`units={id: unit}`、可选 `context_unit_ids`/`language`），
输出 `du4-operating-relations/1`（`relations/diagnostics/status/work_used`）。
每个 ref = `{unit_id, char_start, char_end}`，精确指向**原文** Python 切片（含换行/繁体原字形）；
匹配视图（t2s + 折行消隐）只用于匹配，偏移经逐字符映射回到原文。

## 实际验证

- RED（A）：`results/red-run.txt` — 真实 m41 首答三关系断言语义失败（`assert 0 == 3`），非导入错误；60 failed / 26 passed。
- 最终（B/C）：`results/final-run.txt` — `PYTHONPATH=src python -B -m pytest -q tests/unit/du4_operating_states` → 86 passed，exit 0。
- 静态（C）：`results/static-checks.txt` — ruff 0 remaining（14 个 F541 已修）、mypy `no issues found in 4 source files`。
- 输入不变、零/部分预算 partial 与计数、确定性、长句有界、role 无关、跨 parent 不串联、精确 refs 都在
  `test_c_contract.py` 断言。真实保存段落（test_a）与合成/holdout（test_b）分开报告，不宣称市场召回率。

## 真实 m41 首答的三条独立关系（test_a 逐条断言）

原文：`答：您好，公司现无生产 VC（碳酸亚乙烯酯）的情况，根据公司控\n股股东中国节能信息，中国节能与宁德时代已经建立了联系，并希望建立\n业务协同与合作。`

| # | 断言（原文 refs） | activity | polarity | stage | attribution | modality |
|---|---|---|---|---|---|---|
| 1 | 公司现无生产 VC（碳酸亚乙烯酯）（actor 公司 / obj VC（碳酸亚乙烯酯） / pred 生产 / qual 现无） | production | negative | current | issuer | actual |
| 2 | 中国节能与宁德时代已经建立了联系（actors 中国节能+宁德时代 / pred 建立了联系 / qual 已经） | business_relationship | positive | contact_established | quoted_related_party | actual |
| 3 | 并希望建立\n业务协同与合作（actors 继承同上 / obj 业务协同与合作 / pred 建立 / qual 希望） | business_relationship | positive | intended_cooperation | quoted_related_party | aspirational |

失败边界（测试固化）：股东增持回答 0 关系；提问中的带量采购设想 0 关系（仍是 question context）；
hope 不是合同/订单/发货；联系不是合同；R2 主体不改写成发行人。R3 的 assertion ref 保留原文 `\n`，证明偏移是原文而非归一化视图。

## 覆盖面（规格，非召回率）

- 参考设计 32 原始合成例：关系有无逐例断言（`test_b_synthetic_specs.py::SYNTHETIC_CASES`），外加定向 stage/modality/refs 断言。
- 16 组扩展反例：双否定→uncertain、未取消≠投产、非生产瓶颈≠停产、仅试用≠认证成功、行政否定、
  主体四类不互换、跨 parent 不串联、提问前提、纯财务组成、停产影响营收保留、感谢语+真实否定、愿景、
  无指代"没有/不便评论"、无法确定→uncertain、五阶段区别（建立联系/计划/希望/已签约/已发货）、正文关系与角色无关。
- Holdout（未见公司/产品/英文/繁体/折行）：`寰宇新材…ZX-9 添加剂`、`Halcyon Meridian…Tessellate resin`、
  `臺廠光宇精密…氫能模組`（object ref 为原繁体 `氫能模組`）、`星环新材现无生\n产 TL-3溶剂`。

## 给 ROOT 的 OperatingFact 适配建议（不自行改共享谓词）

1. `detect_reading_business_fact(text)` 内用薄适配器把文本包成单 unit 观察（schema `du4-operating-observation/1`；
   `parent_id/role/kind/locator` 可用调用方占位，不需要来源重签收），调用 `detect_operating_relations`，
   **传入调用方现有的共享 `WorkBudget` 实例**；组件内部不建预算。
2. 映射：
   - `reasons`：`polarity=negative` 或 `stage∈{not_yet,suspended,discontinued}` 或 `modality=uncertain` → 加
     `operating_state_boundary`；`activity=business_relationship` 且 `stage∈{contact_established,intended_cooperation,planned,conditional}`
     → 加 `business_relationship_stage`。
   - `topics`：基础 `core_business`；`activity∈{production,capacity}` 且 positive+current → `capacity_projects`；
     `stage∈{planned,conditional,intended_cooperation}` → `new_business`。**否定/非进展状态不得带 `business_progress`**。
   - `score`：普通有界分（沿用 `max(fact.score, 3)` 量级），不因否定词数量放大。
3. 移除 reading-only 的 `_OBJECT × _ACTIVITY` 裸共现分支（`narrative_business_policy.py` 约 534 行
   `activity = any(_OBJECT.search(clause) and _ACTIVITY.search(clause) ...)`），旧 `detect_business_fact`、
   N6 识别与显式 0.8 重放保持不动。
4. `READING_BUSINESS_POLICY_VERSION` 6→7，沿用现有 inventory import，加一条真实 inventory/freezer/comparator 缓存失效断言。
5. 角色准入留在来源/结构边界：本组件角色无关，问句排除是文本语气级（问：/哪些/有没有/？等）；
   question/shadow 仍按现有 `_admitted` 拒绝。`context_unit_ids` 传同 parent 已观察上下文（如 m41 兄弟），
   不裁剪 QA 闭包成员。

## 已知限制（详见 handoff.json known_limits）

- `assertion_refs` 是子句证据跨度（尾部可含"的情况"等未绑定成分）；绑定关系只看组件 refs。
- 主体类别只有四值：股东/控股股东/母公司/子公司/关联方→`quoted_related_party`，供应商/客户/第三方→`other`，
  发行人代词→`issuer`，裸名→`unknown`；股东与子公司的区分靠 `actor_refs`。
- 无指代的"没有。/No. /不便评论"不产关系；跨单元指代闭合不做猜测（参考设计允许把该接口变更报给 ROOT）。
- 不解析数量/期间/币种。

## 未做（STOP 声明）

原件重放、真实选择/完整 QA/预算与历史 0.8 回归、真实摘要、下游 RF 验收、另一公司真实 holdout、
版本号 bump 与缓存失效——均由 ROOT 接收后执行。本卡 0 生产写入、0 供应商调用。**提交后 STOP 等 ROOT 接收。**
