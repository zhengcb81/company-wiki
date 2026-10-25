# W17 ROOT 独立最终复审

**结论：APPROVE（工程组件接收）。未解决的本范围 finding：0。** 初审与两轮中途 REQUEST_CHANGES 证据全部保留；本结论不签来源真值、摘要语义或公司 RF。

- 候选：`C:/Users/郑曾波/Projects/revenue-forecast-audit-w17-root-acceptance`。
- 分支：`codex/root-w17-acceptance-20261025`，基底 `7c71c8111f14a3aae6a1df274eeffb81c01939b7`。
- ROOT 修改尚未提交；本复审绑定下列实际文件字节 SHA，不能把基底 commit 当作含修复的代码 commit。后续正常提交若字节相同，可直接据此核对。

## Findings 处置

| Finding | 最终处置 | 实证 |
|---|---|---|
| ROOT-W17-F1 | FIXED：共同scope提取保留各carrier自身身份，显式foreign/矛盾及未关联selection引用为unknown/unrelated；RF run+attempt联合比较，保留每doc原状态。 | cross-run-real-artifacts (earlier replays + final real replay)；review-references-unassociated-selection；nested-reviewed-scope-foreign-attempt；contradictory-nested-run-scope；matching-review-and-selection-positive；same-run-multi-document-positive |
| ROOT-W17-F2 | FIXED：未知或非string schema不参与已知selection语义；报告保留scope_binding与诊断，不拒整import。 | unknown-selection-schema；model-schema-array；selection-schema-object |
| ROOT-W17-F3 | FIXED：显式空列表为观测0，声明与观测不一致及omitted超过candidate均给conflict，raw不修。 | explicit-empty-selection；omitted-over-candidate |
| ROOT-W17-F4 | FIXED：几何锚要求实际有效值，bbox:null不再available，文字可读性独立。 | null-bbox-with-readable-text；ROOT null/invalid geometry test |
| ROOT-W17-F5 | FIXED：可选非object/非法schema形态安全归一化并报告unknown；其余维度继续导入。 | malformed-model-json-array；model-schema-array；selection-schema-object |
| ROOT-W17-R1-selectionSHA | FIXED：selectionSHA仅代表实读selection文件SHA，与producer selection_sha256分开；无对应文件unknown、冲突unrelated，精确正例仍observed。 | same-source-old-review-selection；matching-review-and-selection-positive |
| ROOT-W17-R2-transitive-scope | FIXED：SHA相等不能覆盖所引用selection的foreign来源；继承已算出的关联结果。 | review-references-unassociated-selection |
| ROOT-W17-R2-nested-scope | FIXED：已知容器中的run/attempt统一提取；嵌套旧scope和矛盾scope不会被当前CLI覆盖。 | nested-reviewed-scope-foreign-attempt；contradictory-nested-run-scope |

## RF 索引范围判断

同 run、同 attempt 的 `audit-status-index/1` 可以作为该运行的多文档原始状态观察。当前输出保留索引自己的 applies_to、每个 document_id/source_id，以及分开的 prepared/read/use 状态，因此足以报告索引；它没有宣称所有导入 bundle 已被 RF 采用。不同 run 即使 attempt 标签相同也保持 unknown。无需新增 bundle 身份库、逐文档 gate 或强制过滤。

## 最终独立执行

- 最终收据：`C:\Users\郑曾波\Projects\company-wiki\.planning\w16-w17-root-acceptance\review-w17\approved-final-5e720801/receipt.json`。9 个定向反例/正例与 5 步完整 CLI 共 **14 条命令**，全部 exit 0，独立断言全部通过；前后 7 文件 SHA 稳定。
- 覆盖：引用 foreign selection 的 review、嵌套旧 scope、非 string schema、精确同源 selection SHA 正例、矛盾 scope、同源未关联模型请求、同 run 多文档 RF、foreign run RF。
- 完整链：import → prepare source → 冻结独立 targets → prepare output → attach-review → compare。附审前两条 claim 均 `not_reviewed`，比较输出 `no_total_score=true`。
- 最终代码另做 1 条冻结真实公开产物回放（收据 `frozen-real-replay-receipt.json`）：HTML bundle 的 native_scan unknown、annual14 外部 review unknown、W15 foreign-run RF unknown、claims not_reviewed；不再把不同载体汇成当前公司事实。
- 7 项真实输入在回放后核 SHA 全部保持原值。HTML/stub-model 契约产物、真实 annual14 源侧观察、W15 示例的出处分别保留，fixture 正例明确是中性工程输入。
- ROOT 的最终 W17 定向测试日志 `w17-root-scope-final.log` 为 **59 tests OK**（exit 0），本 reviewer 已实读日志与收据。未重复 737 全量。

