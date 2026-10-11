# Slide 7 原文解析缺口根因调查

## 结论

**遗漏发生在 OCR 识别及低分过滤阶段；未实施修复。** 原图完整，检测器有框，但识别成乱码并被过滤；切片器没有收到这两行。

原件是 PPTX（4,016,522 字节），SHA c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4。slide7 媒体为 ppt/media/image7.png（331,246 字节），SHA d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea。

| 层 | 真实结果 |
|---|---|
| 输入 | 2560×1440 全图；无 PPTX srcRect；全局预处理比例1/1、padding0 |
| 检测 | 25 框，包含两条缺失业务定义 |
| 识别 | 25 非空结果；两条定义是乱码 |
| text_score0.5 | 删除3项：两条乱码及无关 bullet |
| 返回/归一化 | 22行，文本/框/置信度与旧replay逐条完全相同 |
| 两版selector | 均选13/22；缺失业务行此前已不存在 |

## 两条实际缺失的业务定义

- 首行框 [94,177,2320,216]：原图可见 Agents and Infra、Microsoft Cloud、productivity and server licensing；识别为乱码，score **0.43236**。
- 另一行框约 [150,763,1719,805]：原图可见 Productivity and server licensing、licensing offerings across our products；识别为乱码，score **0.44278**。
- 第三个低分项只是单独 bullet，score0.45808，不当作业务缺失。

图像人工读取只作诊断，未补入 normalized text / EvidenceSpan / 摘要。**不能直接降低全局阈值：会放进乱码。** 逐框角度和识别输入张量此次没有保存，所以错误180°旋转、模型权重、字典或英语模型等更细原因仍为未知，不冒签。

## 配置与执行

生产 OCR 配置、三份既有 CPU 模型和参数均保持。config SHA 3ef4d36adff892e66115271a15e3e73dd20a530af615e24d80cdb35f4cf20105；fingerprint 7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d；RapidOCR3.8.1 / ONNXRuntime1.26.0。

首次观测器因 det.scores 为 list 却调用 .tolist() 失败，真实 AttributeError 已保留。ROOT 仅授权修观测器兼容后额外重跑同一页一次，成功 **14.806秒**，60秒硬截止、禁网络；成功即停止。另一次报告构建因 Windows probe 文件为 CRLF、重建误用 LF而断言失败，未写任何报告或产品；随后精确 CRLF 重建验 SHA。

本调查 2 次本地 CPU 推理尝试，1 次成功；**0 HTTP、0 外部供应商、0 真实 token/费用**，母预算不变。不是其他页试验，也不是吞吐性能基准。

## 系统性修复建议

1. 现有 OCR quality 诊断保留被过滤区域的框、分数和阶段计数及来源身份，维持 recall_status=unverified / coverage_complete=false。recognized 不代表完整。
2. 对业务关键不可读区域设计有限本地 ROI 重放，检查角度/裁切，保存变换与偏移的回放身份。不得加公司短语补丁、编造文字或直接降低阈值。
3. TDD 框住低分诊断、全图/ROI 来源与框定位，真实单页两条定义正确恢复或明确不可读；正确文本继续可用，不增加逐材料审批。
4. 修复后在既有大节点 G2/G4 跑 raw/media→unit→切片→摘要引用→RF 实用，不能引用实际证据中不存在的定义。这份调查不提供 G2 或经济质量 PASS，也不阻断其他可用文本。

## 证据与恢复

report.json 保存完整成功 det/rec/filter 观测、真实初次异常、源/媒体/配置 SHA、命令/字段、旧 replay 对照及修复细则。原 probe 可按报告的 CRLF 序列化方法重建，SHA ed8771fbc8dcc82b8c6de5cbefc5492ca1f034d81ba92393380c43e504316498。

阶段数据已保存后，将核验独占 TEMP 的绝对路径及三个文件 SHA，逐文件删、再删空目录，恢复原先不存在状态。最终实测见 JSON cleanup；原 mFresh / mW03 / w4p 原件不删除。失败沙箱 TEMP 的精确任务前缀匹配为0。源身份/发布日期不猜测、不改写。调查未修改产品、配置、旧报告或共享PWF。

最终恢复实测：RESTORED_VERIFIED。首个 PowerShell 路径父目录检查参数不兼容，删除前即停止（0文件删除）；改为静态路径 API 后，核对三个文件 SHA 并逐文件删除，再删空目录。未用递归删除，独占目录现已不存在；全部有限输入 SHA 不变。调查已 STOP。
