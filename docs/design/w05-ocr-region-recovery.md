# W05 OCR 图片正文缺失区域：诊断与有限恢复设计

- 日期：2026-10-11；分支 `codex/w05-cwp-ocr`（起点 `159b993e`）
- 输入根因：`docs/handoffs/w05-cwp-ocr/input/slide7-root-cause.{json,md}`
- 实验证据：`docs/handoffs/w05-cwp-ocr/scratch/locate-cause.json`（13 次本地 CPU 推理，0 网络/0 费用）

## 1. 实际观察到的机制（实验实证，非推测）

RapidOCR 3.8.1 / onnxruntime 1.26.0，配置 `config/local_ocr.json`（SHA `3ef4d36a…`，未改）：

1. **rec 不压缩宽行**：crops 按 w/h 排序分 batch（`rec_batch_num=6`），batch 张量宽度 = `48 × max(320/48, 批内最大 w/h)`，每行等比 resize 到 h=48 后 zero-pad（`ch_ppocr_rec/main.py::resize_norm_img`）。2226×39 的行以 ~2736×48 进入 rec。纯宽度不解释失败（2264 宽的普通行 0.987 通过）。
2. **引擎过滤在 CWP 之外**：`main.py::filter_by_text_score` 在引擎内部按 `Global.text_score`（0.5）删除低分行，被丢弃区域对 adapter 不可见。`RapidOCR.__call__` 支持 per-call `text_score` 覆盖，构造期 `Global.text_score=0.0` 等价（`update_params` 会持久改状态，故只在构造期设置，调用期不再传）。
3. **失败绑定全图管线**：slide7 image7（2560×1440）全图模式下，两条业务定义行 det 有框、rec 乱码（0.43236/0.44278）。**同一区域轴对齐 margin 裁剪（上下各 ~35% 行高）后隔离重识别，两条均以 ≥0.986 正确读出**；cls 开/关、灰度+autocontrast、2x、rot180 隔离下同样可读。⇒ 排除"内容不可读"、"cls 单独致因"、"极性单独致因"。批内张量几何/透视裁剪具体环节未逐一仪表化，记为**未完全隔离的内部细因**；交付的恢复 seam 不依赖该细因的最终解释。
4. **det 前垂直黑边 padding**：w/h>8 或 h≤30 的整图输入触发（ROI 直传也会触发），对结果无碍但记录于机制理解。
5. **cls**：每 crop 压扁到 48×192 分类 0/180，>0.9 才翻转；实验中未观察到其对两条行的独立影响。

## 2. 诊断接口（local_ocr.py）

`ImageOCRResult` 增加默认 `None` 的 `region_diagnostics: OCRRegionDiagnostics | None`：

- 旧三参数构造 `(width, height, lines)` 与旧 fake adapter 完全兼容；`None` 表示后端不提供诊断。
- `OCRRegionDiagnostics(schema="cwp-ocr-region-diagnostics/1")`：`detected/recognized/accepted`（int 或 null；真实 adapter 的 detected=null——该 seam 不可见 pre-rec 计数）、`dropped: tuple[OCRDroppedRegion]`（box[3 位小数]/confidence[6 位]/text[规范化乱码，仅诊断]/reason="low_text_score"）、`recovery: tuple[OCRRegionRecovery]`（恢复编排写入：region box、status、每次 attempt 的 transform/params/结果、recovered_text/box/confidence）。
- 乱码只存在于诊断，绝不成为 EvidenceSpan/unit 文本；`recognized != 完整 recall`，`coverage_complete=false`/`recall_status=unverified` 不变。

引擎侧：构造参数 `Global.text_score=0.0`（下限），CWP 用 `config.text_score`（0.5，生产 config 不动）在同一位置过滤；净行为与旧 25→22 逐条一致（实验 E0 已证）。

## 3. 有限恢复（新 ocr_region_recovery.py）

**ROI 选择**（低分+几何+通用文本信号，不含投资语义）：reason=low_text_score、`0.2 ≤ score < text_score`、宽≥120px、高≥12px、aspect≥2.0；按 (-confidence, box) 排序取前 4 region/image。（真实页 "·" bullet 宽 69px 被排除；两条业务行 0.432/0.443 入选。）

