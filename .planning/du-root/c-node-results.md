# C 节点：新层对基准金标的效果（实测）

命令：

```bash
python -X utf8 .planning/du-root/c_node_new_layer.py \
  --bindings <本机 bindings> \
  --gold tools/document_understanding_benchmark/gold \
  --output .planning/du-root/c-new-layer
```

证据：`.planning/du-root/c-new-layer/new_layer.json`
预算：与基线相同（普通 96 units，发行类 160 units）。**公平对照**——不靠多选提分。
0 模型调用、0 网络调用。

## 总体

| scope | 基线（现有 selector） | 新层 | 变化 |
|---|---|---|---|
| development（6 份） | 0.220 | **0.384** | +0.164 |
| holdout（5 份） | 0.000 | **0.350** | +0.350 |

## 逐份

| 样本 | 基线 | 新层 | 说明 |
|---|---|---|---|
| cn-equity（恒锋增发） | 0.000 | **0.857** | 计划点名的「建设期」目标，已解决 |
| cn-ir（万润 IR） | 0.143 | **1.000** | 否定与前提同包 |
| holdout-cn-glodon-q1 | 0.000 | **0.800** | |
| holdout-cn-yake-q1 | 0.000 | **0.857** | |
| cn-q-business（中微季报） | 0.667 | 0.444 | **回退** |
| cn-h1（中微半年报） | 0.250 | 0.000 | **回退** |
| holdout-us-nvidia-10k | 0.167 | 0.000 | **回退** |
| cn-ipo-confirmation | 0.000 | 0.000 | 扫描件 0 原生字符，无单位可选（正确） |
| hk-annual（名创年报） | 0.000 | 0.000 | 见下：表格抽取缺口 |
| holdout-hk-alibaba-fy2023 | 0.000 | 0.000 | 18038 units 对 96 预算 |
| holdout-us-mongodb-10k | 0.000 | 0.091 | |

## 三个真实缺陷（实测发现并修复，均有回归测试）

1. **子章节不继承父章节角色**。`第三节 董事会关于本次募集资金使用的可行性分析`
   正确识别为 `fundraising`，但其下 `（一）项目基本情况`/`（二）项目投资计划`/
   `（四）项目建设周期` 等子标题自身不含主题词，全部停在 `unknown`。
   `unknown` 排在所有已知角色之后 → **19 个 project 包全部被 1000+ 散文包挤在预算之外**。
   修复：子章节继承父章节角色，`basis` 记 `role_inherited`；已正面匹配的角色不被覆盖。
2. **包 ID 按 unit_id（内容哈希）排序**，等于随机序，所有基于 ID 的次序都是任意的。
   修复：改用首个成员在输入中的 `ordinal`。
3. **`build_dependency_packages` 默认 `max_packages=400` 静默截断尾部**，而尾部就是文档后段，
   发行说明书的募投项目包因此整段丢失。修复：默认不截断，显式截断时报 `PACKAGE_LIMIT_REACHED`。

## 仍未解决（诚实记录）

**名创门店表（hk-annual）仍为 0.000，已定位到根因**：
真实 parser 把该双语门店表抽取成**退化的单格行**（`'1,093'`、`'3,536'`、`'Total 合計'`），
而不是 `项目 | 投资额 | 建设期` 这样的规整多列行。即使 `full_table_scan=True`
（1283 个 table_row）也**没有产出任何 `operating_table` 包**。
恒锋的募投表是规整多列行，所以 project 路径可用；名创的表不行。
需要表格几何重建（行列由 bbox 反推），属 parser/表格模型工作，不是排序能解决的。

**三份回退**：kind-band 优先让结构化单元挤占了部分散文事实的预算。
这是真实权衡，**不做针对本金标的调参**（计划明令禁止为过基准而改算法），如实报告。

## 仍未测

- 真实模型摘要与语义蕴含（`paid_path=not_run`）。
- `context_completeness` / `role_modality_quantity` 仍是 NOT_EVALUATED
  （基线不产出 route/semantic units）。
- 20 份调查样本是开发集，不是盲测集。
