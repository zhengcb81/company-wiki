# W05-CWP-OCR 发现记录

## 代码阅读结论（2026-10-11）

1. **rec 宽行机制**（rapidocr 3.8.1 `ch_ppocr_rec/main.py`）：crops 按 w/h 排序分 batch（rec_batch_num=6），batch 内 `max_wh_ratio=max(320/48, 批内最大)`，`resize_norm_img` 把每行 resize 到 h=48、w 等比（≤48×max_wh_ratio）再 zero-pad。**宽行不压缩**——2226×39 会以 ~2736×48 进入 rec。纯宽度不是两条乱码行的充分解释（同行宽 2264 的普通行 score 0.987 通过）。
2. **cls 机制**（`ch_ppocr_cls/main.py`）：use_cls 默认 true；每 crop resize 到 48×192（宽行横向压扁）分类 0/180；label "180" 且 score>0.9 才翻转。宽行被压扁后误判 180 是候选细因之一。
3. **det 前垂直 padding**（`utils/process_img.py apply_vertical_padding`）：w/h>8 或 h≤30 时上下补黑边到 new_h=max(w/8,30)*2。ROI 直接进引擎会触发该机制。
4. **引擎 per-call 覆盖**（`main.py __call__`）：`text_score/use_cls/use_det/use_rec/box_thresh/unclip_ratio` 可按调用覆盖，但 `update_params` 会**持久改引擎状态**，之后每次调用都须显式传参。
5. **引擎 0.5 过滤在 CWP 之外**：`filter_by_text_score` 在引擎内部执行（`main.py:329`），被丢弃区域对 adapter 不可见。把引擎构造为 text_score=0.0（下限），CWP 侧用 config.text_score 同阈值过滤，净行为不变且丢失项可见。
6. **replay 接缝（只读）**：`replay.py:67` locator 正则固定 `cwp-pptx-image-ocr/1|s=|p=|m=|ocr=<64hex>|l=|b=`；`_parse` 只认 version=="2.0.0" 走 OCR 分支。⇒ **不能 bump PPTX_OCR_PARSER_VERSION**（会掉进 non-OCR 分支），恢复算法 revision 必须进 `LocalOCRConfig.identity_manifest`（fingerprint 随之变化 → 旧缓存失效）。replay 用同一 `adapter_identity()` 函数，自动兼容。
7. **replay 元数据全等校验**：`replay_units` 比对全部 metadata ⇒ 恢复路径必须确定性（同 bytes+同 adapter ⇒ 同 crops/同变换/同顺序/同 metadata）。
8. **`enrich_pptx` 结构**：unique media 缓存（`cache[digest]`），`pixels` 累计入共享 `ocr_limits.max_total_pixels`；恢复应放在 cache-miss 分支内（每个 unique media 一次），ROI 像素累计入同一 `pixels`。
9. ImageOCRResult 三参数构造 `(width,height,lines)` 被测试/回放广泛使用，新增字段必须带默认值。

## 实验记录（locate-cause.json，2026-10-11，13 次本地 CPU 推理，0 网络/0 费用）

1. **E0 基线**：全图 + 引擎 per-call `text_score=0.0` → 引擎返回 25 条，CWP 侧 0.5 过滤 → 22 条，与 input 根因报告 `normalized_lines` 逐条一致（`e0_accepted_matches_root_cause=true`）。"引擎下限 + CWP 同阈值过滤"方案净行为等价，且 3 个被丢弃项（含两条业务定义行与 "·"）可见。
2. **两条业务定义行在隔离重识别下完全恢复**（margin 轴对齐裁剪，上下各 ~35% 行高边距）：
   - 行1 box[94,177,2320,216] → "We will transition to two reporting segments for FY27. Agents and Infra will include the Microsoft Cloud, productivity and server licensing, and"，score 0.989（含目视词 Agents and Infra / Microsoft Cloud / productivity and server licensing）。
   - 行2 box[150,763,1719,805] → "Productivity and server licensing brings together licensing offerings across our products including:"，score 0.986（含目视词 Productivity and server licensing / licensing offerings across our products）。
   - cls 开/关、灰度+autocontrast、2x 放大、rot180 隔离下同样读出 → 排除“内容不可读 / cls 单独致因 / 极性单独致因”。