**变换梯子**（确定性，每 region ≤2 attempts、每 image ≤8 attempts）：

1. `roi-margin-crop/1`：box 上下各扩 35% 行高（钳制图内）轴对齐裁剪，隔离重识别。坐标回映射 = 平移。
2. aspect≥4 → `split-stack/1`：亮度列投影找空白间隙（dark<200，逐 2 行采样，gap≥5px），按 target_ratio 6.5 切块、1:1 纵向堆叠（8px 间隔）单次识别，按 chunk 行偏移回映射；无间隙处强制切分并记录。aspect<4 → `upscale-2x/1`（LANCZOS 2x，回映射带 0.5 缩放）。

**验收（不降阈值）**：恢复行必须 `score ≥ text_score`（0.5）。margin-crop 返回多行时按 y 中心落在 region 内选行，全部通过才接受，text 以空格连接、box 取并集、confidence 取 min；split-stack 全部非微小块（宽≥40px）通过才拼接（实验证明该规则拒绝碎词乱拼）。失败 → region 状态 unrecovered，作为质量 flag 上抛，不阻断原文与其他正确行。

**去重（不删正确行）**：恢复行 box 与既有 accepted 行 box IoU>0.5 或被包含 → 不新增（原行优先）；恢复行之间同理；永不删除/修改既有行。

**预算（请求级累计，不逐 image 重置）**：每次 attempt 的 crop 像素计入 composer 的共享 `pixels`（`max_total_pixels` 累计强制）；attempts 与 ROI 像素在请求级 RecoveryBudget 累计上报；deadline 用 `OCRLimits`（尝试前检查 + 原生返回后检查）。**不引入独立请求级 attempt 上限**：否则全量 enrich 与 replay 选定 media 子集会产出不同恢复结果，破坏 replay 元数据全等校验（replay.py 只读）。

**指纹/缓存**：`LocalOCRConfig.identity_manifest` 增加 `region_diagnostics`、`engine_text_score_floor: 0.0`、`region_recovery`（常量键）→ fingerprint 变化 → 旧缓存不能冒充新产物。`PPTX_OCR_PARSER_VERSION` 保持 2.0.0：replay.py 的 `version=="2.0.0"` 分支与 locator 正则（`cwp-pptx-image-ocr/1|…|ocr=<64hex>|l=…|b=…`）只读且必须原样兼容；缓存失效职责由 fingerprint 承担。raw/source_id 不变，旧解析版本不覆盖。

**无全局状态**：无跨 worker 的全局 hook/engine；RecoveryBudget 是单次 enrich（单请求）内的普通对象。

## 4. 组合（ocr_composition.py）

- 恢复在 unique-media cache-miss 分支内执行（同 media 多次出现只恢复一次，attempt 计数一致）。
- `lines = result.lines + recovered_lines`；恢复行 unit：kind `pptx_image_ocr_line`、locator 延续同一 schema 与 `l=` 连续索引、flags 增 `ocr_recovered`（低于 low_confidence_threshold 再加 `low_ocr_confidence`）、metadata 增 `ocr_recovered: true`；坐标=映射回的原图 box；`ocr_confidence`=合并 min。
- page/image 记录与文档级 `ocr` 元数据上报：dropped/recovered/unrecovered 计数、attempt 记录（transform/params/每行结果）、ROI 像素与累计 attempts；未恢复 region 不改变 page_status 语义、不阻断。
- 全流程确定性：同 bytes+同 adapter ⇒ 同 crops/同 attempts/同 metadata（replay 全等校验的前提）。

## 5. 未证实/不声称

- 批内 `max_wh_ratio` 张量或透视裁剪 warp 哪个具体环节产生乱码：未仪表化，不声称。
- cls 对 48×192 压扁输入的误翻行为：未观察到独立作用，不声称。
- 不改生产 config/模型/site-packages；不下载模型；无云 OCR/LLM；恢复行不过阈值不进正文。
