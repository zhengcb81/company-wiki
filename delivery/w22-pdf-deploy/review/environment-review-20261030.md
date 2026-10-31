# W22-PDF-DEPLOY 独立环境审查（deployed environment audit）

- 卡片：`docs/plans/du11-source-closure-2026-10-18/harness_lanes/20261030/W22-PDF-DEPLOY.md`
- 审查对象：已部署离线 PDF 运行时 `C:/cwp-runtime/w22-pdf-sdk`
- 审查者：独立 reviewer（未参与创作；只读审计，未改动被部署树任何字节/权限）
- 日期：2026-10-30
- 结论：**ACCEPTABLE**（A–F 全部通过；无阻断缺陷）

---

## 总体结论

所有可复现断言均已独立重算并吻合：SHA-256 信任链、硬链接源保护、隔离身份、配置诚实性、磁盘口径、目标分类、路径/符号链接安全。未发现阻断缺陷。NTFS 实际分配字节不可知——收据用词正确地限定为 *logical* 字节，未越权声称磁盘占用。

---

## A. 硬链接源保护 — PASS

抽样方法：`os.walk` 遍历 `env/Lib/site-packages`，按 `docling*|torch*.py|*.safetensors` 收集候选，固定 seed 随机抽 8 个；`artifacts/` 取 `model.safetensors` + 随机 1 个；另查 `env/Scripts/python.exe` 与 4 个 `.dist-info/RECORD`。

对每个样本三重核对：`os.path.samefile(tgt,src)`、`st_ino/st_dev` 相同、源文件重算 SHA-256 == plan 行 `sha256`、字节数一致。

| 样本 | samefile | inode | sha==plan | bytes | nlink |
|---|---|---|---|---|---|
| env: docling_parse_backend.py | ✓ | ✓ | ✓ | ✓ | 3 |
| env: torch/_dynamo/backends/torchxla.py | ✓ | ✓ | ✓ | ✓ | 4 |
| env: torch/_dynamo/variables/torch.py | ✓ | ✓ | ✓ | ✓ | 4 |
| env: torch/_higher_order_ops/executorch_call_delegate.py | ✓ | ✓ | ✓ | ✓ | 4 |
| env: torch/testing/_internal/torchbind_impls.py | ✓ | ✓ | ✓ | ✓ | 4 |
| env: torchvision/.../torch_function_helpers.py | ✓ | ✓ | ✓ | ✓ | 4 |
| env: transformers/exporters/exporter_executorch.py | ✓ | ✓ | ✓ | ✓ | 3 |
| env: transformers/pytorch_utils.py | ✓ | ✓ | ✓ | ✓ | 3 |
| artifacts/model.safetensors (171,658,996 B) | ✓ | ✓ | ✓ | ✓ | 2 |
| artifacts/config.json (3,268 B) | ✓ | ✓ | ✓ | ✓ | 2 |
| env/Scripts/python.exe（scaffold，见下） | ✗(copy) | — | ✓ | ✓ | 1 |
| env 4× `.dist-info/RECORD` | ✓ | ✓ | ✓ | ✓ | 3–4 |

- 合计 14 项硬链接/源核对，**0 失败**（python.exe 为 scaffold 复制件，非硬链接，符合 venv 语义）。
- 源 env `C:/Users/郑曾波/Projects/company-wiki/.planning/c3-20261028/pdf-sdk-isolated/env` **仍存在**；其 `python.exe` sha256 `0e818a1f...` 与部署副本字节相同（253,256 B）。另抽 6 个源文件重算 SHA 与 plan 行一致（6/6）。
- 部署副本 `python.exe`/`pythonw.exe`/`pyvenv.cfg` 是 venv 正常 scaffold 复制（`pyvenv.cfg` 记录 `command = C:\Miniconda\python.exe -m venv --without-pip C:\cwp-runtime\w22-pdf-sdk\env`），不是硬链接共享；未对任何硬链接文件就地写/chmod。

## B. 隔离与身份 — PASS

命令（worktree 内，无 SDK import）：
```
/c/Miniconda/python.exe -m tools.pdf_runtime_deployment verify \
  --config C:/cwp-runtime/w22-pdf-sdk/paragraph-runtime.config.json \
  --repo-src C:/Users/郑曾波/Projects/company-wiki-w22-pdf-deploy/src
# real 0m40.203s (task exec_eb4a98d8)
```
结果：
- `config_load.status = PASS`，`light.status = PASS`
- `environment_sha256 = c84a984ccb3a56dffbfd0d4538f14ce4a27de44dec4981527a2b0c4a545cdf44` ✓（与卡、config、plan、deployment.json 一致）
- `distribution_count = 104`，`third_party_count = 104` ✓
- `zero_write_verified = true`（before==after，`tree_files=38627`，`tree_bytes=1461229415`，与我复算完全一致）
- `sdk_imports = 0`，`enable_user_site = false`，`prefix = C:\cwp-runtime\w22-pdf-sdk\env`（未注入用户/全局 site）

