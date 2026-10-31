# W22-PDF-DEPLOY handoff

状态：待独审完成后定稿（READY_FOR_ROOT / PARTIAL）。本文件与 `handoff.json`
（schema `harness-handoff/1`）共同交付。

## 交付了什么

一个小型、可重复、幂等的离线 PDF 增强 runtime 部署工具
（`tools/pdf_runtime_deployment/`），把 W21 已验证的 104-distribution 依赖闭包
与模型，用同卷 NTFS hardlink 投影到**纯 ASCII 资源树**，产出符合既有
`pdf-paragraph-runtime/2` 的本地配置，并验证真实生产入口。上层接口不变：
`COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG` 显式选择该配置即可。

## 真实结果（2026-10-30）

| 项 | 结果 |
|---|---|
| 部署目标 | `C:/cwp-runtime/w22-pdf-sdk`（首建，无外来内容；ASCII；C: 同卷） |
| plan | 104 dist / 36,121 env 行 + 6 模型行；plan SHA `327891cf…`；源配置 SHA `bcc42711…`（= W21 接收 review 冻结的 profile 字节） |
| deploy | 36,127 hardlinks，SDK/模型**零字节复制**，scaffold 516,976B，共享逻辑 1,405,313,714B，417s；`environment_sha256=c84a984c…` 与源一致 |
| verify L0 | fresh-process PASS：104 dist 全在部署 site-packages、无 pip/user/base site、ASCII prefix、零 SDK import、closure digest 一致 |
| verify L1 | 生产 `configured_paragraph_runtime()` 加载 PASS，配置逐值同源仅 python/artifacts 为 ASCII 路径 |
| 零写复核 | 同配置二次轻量验证 `zero_write_verified=true` |
| constructor | CONSTRUCTOR_OK 22.748s / 30s（真实 SDK 构造，ASCII artifacts） |
| canonical E2E | **enhanced，accepted_groups=2，rejected_groups=0**；completed [1,2] / stream_complete；worker 17.04s/120s；峰值 3,330,412,544B/4GiB；已知中文资源打开失败**不再发生**；源文本保持；负对照（单字符篡改）仍被拒绝 |
| 对齐诊断 | 真实 SDK 提案 2/2 经未改动的生产 `align_paragraphs` 接受 |

## 两轮诚实记录（C2 首跑 → 修正）

1. 首轮（pymupdf 内置 `china-s` 夹具）：`native_fallback` 于 120s 封顶（生产
   子进程 repo-local pycache 冷编译一次性成本），随后 `unaligned_native_fallback`
   accepted0/rejected2。**未抬任何封顶**；经生产 `child_launch_command` 做
   no-document 预热（13.7s，不作为就绪收据）。
2. 诊断定位：真实 SDK items 文本为乱码 —— 内置 `china-s` 字体无 ToUnicode
   CMap，docling/pdfminer 解码失败（W21 alias 对照 rejected2 同因，非部署/对齐
   层缺陷）。换用带 ToUnicode 的嵌入系统字体夹具（`_synthetic_pdf.py`）后
   accepted2。收据 `w22-synthetic-e2e.json`、`w22-alignment-diagnostic.json`。

## 边界（不在本卡，ROOT 收口）

- 真实公司文档的 C2、主线摘要/缓存/RF：NOT_RUN，归 ROOT。
- 合成文档 `evidence_span_count=0` 属 selector 语义（与 W21 相同），非部署缺陷。
- 环境部署是显式交付物：`C:/cwp-runtime/w22-pdf-sdk` 保留，不得删除后声称可用；
  淘汰时只删 owned 链接名，不沿 hardlink 追删源。
- NTFS 目录/link 元数据分配未精测，不把逻辑 1.4GB 描述为新增磁盘。

## 独立审查

两个独立 agent 并行审查（代码/规范一致性+反例测试；部署环境/硬链接源保护/
磁盘账目）。报告落盘 `delivery/w22-pdf-deploy/review/`。审查结论与修复记录见
`handoff.json` 的 `independent_review` 与 OPEN 项。
