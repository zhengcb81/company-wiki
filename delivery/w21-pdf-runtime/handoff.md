# W21-PDF-RUNTIME 交付 handoff

状态：FINAL（初审 10 项全 PASS、0 阻塞、6 INFO 已采纳；终审记录见文末）。

## 身份

| 项 | 值 |
|---|---|
| card_id | W21-PDF-RUNTIME（PLAN_ID `w21-pdf-runtime-2026-10-29`） |
| 工作目录 | `C:/Users/郑曾波/Projects/company-wiki-w21-pdf-runtime`（稀疏工程检出，未关sparse） |
| 分支 | `codex/w21-pdf-runtime-20261029` |
| base_commit | `bb5d09c056ca36bba8061d761b5469d87aa6e5e0`（卡内冻结基线，逐字节一致） |
| implementation_commits | `e173c977`（A seed+调查）、`cf888f0d`（B 隔离launch+guard修复+rev1收据）、`5a33d923`（C 完整性标签修复+E2E+rev2-5收据） |
| 最终 tested commit | 见文末终审记录的 final commit |
| reviewed commit | 初审=5a33d923；终审见文末 |
| 是否已推远端 | 见文末终审记录 |

改动范围：**33 文件，+930/−7**（生产+探针+新测试 6 件 +765/−7；本卡PWF+收据 27 件 +165）。生产仅 `narrative_pdf_enhancement.py`；`_paragraph_worker.py`、`narrative_pdf_environment.py`、checkpoint/alignment、`_bounded_process.py`/`_process_tree.py`、ROOT WIP 区零改动（无缺陷不强改）。未新增 `narrative_pdf_runtime_env.py`（launch实现留在enhancement模块内，由既有 `orchestration_sha256` 入recipe身份）。

## 逐需求状态

| 卡内需求 | 状态 | 证据 |
|---|---|---|
| B: guard标准discard device单元正反例 | implemented/tested | `test_w21_pdf_runtime_probe_guard.py` 15例：真 `os.devnull` 任意写模式放行；`NUL.txt`/`nul_backup`/`devnull`/`sub/NUL`/`./nul` 一律 `persistent_write`；.pdf/.env 读取拒绝；fd open不适用；audit hook 直调不安装；旧guard复刻测试固化历史误拦证据。语义备注：Windows 下 `sub/NUL`、`./nul` 物理上同为丢弃设备，guard 拒绝属偏严策略（无放行风险，findings.md 记录决策） |
| B: 生产真实launch owner的child搜索路径隔离 | implemented/tested | `child_environment`（OS必需allowlist+显式offline/线程变量，无PYTHONPATH/PYTHONHOME/PYTHONSTARTUP/PYTHONUSERBASE）+ `child_launch_command`（`-I -X utf8` + repo-local pycache_prefix）。测试：builder断言 + 真实子进程sentinel（父注入毒化PYTHONPATH/PYTHONHOME/PYTHONUSERBASE后child `sys.flags.isolated/safe_path=True`、user_site=False、毒包不可达、parent env逐键不变）+ 真worker身份段在隔离flag下首方绑定成功 |
| B: 探针新revision留新收据、旧失败不改 | implemented | 新controller `tools/pdf_runtime_probe/run_cold_probe.py` rev1→rev5各自receipt/marker在工区PWF receipts/；ROOT `.planning/c3-20261028` 全部原样（SHA核对见下） |
| B: recipe身份反映真实启动实现 | implemented | `orchestration_sha256`/`worker_sha256` 等自动随文件变化；未改recipe键集；旧publication冻结recipe语义不受影响（validate语义=实现漂移检测，与历次orchestration变化一致） |
| C.1: 新revision受界no-document冷启动 | implemented/**DONE** | rev5：`done_no_document=true`，16.22s（30s卡定界内），guard_rejections=0，peak_commit 615,989,248B，`isolated/safe_path/utf8=True`，prefix=env。rev1-4收据保留各失败根因（见"根因链"） |
| C.2: 合成PDF真实入口E2E | implemented/**PARTIAL（canonical）/诊断性完成（ASCII别名）** | 见"两个E2E各证明了什么" |
| C.3: 故障恢复 | implemented/tested | 既有 `test_pdf_page_checkpoints.py`（80例：超时/损坏尾记录/finished-page保留/真实冷小child）全过；未新增重复覆盖 |
| C.4: 清理与SHA核对 | implemented | 见"清理收据" |
| C.5: 独立agent审查 | **完成** | 初审+终审报告见文末路径 |

未做/不做（卡内明确排除）：不改全局ACL/MIC、不动ROOT计划、不装系统包、不重建env、不跑HK批次、不读未曝光公司原件、不引入新DB/调度/授权链。

## 启动owner的最终形态（narrative_pdf_enhancement.py）

- 命令：`[config.python, "-I", "-X", "utf8", "-X", "pycache_prefix=<repo>/__pycache__/pdf-paragraph", worker]`；无 `-B`（bytecode写往owned前缀）；前缀不可建时回退 `-B` 慢路径且零写入。
- 环境：`child_environment(cpu_threads)` = OS必需allowlist（APPDATA/COMSPEC/HOMEDRIVE/HOMEPATH/LOCALAPPDATA/PATH/PATHEXT/PROGRAMDATA/SYSTEMDRIVE/SYSTEMROOT/**USERNAME**/USERPROFILE/WINDIR）+ 显式 HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE/HF_HUB_DISABLE_TELEMETRY/DO_NOT_TRACK/TOKENIZERS_PARALLELISM/PYTHONUTF8/PYTHONIOENCODING/PYTHONNOUSERSITE/PYTHON_DOTENV_DISABLED/OMP|OPENBLAS|MKL_NUM_THREADS。无 TEMP 继承（由enhance每run指向owned scratch）。
- TEMP：`<repo>/__pycache__/pdf-paragraph/tmp/cw-paragraph-*`（原因见根因链#2；parent建立，run后即删）。
- 资源界/超时/树回收/checkpoint/fallback全部复用原实现，未抬任何限额。