## C. 配置诚实性 — PASS

`paragraph-runtime.config.json` 对源 `runtime-isolated.json` 逐字段比对，**仅 `python` 与 `artifacts` 不同**（两处均改为 `C:\cwp-runtime\w22-pdf-sdk\...` 目标路径），其余全同：`schema_version`、`model_sha256`、`model_config_sha256`、`docling_version`、`max_seconds`、`max_pages`、`runtime_versions`（docling-core 2.78.0 / docling-ibm-models 3.13.2 / torch 2.12.0 / pymupdf 1.26.7 / pypdfium2 4.30.0 / python 3.13.9）、`max_memory_bytes`、`environment_sha256`、`environment_algorithm`。
- `schema_version = pdf-paragraph-runtime/2` ✓
- `environment_algorithm = pdf-runtime-closure/2` ✓
- 配置 12 个 key，无 secret/token/key/password/完整父 env（两个 "environ" 命中是闭包身份字段 `environment_sha256`（64 位 hex）与 `environment_algorithm`，非密钥）。

## D. 磁盘口径 — PASS（未越权）

独立重算部署树：
- `env/` 38,619 文件 / 1,289,463,193 B；`artifacts/` 6 文件 / 171,764,371 B。
- plan：`env_rows` 36,121 + `artifact_rows` 6 = **36,127**；plan 共享逻辑字节（env+art）= **1,405,313,714 B**。
- 部署新增 scaffold（不在 plan env_rows 的 venv 文件）：**9 个非 .pyc 文件 = 516,976 B**（.gitignore / Activate.ps1 / activate / activate.bat / activate.fish / deactivate.bat / python.exe / pythonw.exe / pyvenv.cfg），**精确等于** `deployment.json.new_scaffold_file_bytes`。
- 另有 2,489 个 `__pycache__/*.pyc`（≈55.4 MB）是运行期字节码，**非部署新增**，被正确排除在 `new_scaffold_file_bytes` 之外（plan `missing_unhashed_bytecode=0`）。

与 `deployment.json` 对照（全部 True）：
- `created_links 36127` == plan rows total ✓
- `logical_shared_bytes 1405313714` == plan 共享字节 ✓
- `new_scaffold_file_bytes 516976` == 9 个 scaffold 字节 ✓
- `reused_links 0`、`sdk_bytes_copied 0`、`model_bytes_copied 0` ✓
- `diagnostic_counts`（record_deviations 12 / missing_unhashed_bytecode 0 / active_pth_hooks 2 / site_hooks 0）== plan diagnostics ✓

**NTFS 分配 vs 逻辑字节**：收据字段为 `logical_shared_bytes` / `new_scaffold_file_bytes`（明确 *logical*）；全文扫描 `allocated/on-disk/disk_usage/physical/ntfs/cluster/st_blocks` **均未出现**。收据**未**声称实际磁盘占用——**无越权**。硬链接共享字节不等于新增磁盘，卡与收据表述一致。

## E. 目标分类 — PASS

命令：
```
/c/Miniconda/python.exe -m tools.pdf_runtime_deployment status --target C:/cwp-runtime/w22-pdf-sdk
# real 0m0.533s
```
结果 `classification = OWNED_COMPLETE`，receipt 内 `plan_sha256 = 327891cff2924d6306f1b90a5e4672a052ad830a62adab38588ddf642aa8266c` 与 plan/deployment 一致 ✓，status COMPLETE、venv_created true、其余字段与 deployment.json 逐项吻合。

## F. 安全 — PASS

- **路径包含**：全树 `os.path.realpath` 起点检查，0 个文件/目录解析到 `C:/cwp-runtime/w22-pdf-sdk` 之外。
- **符号链接/junction**：`os.walk(followlinks=True)` 扫描 **0 个 symlink**；`os.path.isjunction` 扫描 **0 个 junction**。
- **deployment.json 密钥扫描**：key 路径与 value 双重扫描，无 key/token/secret/password/credential/env_full/environ 值；唯一正则命中 `environment_sha256` 是哈希字段名误报。无完整父环境导出。

---

## SHA-256 信任链（独立重算）

