# W22-PDF-DEPLOY 独立环境审查（第 2 轮：最终提交代码重建树）

- 卡片：`docs/plans/du11-source-closure-2026-10-18/harness_lanes/20261030/W22-PDF-DEPLOY.md`
- 审查对象：`C:/cwp-runtime/w22-pdf-sdk`（审查 finding D2 后由最终提交代码**从零重建**的新树）
- 新 plan：`1cba5f2e4dca2a900c39b4ba368b8a1d94a9f29362f20f5ebf64daf9a1e8e931`（manifest：`C:/cwp-runtime/w22-pdf-sdk-plan.local.json`）
- 新 receipt tool SHA：`302bf87d14450d09c7e904a4ae4a9d242e967f8d44dc40e618f03bca2ddc0819`
- 审查者：独立 reviewer（未参与创作；只读审计；仅写本报告文件）
- 日期：2026-10-30
- 结论：**ACCEPTABLE**（A2–F2 全部通过；无阻断缺陷；tool SHA 与 git HEAD 三方一致）

> 本轮审计**只覆盖新重建树**。中间树的 ACCEPTABLE 报告原样保留于 `review/environment-review-20261030.md`（其 receipt 存于 `review/deployment-intermediate-revision-99a5d250.json`，tool SHA `99a5d250…`、plan `327891cf…`，与新树不同，确认已按 finding D2 重建而非原地改写）。

---

## SHA-256 信任链（独立重算，全部一致）

| 对象 | 值 | 一致 |
|---|---|---|
| plan 规范摘要（canonical，去 `plan_sha256` 字段） | `1cba5f2e…e931` | ✓（`deployment.plan_sha256` 同） |
| 源 profile `runtime-isolated.json` | `bcc42711…ff2a` | ✓（`source_config_sha256` 同） |
| 部署 `paragraph-runtime.config.json` | `bd88ad43…bd22` | ✓（`output_config_sha256` 同） |
| receipt/plan `tool.implementation_sha256` | `302bf87d…0819` | ✓ 见 E2 三方比对 |

---

## A2. 硬链接源保护 — PASS

方法：`os.walk` 遍历 `env/Lib/site-packages`，`docling*|torch*.py|*.safetensors` 候选，**用与第 1 轮不同的新 seed (20261101)** 独立抽 8 个；`artifacts/` 取 `model.safetensors` + 随机 1 个（`README.md`）；另抽 5 个 `.dist-info/RECORD` 与 `env/Scripts/python.exe`。每项核对 `os.path.samefile`、`st_ino/st_dev`、源文件重算 SHA-256==plan 行 `sha256`、字节一致。

| 样本 | samefile | inode | sha | bytes | nlink |
|---|---|---|---|---|---|
| env: docling_parse_backend.py | ✓ | ✓ | ✓ | ✓ | 3 |
| env: huggingface_hub/serialization/_torch.py | ✓ | ✓ | ✓ | ✓ | 3 |
| env: sympy/printing/pytorch.py | ✓ | ✓ | ✓ | ✓ | 4 |
| env: torch/_functorch/pyfunctorch.py | ✓ | ✓ | ✓ | ✓ | 4 |
| env: torch/_higher_order_ops/torchbind.py | ✓ | ✓ | ✓ | ✓ | 4 |
| env: transformers/integrations/torchao.py | ✓ | ✓ | ✓ | ✓ | 3 |
| env: transformers/pytorch_utils.py | ✓ | ✓ | ✓ | ✓ | 3 |
| env: transformers/utils/dummy_…_torch_objects.py | ✓ | ✓ | ✓ | ✓ | 3 |
| artifacts/model.safetensors (171,658,996 B) | ✓ | ✓ | ✓ | ✓ | 2 |
| artifacts/README.md (3,219 B) | ✓ | ✓ | ✓ | ✓ | 2 |
| 5× `.dist-info/RECORD`（filelock/idna/requests/setuptools/tree_sitter） | ✓✓✓✓✓ | ✓ | ✓ | ✓ | 3 |

- 合计 15 项硬链接/源核对，**0 失败**。
- 源 env `…/pdf-sdk-isolated/env` 仍存在；`python.exe` sha `0e818a1f…` 与部署副本字节相同（253,256 B，samefile=False=venv scaffold 复制件，符合预期）。另抽 8 个源文件重算 SHA 与 plan 行一致（8/8）。
- `pyvenv.cfg` 记录 `python -m venv --without-pip C:\cwp-runtime\w22-pdf-sdk\env`，`include-system-site-packages = false`。
- 未对任何硬链接文件就地写/chmod（env/artifacts 文件数与字节在 verify 前后完全不变，见 B2）。

## B2. 隔离与身份 + D3 light_verification 块 — PASS