## 根因链（rev1→rev5与E2E的全部发现，每步有receipt）

1. **guard误拦（ROOT已知）**：torch→dill `open(os.devnull,'r+b')` 被旧探针判为持久写。rev1修复后0拒绝通过该点。
2. **child进程完整性级别（新发现，主线SDK阻点的深层根因）**：部署env的 `python.exe` 文件带 `Mandatory Label\Low Mandatory Level:(I)(NW)`（继承自Low标签的部署树；icacls 证据固化在 `handoff.json.integrity`），Windows子进程IL=min(父, exe文件IL)→child恒Low→**无法在任何Medium目录创建文件**（父级%TEMP%的TemporaryDirectory、%TEMP%根等全部不可写）。dill.session在import期调用 `tempfile.gettempdir()`，全部候选不可写→`FileNotFoundError`（rev2/rev3 stderr）。生产enhance原把TEMP指向parent %TEMP%下的TemporaryDirectory→生产child从不可能在本机完成导入。rev4修复：TEMP/pycache指向repo-local Low树（ROOT仓与W21工区整树均 `Low Mandatory Level:(OI)(CI)(NW)`，child可写；Medium进程向Low树写=向下写，总是允许）。
3. **字节码重编译（新发现）**：env无 `__pycache__` 且原launch `-B` 禁写字节码→每次child全量重编译SDK（端点证据：rev1冷缓存30s界内未完成且IO-bound；rev5预热字节码16.2s完成；中间测量值67.4s冷/54.5s热/26.7s预热为实现侧自报，与端点一致）。pycache_prefix后rev5达成。
4. **getpass崩溃（新发现）**：allowlist初版缺 `USERNAME`；torch inductor `default_cache_dir()`→`getpass.getuser()` 在无console+无env时 `OSError: No username set in the environment`（rev4 stderr原文）。rev5补USERNAME后通过。
5. **docling-parse 6.2.0 非ASCII路径缺陷（新发现，canonical E2E的阻塞，跨层）**：C++ `font_glyphs::initialise` 用窄串 `std::ifstream` 打开 `pdf_resources/glyphs/standard/*.dat`；上游以UTF-8窄串传路径，本机ACP=GBK时 `C:\Users\郑曾波\...` 的UTF-8字节按GBK解释→`RuntimeError: filename does not exists`→任何PDF转换 `ConversionStatus.FAILURE`。证据固化：child stderr摘录=`receipts/canonical-stderr-diagnosis.txt`（sha256 `678766800e1155133bfbadce84d36db2239ccf14ab4f841a689f5708e70ad2c0`）；fopen对照=`receipts/canonical-fopen-comparison.txt`（同路径GBK字节fopen OK / UTF-8字节fopen FAIL）。**接口需求交ROOT**：部署env须位于ASCII路径（junction别名或重定位；本卡以只读junction做过诊断验证后已删除），或机器级"使用UTF-8"选项，或上游修复。

## 冷启动/真SDK/合成入口各证明了什么

