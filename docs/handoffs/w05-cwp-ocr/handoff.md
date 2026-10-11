# W05-CWP-OCR 交接摘要：图片正文缺失区域诊断与有限恢复

- 状态：**COMPLETE**（两条真实原图业务定义均正确恢复；22 原有效行逐条不变）
- 工作树 `C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr`，分支 `codex/w05-cwp-ocr`，起点 `159b993e2f4d36c7e86dc12c9d6028f4a31b353a`
- 0 网络调用、0 云 OCR/LLM、0 费用；未下载模型、未改 site-packages、未改生产 config。

## 根因（实验证实，非推测）

slide7 image7 两条业务定义行在全图管线 det（有框）→ 透视裁剪 → 分批 rec 中被识别为乱码（0.43236/0.44278），被 RapidOCR 引擎内部 `text_score 0.5` 过滤，组合层与 selector 均不可见。**同一区域轴对齐 margin 裁剪后隔离重识别两条均以 ≥0.986 完整恢复**；cls 开关/灰度/2x/rot180 隔离下同样可读 → 排除"内容不可读 / cls 单独致因 / 极性单独致因"。批内 rec 张量几何/裁剪 warp 的具体致病环节未逐一仪表化，**如实记为未完全隔离**；恢复 seam 不依赖该细因的最终解释。E0 复现：引擎下限 0.0 + CWP 侧同阈值过滤 → 25→22 与旧 replay 逐条一致。

## 真正实现

1. **local_ocr.py**：引擎构造 `Global.text_score=0.0`（下限），CWP transcribe 用 config.text_score 同阈值过滤并产出 `ImageOCRResult.region_diagnostics`（`cwp-ocr-region-diagnostics/1`）：detected/recognized/accepted 计数（detected=null，该 seam 不可见）、dropped 区域（box/confidence/乱码文本仅诊断/原因）、recovery 记录（每变换/参数/结果）。乱码只在诊断，绝不成为行/EvidenceSpan。`identity_manifest` 增加 `region_diagnostics`/`engine_text_score_floor`/`region_recovery` 常量键 → **fingerprint 变化 → 旧缓存不能冒充新产物**。`PPTX_OCR_PARSER_VERSION` 保持 2.0.0（replay.py 只读且其 version 分支/locator 正则必须原样兼容；缓存失效职责由 fingerprint 承担）。
2. **ocr_region_recovery.py（新）**：ROI 选择（低分带 0.2≤score<阈值 + 几何 宽≥120/高≥12/aspect≥2，无投资语义，≤4 region/image、≤2 attempts/region、≤8 attempts/image）；确定性变换梯子 `roi-margin-crop/1`（margin 0.35）→ 按几何 `split-stack/1`（间隙切分+纵向堆叠，全非微小块过阈值才拼接）或 `upscale-2x/1`；坐标回映射（translate/scale/rotate90/180/270/pad/split-stack chunk 表）；验收不降阈值（同 0.5）；恢复行与既有行同文本+重叠或 IoU>0.5/包含即拒（原行永不删）；预算请求级累计（ROI 像素入共享 max_total_pixels；尝试数累计上报但**无请求级上限**——否则 replay 选定 media 子集会与全量 enrich 产生不同恢复结果，破坏 replay 元数据全等校验）。
3. **ocr_composition.py**：unique-media cache-miss 分支内执行恢复（同 media 一次，确定性）；恢复行 unit `pptx_image_ocr_line` + `ocr_recovered` flag + 同 schema 连续 `l=` locator + `ocr_recovered` 元数据；page/image/文档级上报 dropped/recovered/unrecovered（含 not_attempted）/attempt 记录/ROI 像素；未恢复 region 质量旗标不阻断。
4. **测试**：test_local_ocr_adapter.py（扩展）、新 test_ocr_region_recovery.py、test_ocr_region_composition.py；既有断言保留（唯一改动：既有 2s 超时测试冷启动容差 2→20s，阻塞 sleep 30>20 语义不变，理由见 findings）。

## TDD

- RED：23 个业务性失败（诊断缺失/ROI 几何/去重/预算/兼容边界），导入错误不是 RED。
- GREEN：集中命令 59 passed（exit 0）；全目录 129 passed（exit 0）；ruff 全过；mypy 新增清零。

## 真实 E2E（evidence/e2e-slide7-result.json）

SourceVersionReader（w04 只读 catalog，purpose=source_export）→ 精确原件/media（SHA 核对）→ 真实 LocalOCRAdapter → enrich_pptx 正常 compose（单页）→ replay 新 adapter 回开。phase1 36.4s / phase2 33.5s（各 90s 硬截止内，COMPLETED，超时/退出状态已记录机制）。**22 原有效行 text/box/confidence 与根因基线逐条精确一致；两条定义恢复（0.989/0.990，全部目视关键词在内）；"·" bullet 保持质量旗标；replay 全等；初末 SHA 不变**。

合成小图探针（evidence/synthetic-probe.json，标记 synthetic）：中/英两图四档降质未诱导出 score<0.5 分支（最低 0.599，另有漏检/高分碎读形态）——低分机制演示以 slide7 + 单元矩阵为准，合成不替代真实页验收，局限如实记录。

## 清理

scratch 基线（不存在）→ 实验/E2E/探针临时文件 → 关键 JSON/日志/2 张 ROI 图（≤32KiB）移入 docs/handoffs/w05-cwp-ocr/{evidence,logs,scripts}，临时合成 PNG 删除，scratch 目录删除恢复原状；原件/老 TEMP/其他 owner 文件未动，全 SHA 不变。

## 剩余

- 批内 rec 张量/裁剪细因的仪表化归因（非恢复机制所依赖）。
- ROOT 联调（raw→units→selector→summary→RF）在既有 G2/G4/G5 节点做；本卡不给经济质量 PASS。
