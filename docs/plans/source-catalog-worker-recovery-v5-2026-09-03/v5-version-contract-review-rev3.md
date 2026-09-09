# V5 版本合同 rev3：独立设计复审（G1 定点闭合检查，2026-09-09）

审查者：independent design review agent（非作者，复审）
范围：rev3 `v5-version-contract.md`（commit `30de11d`，branch `fcap`）、`tools/v5_*.py`、重生成的 `v5-version-reference-inventory.{json,md}`、`v5-baseline-equivalence.json`、README/findings/progress 的 rev3 更正行。
方法：只读复算。**两个证据工具并非只读**——它们各自 `Path.write_text` 覆写证据 JSON/MD，故未直接执行，而是用 importlib 载入并拦截 `Path.write_text`，在内存中复现其输出后与已提交文件逐字节比较（未在磁盘写任何证据文件）。

结论：**rejected**。G1 主体已闭合——冻结集合 51 = 48 + 3、条目类型与 `v5_own` 枚举、`frozen_set_composition`、N13/N14 重写、N16/N17 新增，均经本次复算成立；但存在**一处自相矛盾使 N17 不可实现**：N17 规定 `evidence_tools[]` 缺失即拒绝（`:120`），§5.2 亦称两个证据工具「记为 `evidence_tools[]`」（`:65`），而 §5.1 的字段清单（`:51`）没有该字段，且 §5.1 `:50` 规定 `additionalProperties: false`、N4（`:107`）对未知字段直接拒绝——含 `evidence_tools` 的 manifest 被 N4 拒、不含的被 N17 拒，二者不可同时满足，V5-2 必须再决策。另：§5.1 写「必填字段 17 项」而实际列举 18 项（`:51`）。G2 部分关闭（progress.md:13、findings.md:41 仍写死 64，实测 72 tracked）；G3/G4/F7 关闭；新增 H1（P2）、H2/H3（P3）。

## 闭合判定

| ID | 原级别 | 状态 | 证据（本次复算） |
|---|---|---|---|
| G1 集合定义 | P1 | partially closed | 51 项 = 48 `baseline/plan/**`（复算：29 schema + 11 prose + `findings.md` + `plan_review_findings.md` + 4 `.v4.json` + `plan_consistency_check.py` + `plan_freeze_check.v4.txt` = 48）＋ 3 个 v5 自有治理件（`:56-62`）；条目类型 `{path,sha256,size_bytes,equivalence}`、枚举含 `v5_own`（`:42,56`）；`frozen_set_composition{48,3,51,1}` 与 `normative_file_count` 一致（`:64`）；证据工具入 `evidence_tools[]` 非 normative（`:65`）；N13「恰等于 51 项」（`:116`）、N14（`:117`）、N16/N17（`:119-120`） |
| G1 阻断项 | P1 | **open（阻断）** | N17（`:120`）＋§5.2:65 要求 `evidence_tools[]`，§5.1 字段清单（`:51`）无此字段；§5.1:50 `additionalProperties:false` ＋ N4（`:107`）拒绝未知字段 ⇒ N4 与 N17 不可同时满足。修法：把 `evidence_tools[]`（`{path,sha256,size_bytes}` 条目、必填）加入 §5.1，并将「17 项」改为实际项数 |
| G2 | P3 | partially closed | 合同 `:75` 已改为「精确 tracked 数由 `git ls-files` 实时查询（不写死）」；但 `progress.md:13` 仍写 `git ls-files`=64、`findings.md:41` 仍写 64（带「另 5 份随后提交」限定）；实测 **72 tracked** |
| G3 | P3 | closed | 合同 `:76`、`README.md:30`、`findings.md:44`、`progress.md:14` 均为 `2026-09-07T18:08:52Z` UTC（并标注本地 19:08:52+01:00） |
| G4 | P3 | closed | `v5-baseline-equivalence.json` 键为 `v4_exact`/`crlf_only`/`unproven_new_baseline`（计数 21/17/10，`unresolved`=0），与工具内存复现**逐字节相同**；残留：该 JSON 仍含 `unresolved` 桶、无 `v5_own` 键，§4:42「与证据 JSON 一致」措辞不精确 |
| F7 | P2 | closed | `v5-version-reference-inventory.md:3` 已改为「`baseline/**`（54 份）＋ v5 根目录规划文档（5 份）＝ 59 份」；该 .md 由工具重生成并与复现**逐字节相同** |
| H1（新） | P2 | open | 已提交的 `v5-version-reference-inventory.json` **无法由其自身工具复现**：`README.md`（盘 4303 B/`55d697f2…` vs 实际 4307 B/`a83c3b2f…`）、`findings.md`（4618 vs 4646）、`progress.md`（7478 vs 8032）为改前值；totals（59/44/14/11/9、`$id` 29、后缀 14/12/2/1）与复现一致。非阻断：§3:34 已要求冻结前重生成，且三份根文档不在 51 项冻结集内 |
| H2（新） | P3 | open | §6.2:80「v5 目录 71 文件 = 12 根 + 54 + 3 + 2」；实测 **72 = 13 根 + 54 + 3 + 2**（根目录含 rev2 审查文件未计）。硬编码目录数属 G2 同类脆弱点（本文件写入后即为 73） |
| H3（新） | P3 | open | 两个证据工具并非只读：`v5_version_reference_scan.py:91,135` 与 `v5_equivalence_check.py:61` 直接 `write_text` 覆写证据 JSON/MD；在漂移树上运行会静默改写被哈希绑定的证据。建议加 `--check` 模式或在 §6.2 写明「复现会改写证据文件」 |

## 对三项指定问题的回答

1. **「v5 checker 入口」名称**：仍留待 V5-2 定名（`:61`），故 N13 的「恰等于 51 项」与 N16 在冻结前无字面清单可判。建议 §5.2 明确：该条目的 `path` 即 `pre_freeze_check.command` 中出现的脚本（`:66` 已要求二者同时出现），`equivalence` = `v5_own`。
2. **`frozen_set_composition` 如何校验**：目前仅 `total` 与 `normative_file_count` 一致（`:64`），类计数缺推导规则。建议写明：`imported` = `equivalence ∈ {v4_exact, crlf_only, unproven_new_baseline}` 的条目数；`v5_own_governing` = `v5_own` 条目数；`self_excluded` = 1。
3. **`.gitattributes` 哈希是否跨 checkout 稳定**：**稳定**（实测）。工作树字节 = `HEAD` blob 字节（172 B、纯 LF、sha256 `88182b266065f970…`）；`git hash-object --path=` 与 blob oid 相同；`git check-attr text/eol/filter/working-tree-encoding` 全为 unset（`* -text …` 对自身生效，覆盖 `core.autocrlf=true`）。故 N14 的哈希绑定可执行，漂移会 fail-closed。

## 声明

本复审只读、非作者；除本文件外未写入任何文件——复现工具时未在磁盘生成证据文件，importlib 载入产生的 `tools/__pycache__/` 已删除，`git status` 已恢复为空。未提交、未运行产品测试或旧 checker/worker、未联网。本审查**只绑定规划文档完整性**，不授权实施。rev3 未通过：G1 阻断项（`evidence_tools[]` 与 N4／`additionalProperties:false` 冲突）修复前，不得生成 `plan_manifest.v5.json`，不得进入 V5-2 冻结。
