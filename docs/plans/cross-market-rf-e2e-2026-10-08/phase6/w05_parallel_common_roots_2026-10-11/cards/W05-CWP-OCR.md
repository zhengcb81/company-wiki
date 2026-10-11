# W05-CWP-OCR：图片正文缺失区域诊断与有限恢复

**可立即开工。** 已创建工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr`；分支 `codex/w05-cwp-ocr`；起点 `159b993e2f4d36c7e86dc12c9d6028f4a31b353a`。给一个独立harness本文件即可。先读树内AGENTS.md、pyproject.toml、本文、`docs/handoffs/w05-cwp-ocr/input/`；本线PWF用 `.planning/w05-cwp-ocr/`，不新建共享root计划、不重置别人的树。

## 实证与完成标准

微软FY27 Segments and Investor Metrics.pptx slide7是整页图片。原图有两行业务定义，检测器已找到；识别器输出乱码，分数0.43236/0.44278，经0.5过滤后25行变22行。旧回放与本次结果逐条相同。问题在来源OCR识别与质量反馈，不在selector。

交付实际来源层修复：保留未读清区域的诊断、有限本地重新识别、成功正文的原位置与指纹。两条真实原图定义正确恢复是本卡完整验收目标；只做到具体缺口诊断而未恢复则交付PARTIAL。其他正确行仍可使用。

不得简单降低阈值把乱码当正文，不手录答案进产品、不按公司名/页号/金句特判。更细角度分类/recognizer输入原因尚未查明，先有限实验定位。读现有config/model/runtime，不猜权重、不改site-packages、不下载新模型、不用云OCR/LLM，本卡收费0。

## 精确输入与排他写集

工作树 `docs/handoffs/w05-cwp-ocr/input/inputs.json` 给持久原件SourceRef、replay-config及SHA；经已有SourceVersionReader只读取精确原件。Windows长路径用给定extended path，不搬原件。PPTX SHA `c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4`，4,016,522B；`ppt/media/image7.png` SHA `d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea`，331,246B。独立root-cause JSON/MD随input提供。

可写产品：

- `src/company_wiki/document_normalization/local_ocr.py`、`ocr_composition.py`；可新增同目录 `ocr_region_recovery.py`。
- `src/company_wiki/document_normalization/units.py` 仅OCR parser版本常量，旧non-OCR版本不变。
- `tests/document_normalization/test_local_ocr_adapter.py`、`test_local_pptx_ocr.py` 和新 `test_ocr_region_recovery.py`、`test_ocr_region_composition.py`。
- `.planning/w05-cwp-ocr/`、`docs/handoffs/w05-cwp-ocr/`、新 `docs/design/w05-ocr-region-recovery.md`。

禁止写 `source_catalog/narrative_*`、scripts/config.py、生产config、source_contract、AUTO、scheduler、CI/gate。ROOT当前正做业务分类/预算/LLM配置，文件绝不重叠。pptx_parser调用入口只读。需要越界时报告精确接缝与反例，ROOT负责接线。

## 公共接口

保留 `OCRAdapter.transcribe(data, *, limits) -> ImageOCRResult` 和旧OCRLine构造。ImageOCRResult可增加默认空的 `cwp-ocr-region-diagnostics/1` 质量诊断，旧fake adapter/三参数构造继续兼容。至少表达：detected/recognized/accepted计数（backend未知为null）、未读清box、confidence、原因、恢复状态及每次变换/参数/结果。乱码仅在诊断，不能成为事实EvidenceSpan；`recognized`不等于recall完整。

按低分、几何及通用文本候选信号选ROI，不读RF投资语义；最多每image4个region、每region2次额外尝试、image合计8次额外识别。所有恢复计入原总像素/时间额度，不逐次重置；composer须累计整个请求的ROI像素及尝试，不能每个image重新拿完整额度。记录缩放/裁剪/角度与回映射；不要持有可跨worker共享的全局hook或engine。

新算法必须进入有效parser/adapter指纹，旧缓存不能冒充新产物。生产config不改，可增加稳定算法revision；不是许可flag。raw/source_id不变，旧解析版本不覆盖。恢复unit的bbox映射回原media/slide，带source/media/config/变换指纹和真实locator。相邻/重叠ROI去重不能删掉原正确行或乱拼碎词。未恢复region作quality flags，不阻断原文打开或正确文本。

## TDD与三个大节点

### A：根因、设计和真正RED

先保存基线25→22实证，写fake-backend失败反例证明过滤区域诊断缺失；写ROI几何、去重、预算反例。导入错误/缺依赖不是业务RED。设计稿记录实际观察到的角度/输入机制及未知，不先拍脑袋换模型。

### B：实现及集中单元/集成

单元矩阵：低分/空白/单bullet；越界/NaN；90/180度/缩放/padding坐标回映射；重复ROI；旧adapter；恢复第二次前预算耗尽；原生返回后deadline；engine失败；拒网络。ONNX不能合作中断时用隔离进程硬截止，不能把挂起写PASS。

集成必须正常PPTX parse→enrich_pptx→NormalizedDocument，composer实读新诊断与恢复正文，验证坐标/指纹/quality/有界输出；不只测helper。集中运行：

```powershell
python -B -m pytest -q tests/document_normalization/test_local_ocr_adapter.py tests/document_normalization/test_local_pptx_ocr.py tests/document_normalization/test_pptx.py tests/document_normalization/test_ocr_region_recovery.py tests/document_normalization/test_ocr_region_composition.py
```

保留旧断言，正常lint/hooks，不扩每小步全仓慢contract。

### C：真实单页端到端及交接

SourceVersionReader→精确PPTX/media→实际当前本地OCR→正常compose；单页硬截止90秒，保存超时/退出状态。两条定义读对，locator可回开，原22条有效行不新增乱码/不丢信息。目视golden只用于独立expected，不能进入生产代码。另两个非微软中/英文小图测通用几何/低分机制；合成图标synthetic，不能替代真实页验收。

初末原件/media SHA不变；独立scratch初始清单记录，结束只删本线owned临时crop/dump，恢复原样，保留关键小日志/质量JSON/必要ROI图片≤2MiB。真实ONNX测试放手动工程E2E，不每commit默认跑。按工作树内input/handoff_contract.md给JSON/MD/manifest、真实RED/GREEN/E2E、普通commit和剩余项；不安装/推主线。

ROOT收尾做raw→units→W04selector→summary引用→RF实际用途联调。你不等业务分类worker，不写其叶子；工程绿不等于公司研究通过。只在这三个大节点审查，不新增小节点签收。