独立命令（worktree 内）：
```
/c/Miniconda/python.exe -m tools.pdf_runtime_deployment verify \
  --config C:/cwp-runtime/w22-pdf-sdk/paragraph-runtime.config.json \
  --repo-src C:/Users/郑曾波/Projects/company-wiki-w22-pdf-deploy/src
# real 0m15.233s (exec_662655ca)
```
结果：`config_load.status=PASS`、`light.status=PASS`、`distribution_count=104`、`third_party_count=104`、`sdk_imports=0`、`enable_user_site=false`、`environment_sha256=c84a984c…cdf44`、`zero_write_verified=true`、`tree_files=36138`、`tree_bytes=1405835132`、`recorded_in_receipt=true`。

**D3 块一致性**：receipt 内 `light_verification`（含 `light`、`config_load`、`zero_write_verified`、`tree_files/bytes`、`python`、`environment_sha256`）与我独立 verify 输出**逐字段一致**。

**zero_write_verified 语义澄清（重要，非缺陷）**：`cmd_verify`（`__main__.py`）先 `snapshot_tree(config_path.parent)` → 跑 light+config_load 子进程 → 再 snapshot，`zero_write_verified = before==after`。该真值只覆盖**子进程对树的写入**（为真：env/artifacts 文件数/字节 verify 前后完全不变 36130/1234066319 与 6/171764371）。**之后** `write_receipt`（原子 temp+`os.replace`，"Only the marker file is touched"）把 D3 块写入 `deployment.json`——这是卡要求的新字段，属设计内对 owned receipt marker 的写，不触碰 env/artifacts 硬链接内容。故 verify 语义诚实，env/模型零写得到证明。

> 注：`tree_bytes` 因 receipt 自身在树内且每次 verify 更新 D3 块，会随 verify 次数轻微漂移（作者记录 1405834014，我这轮 verify 后为 1405835132，差 = deployment.json 增长）。这是 marker 自引用的正常现象，不是越权或失真；env+artifacts 逻辑字节恒定。

## C2. 配置诚实性 + 新 receipt 字段准确性 — PASS

- `paragraph-runtime.config.json` vs 源 profile 逐字段比对：**仅 `python` 与 `artifacts` 不同**（改指向 `C:\cwp-runtime\w22-pdf-sdk\…`）。`schema_version=pdf-paragraph-runtime/2`、`environment_algorithm=pdf-runtime-closure/2`、`environment_sha256=c84a984c…`、model/model_config/runtime_versions 全同。
- receipt 新字段逐项核实（全部准确）：
  - `source.config_path/config_sha256`：路径存在，sha 重算 `bcc42711…` ✓
  - `source.python/prefix/site_packages/artifacts/base_prefix`：全部存在 ✓
  - `model_sha256 == plan artifacts/model.safetensors 行 sha` ✓；`model_config_sha256 == plan artifacts/config.json 行 sha` ✓
  - `output_config_path`：存在且 realpath 即部署 config ✓
  - `actual_allocation`：`"unknown; NTFS directory/link metadata not measurable here (logical shared bytes only; no on-disk claim)"` —— **诚实声明未知**，未声称磁盘占用 ✓
  - `source_protection`：`rehash_each_source_before_link=true`、`samefile_verified_per_link=true`、`byte_copies_of_packages_or_models=0`、`sources_modified=false` —— 与 A2 实测（每项 samefile+源重哈希通过、0 大复制、源未变）一致 ✓
  - `environment_algorithm` 字段已新增到 receipt 顶层 ✓

## D2. 磁盘口径 — PASS（精确）

独立重算：`env/` 36,130 文件 / 1,234,066,319 B；`artifacts/` 6 文件 / 171,764,371 B。
- plan：`env_rows` 36,121 + `artifact_rows` 6 = **36,127** → `created_links 36127` ✓
- plan 共享逻辑字节 = **1,405,313,714** → `logical_shared_bytes 1405313714` ✓
- scaffold 非 .pyc = **9 文件 / 516,976 B**（.gitignore/Activate.ps1/activate/activate.bat/activate.fish/deactivate.bat/python.exe/pythonw.exe/pyvenv.cfg）→ `new_scaffold_file_bytes 516976` ✓
- env 下 7,246 个 `.pyc` **全部在 plan env_rows 内**（源 env 自带 .pyc 被硬链接），非运行期生成（新树 0 个运行期 scaffold .pyc）。
- `reused_links=0`、`sdk_bytes_copied=0`、`model_bytes_copied=0`、`venv_created=true` ✓
- `diagnostic_counts`（12/0/2/0）== plan diagnostics ✓
- **无越权**：全文无 `allocated/on-disk/disk_usage/physical/ntfs/cluster` 声明；唯一提及 NTFS 的是诚实的 unknown 说明。

## E2. 分类 + tool SHA 三方比对 — PASS

