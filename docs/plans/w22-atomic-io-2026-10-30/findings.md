# W22-CWP-ATOMIC-IO 调查记录

已知证据、读路径、接口与禁止范围见TASK_CARD.md。旧结果保持原状态，不拿工程已合线替代真实C2/主线召回验收。作者在A/B记录新证据和失败，保持小而可复核。

## A1: 范围核对（2026-10-30）

- 工区 `C:/Users/郑曾波/Projects/company-wiki-w22-atomic-io`，分支 `codex/w22-atomic-io-20261030`，HEAD=`662f821e749bc221c8c308986e54e00465834332`（=卡基线）。稀疏 checkout：config/scripts/src/tests/tools。
- `atomic_output` 生产调用方共 5 处，全部在 `source_catalog`：`canonical_writer.py:817`(sync=True)、`service.py:1344/1355`(`_atomic_write` w/utf-8/newline="\n"、`_write_csv` w/utf-8-sig/newline="")、`normalizer.py:301`、`official_json_projection.py:819`(persist_projection, sync=True)。无任何代码按目标名前缀清扫 stage 文件。
- ROOT w21 接收审查（已提交基线）认定两个共同 owner：staging 名复制目标 basename 放大路径；gate scratch 固定放 `PROJECT_ROOT/cwpp-*`。

## A2: 行为复现（tools/w22_atomic_probe.py，真实 NTFS，宿主 LongPathsEnabled=0 仅作只读观察）

- 目标 252 字符（≤259）普通创建 OK；同目标旧命名 stage 265 字符 → `FileNotFoundError errno 2`（`os.open` 下 winerror 为 null）；旧代码 `atomic_output` 同样 `FileNotFoundError errno 2`，原目标字节不变。
- 457 字符深目录：普通 `os.stat` → `FileNotFoundError errno 2 / winerror 3`；`\\?\` 扩展长度形式 mkdir、open、os.replace、unlink 全部成功——扩展长度封装的平台能力成立。
- 真实竞争错误形态：目标被无 FILE_SHARE_DELETE 句柄占用时 `os.replace` → `PermissionError errno 13 / winerror 5`。与路径长度失败（FileNotFoundError）类型可区分，不得混判。

## A2b: 实测平台事实补充（tools/w22_atomic_probe.py 四段，logs/probe-final.json）

- 普通文件创建：≤259 成功，260 起 `FileNotFoundError errno 2`；普通 mkdir：≤247 成功，248 起 `winerror 206`——两者上限不同，primitive 必须按"父目录+stage 名"而非"目标名"决策。
- 混合形式 `os.replace`（扩展长度 stage → 普通合法目标，同目录）实测 OK——wrap 决策可按路径各自独立判断。
- 457 字符深目录扩展形式 mkdir/create/replace/unlink 全 OK；本宿主（LongPathsEnabled=0，只读观察）上扩展长度封装平台能力成立。

## A3: 冻结成功/失败合同

1. stage 必须与目标同目录（保 os.replace 原子性），独占随机名，不复制目标 basename；stage 名定形 `.atomic-<8rand>.tmp`（20 字符），与目标名解耦。
2. Windows 下两条 wrap 规则（均在私有 leaf 内部，非 Windows 与短路径原样返回字符串）：`openable(path)` 针对"完整已存在路径"（replace/unlink），绝对长度 ≥260 用扩展长度形式（盘符/UNC/相对长路径先绝对化，幂等）；`stage_dir(parent)` 针对"要在其中新建有界 stage"的父目录，当 `abs(parent)+21 > 259` 即用扩展长度形式。这样只要父目录本身可达，stage 必然可建，短 basename 目标贴近上限也不会被 stage 推爆。
3. 关闭后 replace 的既有顺序、sync 语义、mode/encoding/newline、finally 清理本调用 stage 不变；PermissionError(winerror 5/32/33) 保持既有有界重试（4 次/35ms），FileNotFoundError/其他立即传播，错误类型不被路径处理改写。
4. 失败不丢原目标；不删其他并发操作 stage；不新增锁/后台重试/权限门；不能靠 cross-volume move 或全局 temp stage；扩展长度形式不向上层泄漏（caller 的 path 对象与 str 表示不变）。
5. gate scratch：调用专属、实际可写验证（mkdir+探针文件，各候选一次）、候选根按路径长度升序有限尝试（env TEMP/TMP/TMPDIR，无则 gettempdir()，加 PROJECT_ROOT，去重排序），全败抛出带每个候选失败原因的 RuntimeError；TEMP/TMP/TMPDIR/SQLITE_TMPDIR 统一隔离到 owned root；try/finally cleanup 覆盖 child 成功/失败/超时；不改选测、FAST_CONTRACT_CASES、超时、退出码、输出上限政策。

## B/C 已知设计决定与执行记录

- 新私有 leaf `src/company_wiki/_atomic_path.py`：`openable` + `stage_dir` 纯函数，无 I/O，mypy 干净。
- 消费方适配确认：`load_projection` 校验 `adapter.structure_parser_version == CWP_JSON_STRUCTURE_PARSER_VERSION` 且 `parser ∈ cwp_official_json/1.0.1|1.0.2`——集成夹具用真实常量。
- 消费方深目录局限（超出本卡写入边界，留 ROOT 决定）：`_projections_root` 用普通 `mkdir(parents=True)`，目录 >247 字符的 catalog_dir 会 `winerror 206`；本卡已让共享 writer 在深目录可写，消费者 mkdir 不在允许文件清单内，未改。
- RED 证据：logs/red-atomic-tests.log（6 failed/4 passed/1 skipped，含 `_atomic_path` ImportError）、logs/red-gate-tests.log（5 failed/3 passed）。RED 还抓到测试自身一处 newline 语义误解（`\n` 写方向=不翻译，非 CRLF→LF），已修为行为守卫。
- GREEN：logs/green-all-w22.log（41 passed/1 skipped，10.46s）；mypy 2 src 文件 clean；ruff changed files clean。
