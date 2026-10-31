# W22-PDF-DEPLOY handoff

状态：READY_FOR_ROOT（两轮独立审查全部通过；代码复审最终判定 READY_FOR_ROOT，R3 修复核验 PASSED；详见
`handoff.json` 的 `independent_review`）。配套 `handoff.json` 为
`harness-handoff/1`。

## 交付了什么

一个小型、可重复、幂等的离线 PDF 增强 runtime 部署工具
（`tools/pdf_runtime_deployment/`）：把 W21 已验证的 104-distribution 依赖
闭包与模型，用同卷 NTFS hardlink 投影到**纯 ASCII 资源树**，产出符合既有
`pdf-paragraph-runtime/2` 的本地配置，并验证真实生产入口。上层接口不变：
`COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG` 显式选择该配置即可。

## 真实结果（最终绑定，2026-10-30，工具 SHA 302bf87d… == HEAD）

| 项 | 结果 |
|---|---|
| 部署目标 | `C:/cwp-runtime/w22-pdf-sdk`（ASCII；C: 同卷；最终代码首建） |
| plan | `1cba5f2e…`：104 dist / 36,121 env 行 + 6 模型行；源配置 SHA `bcc42711…`（= W21 接收 review 冻结 profile 字节） |
| deploy | 36,127 hardlinks，SDK/模型**零字节复制**，scaffold 516,976B，共享逻辑 1,405,313,714B，COMPLETE；`environment_sha256=c84a984c…` |
| verify | L0 fresh-process PASS（104 dist 全在部署 site-packages、无 pip/user/base site、ASCII prefix、零 SDK import）+ L1 生产配置加载 PASS + `zero_write_verified=true` + 结果写回收据 |
| constructor | **生产启动形态** CONSTRUCTOR_OK 22.95s/30s（`--production-launch`，走真实 child_launch_command；bare 冷导入两次 >30s 超时已如实记录，未抬封顶） |
| canonical E2E | **enhanced，accepted_groups=2，rejected_groups=0**；completed [1,2] / stream_complete；worker 21.38s/120s；峰值 3.10GiB/4GiB；已知中文资源打开失败**不再发生**；源文本保持；负对照（单字符篡改）仍被拒绝 |
| 对齐诊断 | 真实 SDK 提案 2/2 经未改动的生产 `align_paragraphs` 接受 |

## 关键根因链（三轮诚实记录，收据均保留）

1. **部署根因（已修复）**：docling-parse 6.2.0 在 ACP936 主机上无法从非
   ASCII 部署路径打开打包资源（W21 对照冻结）。本工具的真实 ASCII 资源树
   使 `known_non_ascii_failure=false`。
2. **夹具根因（已修复，非部署缺陷）**：pymupdf 内置 `china-s` 字体无
   ToUnicode CMap → SDK 侧提取乱码 → accepted0（W21 alias rejected2 同因）。
   换嵌入系统字体夹具后真实 accepted2。
3. **冷编译边界（已记录，未抬封顶）**：bare interpreter 冷导入超 30s；生产
   形态（repo-local pycache prefix）22.95s 通过。

## 审查与修复

- 环境独审：ACCEPTABLE（14 项硬链接源抽查、账目、symlink/密钥扫描全过）；
  报告 `review/environment-review-20261030.md`。
- 代码独审初判 3 阻塞（D1 repo-src off-by-one / D2 工具身份漂移 / D3 收据
  缺字段）+ samefile 恢复契约反例——**全部修复**；复审报告
  `review/code-review-r2-20261030.md`、`review/environment-review-r2-20261030.md`。
- 审查者新增 15 个反例测试（reviewer-owned）+ author 19 个 = 34 unit 全绿；
  mypy/ruff 干净。
- 中间版部署收据存档
  `review/deployment-intermediate-revision-99a5d250.json`（退役后模型源
  SHA 复核未变）。

## 边界（不在本卡，ROOT 收口）

- 真实公司文档的 C2、主线摘要/缓存/RF：NOT_RUN，归 ROOT。
- 合成文档 `evidence_span_count=0` 属 selector 语义（与 W21 相同），非部署缺陷。
- 部署 env 是显式交付物：`C:/cwp-runtime/w22-pdf-sdk` 保留（计划清单
  `C:/cwp-runtime/w22-pdf-sdk-plan.local.json` 本地保留未提交——含 36k
  per-file 明细，按卡只交 compact 摘要与 SHA）；淘汰时只删 owned 链接名，
  不沿 hardlink 追删源。
- NTFS 目录/link 元数据分配未精测，不把逻辑 1.4GB 描述为新增磁盘
  （`actual_allocation=unknown` 已写入收据）。
