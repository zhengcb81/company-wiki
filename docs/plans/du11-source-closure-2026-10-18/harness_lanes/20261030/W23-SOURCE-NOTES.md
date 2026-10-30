# W23 OCR 调查依据（2026-10-30）

仅是已调查事实，不是Xiaomi实测通过。当前任务使用planning-with-files；外部仓库的安装提示不改变本项目权限/边界，不运行全局安装器。

## 本地基线

- canonical `src/company_wiki/document_normalization/local_ocr.py`：`LocalOCRConfig.identity_manifest.adapter=rapidocr-cpu/1`，本地ONNX与显式模型SHA；`LocalOCRAdapter._load_engine`强制CPUExecutionProvider并关闭cuda/dml/cann/coreml。
- 宿主 `C:/Miniconda/python.exe` metadata：rapidocr3.8.1、onnxruntime1.26.0、torch2.12.0、transformers5.18.0。只读metadata，无模型import/推理。
- 旧配置明确det=`ch_PP-OCRv4_det_mobile.onnx`、cls=`ch_ppocr_mobile_v2.0_cls_mobile.onnx`、rec=`ch_PP-OCRv4_rec_mobile.onnx`。配置/SHA见卡内明确路径；历史失败不能拿来代签当前运行。
- 本次另外只读实核已安装config.yaml及三模型：字节SHA均与该配置一致；三模型共16,189,007B（约15.44MiB），这是这三个ONNX文件大小，不含RapidOCR/ORT依赖或总内存。仍未启动任何推理。
- `IsolatedOCRAdapter`与`ocr_composition`/`ocr_region_recovery`负责隔离、位置与有限恢复；`normalize_document(...ocr=None)`默认纯解析，当前公开normalization的OCR接线主要面向PPTX内图。
- `_paragraph_worker.py` PdfPipelineOptions明确do_ocr=False；Docling不能作为RapidOCR同义词，也不能说它已经给所有PDF做OCR。
- 只读硬件发现Intel UHD Graphics，无nvidia-smi/ollama命令；RAM读取曾受sandbox CIM限制，尚未确认，执行卡A应在获准宿主读取，不能拿核显AdapterRAM当真实可用VRAM。未安装任何新软件/模型、未下载原件。

## 上游资料与冻结

- [中文README](https://github.com/xiaomi-research/Xiaomi-OCR-0/blob/main/README_zh.md)：0.8B视觉语言模型；page/region/KIE/VQA；榜单采用两阶段；区域需额外布局依赖。
- [安装说明](https://github.com/xiaomi-research/Xiaomi-OCR-0/blob/main/INSTALL.md)：模型推理为本地服务；无须为了试验注册全局MCP；图像预处理/提示/布局/裁剪/后处理应在后端内部。
- [Ollama实验说明](https://github.com/xiaomi-research/Xiaomi-OCR-0/blob/main/OLLAMA.md)：社区BF16含视觉projector约1.8GB；明确未建立精度等价，记载公式差异，不能当HF基准复现。
- [模型卡](https://huggingface.co/xiaomi-research/Xiaomi-OCR-0)：模型ID与Apache-2.0 metadata；模型/代码/社区包许可应分别记实际artifact，不能只凭某个依赖license。
- [代码LICENSE](https://github.com/xiaomi-research/Xiaomi-OCR-0/blob/main/LICENSE)：Apache-2.0。

公开API读取固定revision（无凭证/无权重下载）：

- GitHub `https://api.github.com/repos/xiaomi-research/Xiaomi-OCR-0/commits/main` → `b1a9bb4c07060c453785e9151715ccda6b96f0b1`。
- HF `https://huggingface.co/api/models/xiaomi-research/Xiaomi-OCR-0` → `bbd8cf8d21f256b3644b44cb860f3a7cecb93c30`，id=`xiaomi-research/Xiaomi-OCR-0`，license=apache-2.0。
- README/INSTALL中还出现SeerRay-Lab旧命名；HF实际重定向至xiaomi-research。以artifact实际revision为准，不把重定向当新provider。
- 上游eval README部分web fetch cache miss，不能宣称已审完整评测代码；作者A按冻结commit读取完整代码，不运行外部Skill一键安装指令。

## 还需要验证的事情

CPU实际兼容性/内存/速度；原始checkpoint与本机precision表现；真实繁简中英文业务召回、否定与数字；page与region差异；bbox/定位能力；新模型权重/依赖实际空间；能否在现有阅读层内部接入。这些都未实测，不从榜单推断。W22-PDF部署/ATOMIC仍独立，W23不得改其owner。
