# C 节点：新层对基准金标的效果（实测，最终）

两侧都在**同一份 15 记录金标**、**同一证据预算**（普通 96 units，发行类 160 units）下测量。
0 模型调用、0 网络调用、0 免费额度。

复跑：

```bash
# 基线（现有 selector）
python -X utf8 -m tools.document_understanding_benchmark --mode native \
  --bindings <bindings> --output .planning/du-root/bench-native2

# 新层（ROUTE 适配 + structure + packages）
python -X utf8 .planning/du-root/c_node_new_layer.py \
  --bindings <bindings> --gold tools/document_understanding_benchmark/gold \
  --output .planning/du-root/c-new-layer
```

## 总体

| scope | 基线 | 新层 | 变化 |
|---|---|---|---|
| development | **0.175**（10/57 critical，10 份） | **0.324**（9 份计分） | +0.149 |
| holdout | **0.000**（0/22 critical，5 份） | **0.350**（5 份计分） | +0.350 |

分母说明（诚实披露）：基线把若干份记 `n/a`（PARTIAL 且无可计召回）不计入分子分母；
新层有 9/10 份计分（`cn-ipo-confirmation` 是扫描件、0 原生字符，两侧都无证据可选）。
因此两侧分母不完全相同，比较是**近似同口径**，不是逐份配对检验。

## 逐份（基线 → 新层）

| 样本 | 基线 | 新层 | |
|---|---|---|---|
| cn-equity（恒锋增发） | 0.000 | **0.857** | 计划点名的「建设期」目标，已解决 |
| cn-ir（万润 IR） | 0.143 | **1.000** | 否定与提问前提同包 |
| holdout-cn-yake-q1 | 0.000 | **0.857** | |
| holdout-cn-glodon-q1 | 0.000 | **0.800** | |
| cn-q-sparse（世华季报） | 0.000 | **0.444** | |
| cn-q-business（中微季报） | 0.667 | 0.444 | 回退 |
| us-txt（电话会） | 0.091 | 0.091 | 持平 |
| us-20f（TAL） | n/a | 0.083 | 基线不可计 |
| holdout-us-mongodb-10k | n/a | 0.091 | 基线不可计 |
| cn-h1（中微半年报） | 0.250 | 0.000 | 回退 |
| holdout-us-nvidia-10k | n/a | 0.000 | |
| hk-annual（名创年报） | 0.000 | 0.000 | 表格抽取缺口，见下 |
| holdout-hk-alibaba-fy2023 | 0.000 | 0.000 | 18038 units 对 96 预算 |
| us-10k（微软 10-K） | n/a | 0.000 | 新层能解析 HTML，但事实未召回 |
| cn-ipo-confirmation | n/a | n/a | 扫描件 0 原生字符，两侧都无证据 |

## 附带发现：载体覆盖

基线把 `.htm` 载体记为 **UNSUPPORTED**（4 份，含微软 10-K，无路由进现有 selector），
按 UNAVAILABLE 报告而非质量结论。新层经 `document_normalization` 能解析 HTML
（`us-10k` 5215 units）并给出结构，因此**载体层面新层覆盖面更广**；
但该份的关键事实仍未召回（0.000），所以这是「能读」而非「读对」。

## 已定位、未解决

**名创门店表（hk-annual 0.000）**：真实 parser 把该双语表抽成**退化的单格行**
（`'1,093'`、`'Total 合計'`），不是 `项目 | 投资额 | 建设期` 那样的规整多列行。
即使 `full_table_scan=True`（1283 个 `pdf_table_row`）也**产不出任何 `operating_table` 包**。
需要表格几何重建（行列由 bbox 反推），属 parser/表格模型工作。

**三份回退**（cn-h1、cn-q-business、us-nvidia）：结构化单元在固定预算内挤占了散文事实。
这是真实权衡；**未针对金标调参**（计划明令禁止为过基准改算法）。

## 未测

- 真实模型摘要与语义蕴含：`paid_path=not_run`。
- 基准的 `context_completeness` / `role_modality_quantity`：`NOT_EVALUATED`。
- 跨文档变化、峰值 RSS、生产接线。
- 20 份调查样本是开发集；holdout 5 份是独立集，已分开计分。
