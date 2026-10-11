# W05-CWP-OCR 任务计划：图片正文缺失区域诊断与有限恢复

- 卡片：`docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/cards/W05-CWP-OCR.md`（树内副本 `docs/handoffs/w05-cwp-ocr/input/construction_card.md`）
- 工作树：`C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr`，分支 `codex/w05-cwp-ocr`，起点 `159b993e2f4d36c7e86dc12c9d6028f4a31b353a`
- 输入：`docs/handoffs/w05-cwp-ocr/input/`（inputs.json、slide7-root-cause.{json,md}、handoff_contract.md、manifest.json）
- 收费：0（无云 OCR/LLM、不下载模型、无 HTTP）

## 事实基线（来自 input 根因调查，不重跑也成立）

- PPTX SHA `c02f4ea1…`，media `ppt/media/image7.png` SHA `d4edf090…`，2560×1440。
- det 25 框 → rec 25；两条业务定义行（box [94,177,2320,216] 与 [150,763,1719,805]）识别为乱码，score 0.43236/0.44278；`text_score 0.5` 过滤共删 3 项（含一个 "·" bullet 0.45808）→ 22 行与旧 replay 逐条相同。
- rec 对宽行动态加宽（batch `max_wh_ratio`，非压缩），纯宽度不是必然原因；细因（角度/输入/极性）未定位。

## 节点 A：根因定位、设计、RED

1. [x] 读树内 AGENTS.md/pyproject/卡片/input 全部材料。
2. [x] 读 local_ocr.py / ocr_composition.py / replay.py / units.py / main.py(rapidocr) / process_img.py / rec/cls main.py。
3. [ ] 有界真实实验（本地 ONNX，≤ ~12 次调用）：全图 text_score=0.0 基线 + 两 ROI × {plain, use_cls=False, split-stack, gray/contrast, up2x, invert, rot180} 定位细因，记录 JSON。
4. [ ] 设计稿 `docs/design/w05-ocr-region-recovery.md`（记录实测机制与未知）。
5. [ ] RED：fake-backend 反例（过滤区域诊断缺失；ROI 几何/越界/NaN；去重不删正确行；预算/尝试上限；旧 adapter 兼容）。

## 节点 B：实现与集中测试

- local_ocr.py：引擎 text_score floor=0.0 + CWP 侧同阈值过滤；`OCRRegionDiagnostics/OCRDroppedRegion`（默认空，None=后端不支持）；manifest 增加诊断/恢复 revision 常量（fingerprint 变化即缓存失效）。
- 新 ocr_region_recovery.py：ROI 规划（低分带+几何+通用文本信号，无投资语义；≤4 region/image、≤2 attempts/region、≤8 attempts/image）；确定性变换梯子（按实验结果排序）；坐标回映射；拼接与验收（同 0.5 阈值，不降阈值）。
- ocr_composition.py：composer 累计整请求 ROI 像素/尝试（共享 ocr_limits，不逐 image 重置）；恢复行 unit + 指纹/locator（保持 `cwp-pptx-image-ocr/1|…|l=|b=` 形状以兼容 replay 正则）；未恢复 region → 质量 flag，不阻断。
- units.py：不 bump OCR parser 版本（保持 2.0.0），算法 revision 走 adapter fingerprint（replay.py 只读，bump 会破坏其 version 分支——见 findings）。
- 测试：更新两个既有文件 + 新 test_ocr_region_recovery.py / test_ocr_region_composition.py；集中命令按卡片。
- 集成：真实 parse→enrich_pptx→NormalizedDocument，composer 实读诊断与恢复行。

## 节点 C：真实单页 E2E 与交接

- SourceVersionReader 打开精确原件 → media7 → 当前本地 OCR → compose；单页 90s 硬截止（隔离进程）；两条定义恢复、22 原有效行不变、无新乱码；locator 可回开（replay）。
- 另两个非微软中/英文小图验证通用几何/低分机制（真实图，不替代真实页验收）。
- 初末 SHA 不变；scratch 清理；handoff.json/handoff.md/manifest；正常 commit，不推主线。

## 排他写集遵守

- 只写：local_ocr.py、ocr_composition.py、新 ocr_region_recovery.py、（如需）units.py 版本常量、四个测试文件、.planning/w05-cwp-ocr/、docs/handoffs/w05-cwp-ocr/、docs/design/w05-ocr-region-recovery.md。
- 不写：replay.py、pptx_parser.py、scripts/config.py、生产 config、source_catalog/narrative_*、AUTO、scheduler、CI。
