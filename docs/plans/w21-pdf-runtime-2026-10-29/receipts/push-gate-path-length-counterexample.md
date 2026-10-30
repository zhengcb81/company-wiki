# 最小反例（交ROOT）：投影持久化缺 MAX_PATH 预算，被长工区名+gate basetemp 重定位触发

日期：2026-10-30。W21 工区车道按卡边界不修改共享层，此文档为移交 ROOT 的最小反例。

## 现象

`git push`（本分支）被 pre-push gate 的 CI contract smoke 阻断：

```
FAILED tests/contract/test_narrative_availability.py::test_projected_two_parents_cannot_borrow_one_raw_proof
FileNotFoundError: [Errno 2] No such file or directory:
  ...cw-pytest-basetemp\...\test_projected_two_parents_can0\subject-artifacts-...\catalog\projections\
  bf7335288eed182233deb2c57c536587f7957c74bfd3d0564f22441aa98b8c03.json.7whd3gux.tmp
```

同一测试在 gate 环境外单独运行必过；gate 内 100% 复现（本工区）。

## 根因（逐帧）

1. `persist_projection`（`src/company_wiki/source_catalog/official_json_projection.py`）先 `mkdir(parents=True)` 目录成功，再走 `atomic_output(path, sync=True)`。
2. `atomic_output`（`src/company_wiki/_atomic_file.py`）用 `NamedTemporaryFile(dir=path.parent, prefix=path.name+".", suffix=".tmp")`——staging 名 = 64位SHA + ".json" + "." + 8随机 + ".tmp"（82字符）。
3. `tempfile.py:257` 的 `os.open(file, O_CREAT|O_EXCL)` 报 ENOENT：**文件全路径超过 Win32 MAX_PATH**。`_projections_root` 的 mkdir 成功是因为目录路径本身未超限，只有完整文件路径超限。
4. 环境前提：本机 `LongPathsEnabled=0`（注册表实测），python.exe 清单未生效长路径。

## 长度对照（决定性）

| 结构（gate 的 basetemp 布局） | 工区 | 全路径字符 | os.open |
|---|---|---|---|
| `cwpp-*\cw-pytest-basetemp\<ts>\test_projected_two_parents_can0\subject-artifacts-*\catalog\projections\<sha>.json.<rand8>.tmp` | company-wiki-w21-pdf-runtime | **270** | **ENOENT（失败）** |
| 同上 | company-wiki | **254** | OK |

ROOT 主线从未触发的原因：主工区名短 16 字符，254<259。W21 工区名 + gate 将 TEMP/basetemp 重定位进 worktree（`pre_push_gate._run_pytest_gate` 的 `cwpp-*` 布局）恰好把该测试的投影文件路径推过 259。

## 缺陷定位（供ROOT修复参考，不跨范围改）

- `persist_projection` 无路径预算检查；同库 `canonical_writer` 已有先例：`_canonical_destination` 用 `suffix_reserve`/`available` 显式预算并命名拒绝（`canonical_root_path_limit`）。
- 候选修复（ROOT 决定其一）：
  1. `persist_projection` 写前做同款预算检查并命名拒绝；
  2. `atomic_output` 缩短 staging 名（如哈希化前缀）；
  3. gate 的 `cwpp-*` basetemp 用更短根（例如 %TEMP% 下短目录或盘根短名）——注意 `_run_pytest_gate` 注释表明当前选择是为了规避 hook 限制进程访问宿主 TEMP。
  4. 启用机器级 LongPathsEnabled（环境级，非仓库级）。

## 对 W21 交付的影响

- 本包全部生产/测试/收据与该缺陷无关（失败测试属 source_catalog 投影层；W21 相关面 186+ 测试全过；全量 unit 失败集经基线对照为零回归）。
- 推送被门禁按协议阻断；本卡不绕过。ROOT 在主工区（短名）集成本补丁时 gate 不触发此问题（254 OK）。
- W21 车道遵守边界：未修改 `official_json_projection.py`、`_atomic_file.py`、`pre_push_gate.py` 中任何一处。