- **rev5冷启动（30s界，无文档）**：生产launch owner（隔离flags+清洗env+bytecode前缀+Low可写scratch）在已部署env上完整通过 docling.document_converter/base_models/pipeline_options 导入与 DocumentConverter 无文档构造。证明：启动路径本身修复完成；不代表业务召回。
- **canonical E2E（ROOT profile原路径，120s界）**：triage 2页gap触发→真实worker完成identity（environment_sha256复算匹配 c84a984c…）+IMPORT+CONVERTER_READY→PAGE_1 处 ChildFailed（根因#5）→诚实 `native_fallback`，原文text/hash保留。证明：真实入口的观测、fallback与诊断契约在阻点面前行为正确；SDK转换在本机canonical路径下不可用（跨层需求）。
- **ASCII别名E2E（同一env的只读junction别名，120s界，receipt标注 `python_origin=ascii_alias_diagnostic`）**：同一生产入口全管线完成——completed_pages=[1,2]、stream_complete=True、actual_engine=docling/2.96.0、真实model_sha=00333a…、converter_instances=1、peak_job_commit=3,250,298,880B（3.03GiB，4GiB界内）、42.4s<120s；alignment真实拒绝2组→诚实 `unaligned_native_fallback`（未拿engine成功签业务召回；对齐质量验收归ROOT真实文档批次）。证明：一旦部署路径满足ASCII要求，配置界内SDK增强可运行。

## 配置/资源/磁盘

- 未重建/复制env或model；ROOT env 1.23GB逻辑共享字节不变；本卡新增磁盘=工区 `__pycache__/pdf-paragraph`（bytecode镜像，apparent ~160MB / 分配~180MB）——git-ignored，pyc按源mtime+size自动校验失效。
- 冷启动观察峰值616MB（无文档）；真实转换峰值3.25GB（4GiB界内）；CPU4/120s/3页/64MiB in/2MiB out均按既有配置未抬。
- 生产首跑代价：冷字节码缓存时导入~67s+，首run可能fallback一次后自种子。给ROOT的集成提示：可先无文档warmup（`-X pycache_prefix` 一次导入）或接受首文档fallback。

## 测试

- W21相关面：初审实跑137例（六文件）+导入面超集237例全过；新测试20例（launch 5 + guard 15）；ruff/mypy干净；pre-commit全绿。
- 全量 `tests/unit`：9400+通过；40F+60E经基线detached worktree对照为基线已有状态（ROOT侧WIP/稀疏缺数据），失败文件与W21改动面零交集；完整摘要=`receipts/full-unit-summary-current.txt`。

## 清理收据

- ROOT侧：`single-cold-attempt.json`（attempts=1原文）/`cold-probe.json`/`runtime-isolated.json`(sha bcc427…)/`cold_probe.py`(sha bb67326a…) 零接触（初审复核SHA不变）；env今日零写入（find -newermt 2026-10-29 为空）；model.safetensors/config.json SHA复算=00333a…/fdea30…不变；env目录Low标签未变。
- 本卡侧：junction `C:/Users/Public/cw-w21-ascii-env` 已rmdir（dir /AL 复查不存在）；诊断脚本、ROOT侧曾误写的importtime.log、临时pyc实验目录、`%TEMP%/cw-paragraph-diag` 残留目录均已删；`prefix/tmp` 无残留run目录；E2E的PDF/config/输出全部在owned scratch内且run后 `scratch_restored_absent=true`。
- 事故记录：为对照基线曾在工区误用 `git stash pop` 弹出ROOT共享stash并立即 `git reset --hard` 完全恢复；ROOT stash条目未drop、内容无损（progress.md有全过程；工区车道禁止stash的教训已入项目记忆）。

## 独立审查路径

- 初审：`delivery/w21-pdf-runtime/review-initial.md`（独立agent，2026-10-29/30；10项必查全PASS、0阻塞、6 INFO）。
- INFO采纳：数字更正（33文件/+930、~160MB缓存、3.03GiB表述、20例新测试、80例checkpoint测试）、handoff.json落盘（含icacls/SHA/stderr摘录/fopen证据）、`%TEMP%`残留目录已删、progress措辞收敛；guard偏严语义在需求表标注。
- 终审：`delivery/w21-pdf-runtime/review-final.md`（第二次独立agent，7项必查全PASS、0阻塞、2条不阻塞INFO已由作者补记）。终审独立复核了根因#5（自跑fopen对照：GBK OK/UTF-8 FAIL，GetACP=936）。

## 交付状态

- final tested commit：`eab239d9`（终审对象，全部测试在其上通过）
- 终审结论：**通过，可交付/可推送**（2026-10-30）
- 推送：见下方"是否已推远端"终审后更新

## OPEN（如实交ROOT的跨层接口需求）

1. **部署路径ASCII化**（阻塞canonical SDK转换）：env位于 `C:/Users/郑曾波/...`（非ASCII）+ 本机ACP=GBK → docling-parse 6.2.0 C++ 无法打开资源。需ROOT决定：env重定位/ASCII junction别名（诊断已验证可行、零字节拷贝）或机器级UTF-8 ACP或上游修复。满足后同配置即达 ASCII别名E2E 的实测状态（43s内全管线）。
2. 首跑字节码冷编译一次性代价（~67s导入）：建议ROOT集成时做一次warmup或接受首文档fallback后自愈。
3. 对齐质量：合成样张上alignment拒绝2组属真实行为；真实文档的召回/对齐验收归ROOT批次（本卡不签业务召回）。
