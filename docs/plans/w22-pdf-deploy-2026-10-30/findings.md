# W22-PDF-DEPLOY 调查记录

已知证据、读路径、接口与禁止范围见TASK_CARD.md。旧结果保持原状态，不拿工程已合线替代真实C2/主线召回验收。作者在A/B记录新证据和失败，保持小而可复核。

## A 阶段：根因与部署设计（2026-10-30）

### 已核对证据（只读，未改动任何来源）

1. ROOT 接收 review（`review/w21-root-reception-20261030/review.md`）：no-document SDK constructor
   16.222824s/30s 通过；canonical 中文路径 env 在 PAGE_1 `ChildFailed`/`native_fallback`；同一 env 临时
   ASCII alias 完成2页但 accepted0/rejected2（`unaligned_native_fallback`，诊断性质）。
2. 隔离部署（`.planning/c3-20261028/pdf-sdk-isolated/`）：104 distributions/36,121 hardlink/共享逻辑
   1,233,549,343B，scaffold 517,241B，SDK/模型零字节复制；`runtime-isolated.json` 与原 profile 仅差 python
   路径，`environment_sha256=c84a984c…`（pdf-runtime-closure/2）；6 处 INSTALLER 4B/5B RECORD provenance
   差异与 2 个标准 .pth hook 为诊断记录，非门禁。
3. 生产契约（本工区源码）：
   - `configured_paragraph_runtime()` 读 `COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG` 指向的 JSON，schema
     `pdf-paragraph-runtime/2` 须绑 `environment_algorithm=pdf-runtime-closure/2`；
   - `ParagraphRuntimeConfig` 必填 `python/artifacts/model_sha256/model_config_sha256/docling_version/runtime_versions(精确6键)/environment_sha256`，封顶 120s/3页/64MiB入/2MiB出/4GiB committed/CPU4；
   - 子进程启动 `[python, -I, -X utf8, (-X pycache_prefix=repo-local)] _paragraph_worker.py`，env 走 allowlist
     +offline flags，TEMP/TMP 指向 repo-local scratch（Low 完整性子进程可写）；
   - worker 身份校验：docling/6个 runtime_versions/`environment_sha256(roots=v2)` 全部须与配置一致；模型
     `config.json`+`model.safetensors` 逐 SHA 核对后 `artifacts_path` 交给 docling。
4. 对齐层（`narrative_pdf_paragraphs.py`，ROOT owner 不改）：proposal 文本 NFKC 归一后须等于 ≥2 个连续
   native `pdf_text_block` 拼接，且整块 native bbox（含 2–3pt 字号容差）落在 proposal bbox 内；重叠 proposal
   全部作废。

### 根因判读（区分五类路径）

| 路径 | 实际值 | 判读 |
|---|---|---|
| 解释器/site-packages | `…company-wiki\.planning\c3-20261028\…\env\Scripts\python.exe`（含中文用户名） | **判别变量**。W21 对照：中文 env 路径 PAGE_1 失败，ASCII alias 同 env 完成2页。docling-parse 6.2.0 的打包资源（fopen/ACP936 对照）随 site-packages 路径解析，非 ASCII 即失败 |
| 模型 artifacts | `C:\Users\郑曾波\.cache\huggingface\hub\models--docling-project--docling-layout-heron\snapshots\8f39ad3c…`（含中文用户名，6 文件/171,764,371B） | alias 对照运行中保持中文仍完成转换 → 非阻塞，但非 ASCII；按 A4 在 owned ASCII 树 hardlink 原文件（零字节复制），使配置自包含且全树 ASCII |
| 第一方源码/repo scratch | 工区树（中文） | 生产已由 W21 launch owner 处理（隔离 flags + repo-local bytecode/scratch）；W21 alias 对照中 scratch 保持中文且转换完成 → 不动 |
| 临时 alias/junction | W21 诊断用 | 不作为正式环境；本包建真实 ASCII 资源树 |
| 配置文件路径 | 验收子进程显式 `COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG` | 父进程内 JSON 读取与路径无关；不持久改 ROOT 环境 |