3. **细因定位**：乱码绑定于全图管线的 det→透视裁剪→分批 rec 链（批内 `max_wh_ratio` 张量几何/裁剪具体步骤未逐一仪表化，如实记为未完全隔离）；隔离轴对齐 ROI 重识别可靠恢复——即交付的恢复 seam。cls 在 48×192 压扁输入上的行为未被证明为独立致因。
4. **split-stack**：行1 全 8 块通过（0.960–0.999）；行2 目测 1569px 宽强制切分出碎块（"lice"/"nsing" 高分但切词、"+.."/"1.：+"/"1I+:" 低分）→ 证明“全部非微小块通过阈值才接受拼接”的规则能正确拒绝乱拼碎词。
5. E0 36.7s（机器负载波动），单 ROI 调用 2–4.4s。预算：本实验 13 次 + 后续 E2E 计划 ≤4 次。

## 设计决定（依据实验）

- 恢复梯子：attempt1 `roi-margin-crop/1`（margin_ratio 0.35，轴对齐裁剪隔离重识别）；attempt2 按几何分派：aspect≥4 → `split-stack/1`（target_ratio 6.5/gap_rows 8/min_gap 5/dark_thresh 200），否则 `upscale-2x/1`。
- 验收：恢复行必须过与原过滤相同的 `text_score`（0.5），不降阈值；split-stack 要求全部非微小块（宽≥40px）通过才拼接；margin-crop 多行时按 y 中心落在 region 内选行，全部通过才接受，置信度取 min。
- 选择：reason=low_text_score 且 0.2≤score<阈值、宽≥120、高≥12、aspect≥2.0（"·" bullet 宽 69 被排除）；按 (-score, box) 排序取前 4；≤2 attempts/region、≤8 attempts/image。
- 预算：ROI 像素计入共享 `ocr_limits.max_total_pixels`（请求级累计）；attempts 请求级只累计上报、不加独立请求上限——否则 replay 选定 media 子集会产生与全量 enrich 不同的恢复结果（replay 元数据全等校验会炸）。deadline 沿用 OCRLimits。
- 指纹：`LocalOCRConfig.identity_manifest` 增加 `region_diagnostics`/`engine_text_score_floor=0.0`/`region_recovery` 三个常量键 → fingerprint 变化 → 旧缓存失效。`PPTX_OCR_PARSER_VERSION` 保持 2.0.0（replay.py 只读，bump 会掉出其 OCR 分支；fingerprint 已承担缓存失效职责）。

## Node C 实测（2026-10-11）

1. **真实单页 E2E（evidence/e2e-slide7-result.json）**：SourceVersionReader.open_version(purpose=source_export) 经 w04 replay-config 只读 catalog 打开精确原件（SHA/字节数核对）→ ppt/media/image7.png（SHA 核对）→ 当前 LocalOCRAdapter + enrich_pptx（selected_media 单页，正常 compose 入口）。
   - phase1 source→OCR→compose：36.4s（90s 硬截止内，COMPLETED）；phase2 locator replay 回开（新 adapter）：33.5s（90s 硬截止内，COMPLETED）。
   - 原 22 行与 input 根因 normalized_lines 的 text/box/confidence **逐条精确一致**；恢复 2 行定义（0.989/0.990），含全部目视关键词；"·" bullet 保持 not_attempted→unrecovered 质量旗标；coverage_complete=false。
   - replay_units 用新 adapter 重开 2 条恢复行 + 1 条原行：文本/元数据全等。
   - 初末 SHA（PPTX/media/config）不变；0 网络/0 费用。
2. **旧 2s 超时测试冷启动抖动**：`test_parent_hard_deadline_kills_noncooperative_ocr_before_publish` 的子进程需在 2s 内完成冷 import 并进入阻塞；Windows Defender/负载下 5 跑 3 败（entered-native 未写出）。断言语义不变，冷启动容差 2→20s（阻塞 sleep 30>20，仍证明父进程杀死非协作 OCR）。修后 3+3 连绿。
3. **合成小图通用性探针（evidence/synthetic-probe.json，全部标记 synthetic）**：中/英两张非微软合成小图跑真实 adapter + 诊断契约；四档降质（模糊/浅灰/逐字符抖动/低分辨率混叠）均未产生 score<0.5 的 dropped 区域（最低 0.599；另有整行漏检与高分碎读形态）。⇒ 低分分支在非微软内容上的真实演示 = slide7 本身 + fake-backend 单元矩阵；合成降质无法诱导该分支——如实记录为局限，不以合成替代真实页验收。
4. **mypy**：本线修复后新增错误清零（余 6 处 local_ocr.py 既有模式：from_dict **/import-untyped/_engine 可选调用），较基线 9 处净减；ruff 对改动文件全过。
5. **调用账**：定位实验 13 次 + E2E 两次运行（首次 harness 定时器缺陷被迟到定时器覆写状态，重构双阶段后重跑）共 12 次 + 合成探针 4 档共 ~8 次 ≈ 33 次本地 CPU 推理；每次请求内恢复 ≤4 attempts（1 全图+2 ROI），无网络无费用。