| 对象 | 期望 | 实测 | 一致 |
|---|---|---|---|
| 源 profile `runtime-isolated.json` | `bcc427114955...ff2a` | `bcc427114955...ff2a` | ✓ |
| 部署 `paragraph-runtime.config.json` | `bd88ad431822...bd22` | `bd88ad431822...bd22` | ✓ |
| plan 规范摘要（去 `plan_sha256` 字段，canonical JSON） | `327891cff292...266c` | `327891cff292...266c` | ✓ |
| `deployment.plan_sha256` / `source_config_sha256` / `output_config_sha256` | 与上三者同 | 同 | ✓ |

注：plan **原始文件字节** SHA 为 `a9758cd5...bd5bb`（因文件内嵌了自引用 `plan_sha256` 字段）；权威身份是 `plan_digest()`（`deployment.py:113` `sha256(_canonical(plan minus plan_sha256))`），我按该算法重算得 `327891cf...`，与卡/deployment 一致。这不是缺陷，但读者不应拿裸文件字节 SHA 去对 `327891cf`。

## E2E 收据交叉核对（`receipts/w22-synthetic-e2e.json`）

- `config_path = C:\cwp-runtime\w22-pdf-sdk\paragraph-runtime.config.json`（存在，realpath 即部署配置）
- `runtime_identity.environment_sha256` / `docling_version` / `diagnostic.model_sha256` / `warmup.launch_shape[0]` 均与部署 config 吻合
- `status=enhanced`、`page_count=2`、`actual_engine=docling 2.96.0`、`source_preserved=true`、`negative_control_rejected=true`、`known_non_ascii_failure=false`、`WARM_OK`
- 身份字段与部署 config 一致；E2E 是否"内容对齐通过"属 C2 范畴（卡已声明整体 PARTIAL），本审只核环境身份——**未复现也未推翻**其 accepted/rejected 语义（那需重跑真实 SDK，非本环境审范围）。

## 无法复现 / 需注意的点（非阻断）

1. **`deployment.json.seconds = 417.079`**：部署耗时是作者运行时记录，我未重跑 7 分钟部署（会新建/改写目标），故**未独立复现**该耗时；其身份/字节断言均已复现。
2. **plan 裸文件字节 SHA ≠ `plan_sha256`**：见上，需按 `plan_digest()` 规范算法计算，属设计而非缺陷。
3. **运行期 `.pyc` 增长**：部署后运行 verify/E2E 会新增/更新 `__pycache__/*.pyc`（现 2,489 个，≈55.4 MB），不属 `new_scaffold_file_bytes`；`tree_files/tree_bytes` 会随运行漂移（我测得 38627 / 1,461,229,415 与 verify 快照一致）。这不影响 `created_links`/`logical_shared_bytes` 等部署期恒量。
4. **12 个 `record_deviations`**：均为 `colorama/mdurl/pluggy/shellingham/typing-extensions/typing-inspection` 的 `INSTALLER` 文件 4B/5B provenance 差异（哈希+大小双重），是已知历史诊断，卡明确要求不得升级为门禁；`missing_unhashed_bytecode=0`。

---

## 审查者执行的命令与耗时

| # | 命令（只读） | 耗时 |
|---|---|---|
| 1 | `python -c` 重算 plan/config/source-config SHA 链 + deployment 交叉比对 | 0.10s |
| 2 | `python -c` 按 `plan_digest()` canonical 算法重算 plan 摘要 | <0.1s |
| 3 | **A** `python` heredoc：os.walk 抽样 + samefile/inode/source-SHA（8 env + 2 art + py + 4 RECORD） | 2.1s |
| 4 | **A** 源 env 存在性 + python.exe SHA + 6 源文件重算 | 0.3s |
| 5 | **B** `python -m tools.pdf_runtime_deployment verify --config ... --repo-src ...`（后台 exec_eb4a98d8） | 40.203s |
| 6 | **C** `python` heredoc 配置逐字段 diff vs 源 profile | <0.1s |
| 7 | **D** `python` heredoc 树遍历字节核算 + 与 deployment.json 对照 | 2.9s + 3.0s |
| 8 | **E** `python -m tools.pdf_runtime_deployment status --target ...` | 0.533s |
| 9 | **F** `python` heredoc 路径包含 + symlink/junction + 密钥 key/value 扫描 | ~0.1s |
| 10 | 收据 overclaim 扫描 + E2E 身份交叉核对 + config 密钥扫描 | <0.1s |

所有操作对 `C:/cwp-runtime/w22-pdf-sdk/env` 与 `artifacts/` 均为只读（读取/统计/哈希/同文件判定），未 edit/chmod/delete 任何硬链接文件。