### 部署设计（B/C 实施依据）

1. **来源与 resolver**：`--source-config` 显式给出现有 runtime 配置（本次用 W21 已验证的
   `runtime-isolated.json`）；closure 由既有 `describe_environment(configured_runtime_roots(runtime_versions))`
   在**源解释器内**（`-B -I` metadata-only probe）解析，文件清单来自各 dist RECORD；绝不重新发明依赖身份。
   INSTALLER provenance 差异、活动 .pth 记为诊断字段，不升级为门禁。
2. **目标**：ASCII-only 新目录（首验 `C:/cwp-runtime/w22-pdf-sdk` 不存在、同 C: 卷、可写）。结构：
   `env/`（普通 venv `--without-pip --copies`，include-system-site-packages=false）+ `artifacts/`（模型逐文件
   hardlink）+ `w22-paragraph-runtime.json`（输出配置）+ `deployment.json`（owned 收据，含 plan SHA 与工具
   身份）+ 本地 `plan.local.json`（不提交）。
3. **零大复制边界**：venv scaffold 小复制（记 `new_scaffold_file_bytes`）；104 dist 文件与 6 个模型文件全部
   NTFS hardlink，逐链接前重算源 SHA（actual-source 保护）+ `samefile` 证明；逻辑共享字节单列，不冒充新增
   磁盘；NTFS metadata 开销如实声明"未精测"。不做就地编辑/chmod；不沿 hardlink 删源。
4. **基解释器一致性**：CLI 必须由与源 env 同 base 的基 Python 运行（`sys.prefix==sys.base_prefix` 且
   prefix 与 probe 返回的 `base_prefix` 一致），否则显式报错。
5. **幂等/恢复**：目标分类 `ABSENT/EMPTY/OWNED_COMPLETE/OWNED_INCOMPLETE/FOREIGN`。OWNED_COMPLETE 且
   plan SHA 相同 → 复核后零写复用；OWNED_INCOMPLETE → 按 plan 对账恢复（缺→link；已存在且
   samefile+SHA 同→保留；存在但不同→冲突中止，不覆盖不删除非 owned 文件）；FOREIGN/未知 → 明确报错，
   换 owned 目标。绝不误报"已就绪"。
6. **输出配置**：与 source profile 逐字段相同，仅 `python/artifacts` 替换为 ASCII 路径；schema/SHAs/封顶/
   `environment_sha256` 不变（路径变化下 metadata-closure SHA 相同属合法，不虚构代码身份变化）。仍由
   `COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG` 显式选择，上层接口不变。
7. **验证分级**：L0 轻量（新解释器 fresh process：closure 全等 + environment_sha256 + 104 dist 全在目标
   site-packages + 无 user/base site/pip + 零 SDK import）；L1 生产配置加载（repo Python fresh process，
   `configured_paragraph_runtime()` → recipe 绑定核对）；L2 no-document constructor（显式 opt-in，30s 封顶）；
   L3 真实入口 E2E（合成 ≤2 页 PDF → `PdfReading` → 真 worker → 离线 SDK → 现有对齐），转换与对齐分开记录。
8. **同配置第二次轻量复核零环境写入**：verify 前 snapshot 目标树（count/bytes/mtime 摘要），复核后比对。

### 风险与诚实边界（预记）

- alias 对照 accepted0/rejected2 说明**对齐风险真实存在**：即使全 ASCII 部署，E2E 仍可能 accepted0。
  届时先审合成夹具是否真的无增强需求，再给最小对齐反例；对齐层是 ROOT owner，不改。C2 结论按实际
  结果记录，不因部署工程 PASS 而签全部完成。
- Low 完整性子进程对新 ASCII 树（`C:/cwp-runtime/...` 默认 Medium 继承）的**可写性未证明**：worker 需要的
  TEMP/bytecode 在 repo-local（Low 可写），但 dill/transformers 的其他临时写如落入 ASCII 树可能被拒。
  C 阶段以真实日志判定，不预先抬权限/改 ACL。