```
/c/Miniconda/python.exe -m tools.pdf_runtime_deployment status --target C:/cwp-runtime/w22-pdf-sdk
# real 0m0.166s
```
`classification = OWNED_COMPLETE`，receipt `plan_sha256 = 1cba5f2e…e931` ✓，status COMPLETE、venv_created true，其余字段与 deployment.json 逐项吻合。

**tool SHA 与 git HEAD 一致（LF 归一化）**：
```
git -C C:/Users/郑曾波/Projects/company-wiki-w22-pdf-deploy show HEAD:tools/pdf_runtime_deployment/deployment.py
```
- git HEAD（LF 归一化）SHA-256 = `302bf87d14450d09c7e904a4ae4a9d242e967f8d44dc40e618f03bca2ddc0819`
- 原始字节 SHA-256 = 同值（该文件本就是 LF，无 CRLF 差异）
- 工作树 `deployment.py`（LF 归一化）SHA-256 = 同值
- receipt / plan `tool.implementation_sha256` = 同值
→ **四方（git HEAD / raw / working-tree / receipt+plan）完全一致**，且 `git status --porcelain tools/pdf_runtime_deployment/` 无输出（工作树干净）。分支 `codex/w22-pdf-deploy-20261030`，HEAD `ee8138cf…`。

## F2. 安全 — PASS

- **路径包含**：`os.walk(followlinks=True)` + `realpath` 起点检查，0 个文件/目录解析到 `C:/cwp-runtime/w22-pdf-sdk` 之外。
- **符号链接/junction**：`os.path.islink` + `os.path.isjunction` 扫描，**0 symlink、0 junction**。
- **secrets 扫描**：deployment.json（含新 `source`/`light_verification`/`source_protection`/`actual_allocation` 块）key 路径与 value 双重扫描，无 key/token/secret/password/credential/env_full/environ 值（`environment_sha256`/`environment_algorithm` 是闭包身份字段，非密钥）。无完整父环境导出。

---

## 无法复现 / 需注意（非阻断）

1. **`deployment.json.seconds = 226.871`**：作者重建耗时，我未重跑 ~4 分钟部署（会新建/改写目标），**未独立复现**该耗时；其身份/字节/tool-SHA 断言均已复现。
2. **`light_verification.tree_bytes` 自引用漂移**：该值含 deployment.json 自身，每次 verify 更新 D3 块会使其增长（见 B2）。字段语义是"verify 当时快照"，不是恒定值；env+artifacts 逻辑字节恒定。非缺陷。
3. **`zero_write_verified` 的边界**：真值覆盖 light/config_load 子进程；verify 命令在测量后按卡要求写入 D3 marker（`write_receipt`，仅动 `deployment.json`）。代码注释明示 "Only the marker file is touched"，诚实。
4. **12 个 `record_deviations`**：与第 1 轮相同的已知 `INSTALLER` 4B/5B provenance 诊断（colorama/mdurl/pluggy/shellingham/typing-extensions/typing-inspection），`missing_unhashed_bytecode=0`；卡明确不得升级为门禁。

---

## 审查者执行的命令与耗时（第 2 轮）

| # | 命令（只读） | 耗时 |
|---|---|---|
| 1 | 读新 receipt / config / plan 结构 + SHA 链（plan_digest/source cfg/output cfg/tool SHA）重算 | 0.2s |
| 2 | **E2** `git show HEAD:…deployment.py` SHA-256（LF 归一化）+ raw + working-tree 三方比对 | <0.1s |
| 3 | **A2** os.walk 新 seed 抽样 + samefile/inode/source-SHA（8 env + 2 art + 5 RECORD） | ~2s |
| 4 | **A2** python.exe scaffold + 源 env 存在 + 8 源文件重算 | 0.2s |
| 5 | **B2** `python -m tools.pdf_runtime_deployment verify …`（后台 exec_662655ca） | **15.233s** |
| 6 | **C2** config 逐字段 diff vs 源 profile | <0.1s |
| 7 | **D2** 树遍历字节核算 + scaffold 拆分 + 与 receipt 对照 | 4.3s |
| 8 | **E2** `python -m tools.pdf_runtime_deployment status --target …` | **0.166s** |
| 9 | **F2** 路径包含 + symlink/junction + secrets（key/value）扫描 | 8.6s |
| 10 | verify 后 env/artifacts 未触碰复核 + D3 块一致性 + 中间 receipt 存续核对 | 7.5s + 0.5s |

所有操作对 `C:/cwp-runtime/w22-pdf-sdk/env` 与 `artifacts/` 均为只读（读取/统计/哈希/同文件判定）。唯一写入为 verify 命令自身按卡要求更新 `deployment.json` 的 D3 `light_verification` marker（`write_receipt` 原子替换，不触碰硬链接内容）——这是被审工具的设计行为，非本审查者的手动编辑。
