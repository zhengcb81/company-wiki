# W05-CWP-OCR 进度

## 状态：三个大节点全部完成，待 ROOT 审接口并合并

| 节点 | 内容 | 状态 |
|---|---|---|
| A | 根因定位（13 次本地推理实验）、设计稿、真 RED（23 个业务性失败） | 完成 |
| B | local_ocr 诊断 + ocr_region_recovery + ocr_composition 实现，集中套件 GREEN | 完成 |
| C | 真实单页 E2E（两阶段 90s 硬截止）、合成小图探针、清理、交接 | 完成 |

## 关键实证（详见证据 JSON）

- **细因定位**：两条业务定义行在隔离轴对齐 margin 裁剪下以 ≥0.986 完整恢复（cls 开关/灰度/2x/rot180 均可读）；乱码绑定全图 det→透视裁剪→分批 rec 链路（批内张量/裁剪具体环节未逐一仪表化，如实记未完全隔离）。
- **E2E**：22 原有效行逐条精确不变 + 2 条定义恢复（0.989/0.990）+ "·" bullet 质量旗标 + replay 新 adapter 全等回开 + 初末 SHA 不变。phase1 36.4s / phase2 33.5s（各 90s 硬截止内）。
- **合成探针**：四档降质未诱导出 score<0.5 分支（最低 0.599），低分机制演示以 slide7 + 单元矩阵为准，如实记局限。

## 测试

- 集中命令（卡片指定）：59 passed（logs/green-focused-suite.log，exit 0）。
- 全 document_normalization 目录：129 passed（logs/green-full-suite.log，exit 0）。
- RED 阶段：23 failed（业务反例），实现后全绿；旧断言保留，唯一改动是既有 2s 超时测试的冷启动容差 2→20s（断言语义不变，理由见 findings）。
- ruff（改动文件）全过；mypy 新增错误清零（余 6 处既有模式）。

## 待办（ROOT）

- 审接口并合并本分支；raw→units→W04 selector→summary 引用→RF 用途联调在既有 G2/G4/G5 大节点做。
- 批内 rec 张量/裁剪的更细归因（未完成，非恢复机制所依赖）。