## O01–O08

| ID | 结果 | 证据 |
|---|---|---|
| O01 | PASS | 公开字段及版本解释受schema识别约束；未知/非string schema与缺失字段不会制造current观察，新增selectionSHA与producer selection_sha256语义区分。 |
| O02 | PASS | 单一owner、六维、raw/status/指针/SHA与载体自身scope；未关联selection不合并，review/model外部声明不冒充当前bundle。 |
| O03 | PASS | legacy原值保留且解释unknown；原类型/负数/超界诊断保留，ROOT新增空列表和omitted超分母反例变conflict，未作事实遗漏减法。 |
| O04 | PASS | null bbox不算几何可用；文字独立；源侧金标不升级摘要，v5 task不折算自然语言claim，附审前claims not_reviewed。 |
| O05 | PASS | run+attempt联合比较；same-run多doc索引作为自身逐doc状态可观察，foreign run unknown；prepared/read/use verbatim不升级，不声称当前bundle采用。 |
| O06 | PASS | 可选shape/schema冲突均报告型；有效bundle继续，quality_status not_evaluated、无overall/许可/新库；复用有界读取和既有hash。 |
| O07 | PASS | 最终59 W17测试ROOT收据；reviewer最终9个定向反例/正例及5步真CLI链全exit0并独立断言，另最终1条冻结真实回放；旧DU5链仍通。 |
| O08 | PASS | 最终代码真实公开载体只读回放，7项输入SHA复核不变。HTML stub、annual14 selection/review、W15 example各自scope区分，不能绑定的维度unknown，claims not_reviewed。 |

## 最终实际文件 SHA-256

| 文件 | SHA-256 |
|---|---|
| `skills/revenue-forecast-audit/scripts/coverage_observations.py` | `7914c0da7166e4397e8b2219b29cedde0360413616ea1f17c64f0e3db5e93998` |
| `skills/revenue-forecast-audit/scripts/summary_review_import.py` | `860af26a38bdfa03bc2a11932624c35c4cc822498763775dd12d48a4f6ff8aee` |
| `skills/revenue-forecast-audit/references/coverage-observations.md` | `64dd4e8748b726d37f115c4521a4051577c1e274217a1c366a42e8ce63a347ca` |
| `skills/revenue-forecast-audit/SKILL.md` | `5124273299b4310431a885eadb5a9d834d3aa82b6848be413b0f17c308e5ad21` |
| `tests/test_w17_coverage_observations.py` | `15ea23c6db516b6118debdf5e2f8f70947b614c2e3853c303882105d06a37fd7` |
| `tests/test_w17_import_wiring.py` | `b6158983f185fcd929d4f876bc357e0b1e00b17f3f7567c1a3db428a92766ae3` |
| `tests/test_w17_root_scope_integrity.py` | `b53986af424d0620d728cd6d61c86c7020f9f107c4d9133630744fc7076dc707` |

## 保留证据与边界

- 初审 `w17-independent-review.md/json` 保持原样；作者 initial/final 独审和原失败报告没有改写。各轮失败输入、输出与命令收据保留在 reviewer 自有 scratch。
- 最终 JSON 还绑定全部 fixture SHA、初审文件 SHA、ROOT 59 测试日志及 14 命令收据 SHA；真实输入 SHA 在最终回放后复核。
- reviewer 未修改作者、主仓或候选产品，未 checkout、安装或建索引；模型、下载、外网调用均为 0。
- 所有新增检查仍是报告型：绑定不足保持 unknown/unrelated，冲突只给对应诊断，原始来源/声明保留；没有新增人工许可、身份台账、摘要 PASS 或整体业务验收。
