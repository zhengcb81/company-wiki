# Findings

ROOT已定位：旧no-document探针误拦NUL；生产child环境仍继承父Python搜索配置。初态基线bb5d09c0，工程稀疏检出clean，随后仅四个ROOT seed文件。无原件/SDK复制。

## A 阶段调查（2026-10-29）

### 隔离env事实（只读自ROOT `.planning/c3-20261028/pdf-sdk-isolated/`）
- `runtime-isolated.json`（schema pdf-paragraph-runtime/2）：python=该目录`env/Scripts/python.exe`（3.13.9）；
  artifacts=`C:/Users/郑曾波/.cache/huggingface/hub/models--docling-project--docling-layout-heron/snapshots/8f39ad3c0b4c58e9c2d2c84a38465abf757272d8`；
  model_sha256=`00333a43451945aaf89db8ca9c0a17e75d1537c17db60fdb91aa95f4c7929e0c`；
  model_config_sha256=`fdea30805ce2f5666b147fca941dcdd27ad468e27d6ed21902207d3da056a97d`；
  docling 2.96.0 / docling-core 2.78.0 / docling-ibm-models 3.13.2 / torch 2.12.0 / pymupdf 1.26.7 / pypdfium2 4.30.0；
  max_seconds=120, max_pages=3, max_memory=4GiB；environment_sha256=`c84a984ccb3a56dffbfd0d4538f14ce4a27de44dec4981527a2b0c4a545cdf44`（pdf-runtime-closure/2）。
- `deployment.json` status=`DEPLOYED_METADATA_PROOF_PASS`；104发行包hardlink投影，未拷SDK字节。
- 旧cold receipt：单次30s界，18.806s ChildFailed；事件序列 BOOT→IMPORT_DOCUMENT_CONVERTER（samples至313,511,936B peak commit）→
  GUARD_REJECTED(persistent_write)@17.777s（torch→dill 打开 `os.devnull`=`nul` 的 `r+b` 被 `is_relative_to(temp)` 规则误判）→ERROR PermissionError。
- `single-cold-attempt.json` marker=attempts 1, profile_sha bcc427…, probe_sha bb67326a…。旧文件全部只读保留。

### 生产launch owner缺陷（narrative_pdf_enhancement.py:194-208）
- `env = dict(os.environ, HF_HUB_OFFLINE="1", …)` 继承全部父环境：PYTHONPATH/PYTHONHOME/PYTHONSTARTUP/用户site可注入；
  而隔离轻量证明（light-check）用 `-I`+清洗env，两者不等价。
- 命令为 `[config.python, "-B", str(worker)]`，无 `-I`/-E/-X utf8。
- worker（`_paragraph_worker.py`）自身无需改动：`_environment_module()` 显式插入 src 根；
  site-packages 由配置解释器自身提供（`-I` 不影响 venv site-packages）；nt 分支同样显式插路径。

### 本机Windows NUL归一化实测
- `os.path.realpath(os.path.abspath("NUL"))` → `\\.\NUL`（大小写变体归一同设备；`x/NUL` 也归一为设备——Win32语义）。
- `NUL.txt`/`nul_backup` 归一为真实文件路径。`os.devnull` 在本机为小写 `nul`。
- guard 设计：先严格匹配字面量（raw 文本 nt 上 casefold 后等于 os.devnull；POSIX 精确相等），再 realpath 设备归一确认；
  然后才落到 temp 允许/拒绝。这样 `sub/NUL`、`NUL.txt`、`nul_backup` 都不能借设备放行，而 dill 的 `open(os.devnull,'r+b')` 通过。

### 现有测试覆盖（worktree 全部 37 通过）
- test_pdf_runtime_environment.py（18）：v2 resolver/身份/binding。
- test_pdf_paragraph_runtime.py（10）：runner级失败/成功、fallback诚实、legacy v1 recipe 无 v2 键。
- test_pdf_paragraph_reading_integration.py（9）：真实pymupdf解析+mock runner全链路+replay不重启模型。
- test_pdf_page_checkpoints.py：已覆盖损坏尾记录、finished-page保留、真实冷小child。
- 缺口：无 child 搜索路径隔离证明；guard 无单测；无新revision受界冷启动；无真实SDK入口E2E。

### 边界冻结（B/C 依此执行）
- 只改 `narrative_pdf_enhancement.py`（新增私有 `child_launch_command`/`child_environment`，`enhance` 改用）+ 新 `tools/pdf_runtime_probe/`
  （`cold_runtime_probe.py` child探针、`run_cold_probe.py` controller）+ 新tests `test_w21_pdf_runtime_launch.py`、
  `test_w21_pdf_runtime_probe_guard.py`。不新增 `narrative_pdf_runtime_env.py`（launch实现留在enhancement模块内，
  由既有 `orchestration_sha256` 自动入recipe身份；worker/environment/checkpoint/alignment零改动）。
- 启动形态：`[python, "-B", "-I", "-X", "utf8", script]` + allowlist env（SYSTEMROOT/WINDIR/COMSPEC/PATH/PATHEXT/SYSTEMDRIVE/
  USERPROFILE/HOMEDRIVE/HOMEPATH/APPDATA/LOCALAPPDATA/PROGRAMDATA + 显式offline/线程/编码变量 + PYTHONNOUSERSITE=1；
  不含 PYTHONPATH/PYTHONHOME/TEMP继承；TEMP/TMP/TMPDIR 仍由enhance指向owned临时目录）。
- guard 仅存在于探针（生产不加人工门禁）；audit hook 能力表述限于Python可观测事件。
- 探针receipts写工区 `docs/plans/w21-pdf-runtime-2026-10-29/receipts/`；scratch用系统TEMP下 owned `cw-w21-cold-*`；
  旧ROOT receipt/marker零接触。新controller按probe sha单次防重（新marker，不碰旧marker）。
- E2E：synthetic PDF（pymupdf生成，系统TEMP owned），经 `configured_paragraph_runtime()`（COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG
  指向工区owned临时配置）→ 真PdfReading → 真worker → 离线SDK；完成后删除，不提交任何PDF/env/大日志。
