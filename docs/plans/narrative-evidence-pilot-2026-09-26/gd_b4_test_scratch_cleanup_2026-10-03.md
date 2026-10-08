# B4补批：旧测试临时目录清理（2026-10-03）

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

## 范围与依据

本卡只清理下表24个 `C:\Users\郑曾波\Projects\company-wiki` 的直接子目录。独立空间盘点已确认它们来自历史 pytest/CI 排错：mock lake、临时 SQLite/WAL、JSON 断言文件，以及 fake PDF；两份849B PDF 为测试生成的单页夹具。未发现唯一下载原件或 reparse。已读文件共14,543,053B。普通用户读失败是 pytest 创建账号 `CodexSandboxOffline` 的 owner-only ACL；用创建账号 `use_default` 上下文操作，无需更改生产或临时目录 ACL。

**执行前逐根复核：**解析绝对路径必须恰好等于下表项目内直接子目录，所有祖先及子项不得为 reparse。有限统计必须可读，且大小/文件数与下表一致；若嵌套目录仍因另一账号权限不可读，整根保留并记录 hold，不能推测空目录或强改 ACL。执行前检查进程 commandline 无这24个唯一根名；这不是完整 open-handle 检查，删除失败也计 hold。不得泛化为删除 `.rf-*`、`pytest-of*`、所有测试目录或 managed worktree。

| 精确根名 | 已读字节 | 已读文件 |
|---|---:|---:|
| .rf-ca301-safe-20261003 | 0 | 0 |
| .rf-ca301-suite-20261003 | 17 | 1 |
| .rf-ca301-suite-20261003b | 16 | 1 |
| .rf-ci-first-failure-20261003 | 51223 | 30 |
| .rf-ci-first-safe-20261003 | 51223 | 30 |
| .rf-ci-focused-temp-20261003 | 3798 | 1 |
| .rf-ci-focused-temp-20261003b | 3798 | 1 |
| .rf-ci-rest-base-20261003 | 1652338 | 296 |
| .rf-ci-rootcause-base-20261003 | 3124071 | 117 |
| .rf-ci-rootcause-base2-20261003 | 3474375 | 137 |
| .rf-ci-second-firstfail-20261003 | 1912849 | 60 |
| .rf-ci-suite-final-20261003 | 4009583 | 310 |
| .rf-ci-tail-base-20261003 | 258048 | 1 |
| .rf-compat-tests-base-20261003 | 16 | 1 |
| .rf-fc1102-current-wiki-20261003 | 0 | 0 |
| .rf-fc1102-temp-20261003 | 0 | 0 |
| .rf-fc1307-tmp-20261003 | 0 | 0 |
| .rf-meta-tests-20261003 | 0 | 0 |
| .rf-prepush-tmp-20261003c | 0 | 0 |
| .rf-source-reader-guard-20261003 | 0 | 0 |
| .rf-source-reader-guard-20261003b | 0 | 0 |
| .rf-zr1102-collect-20261003 | 0 | 0 |
| .tmp-pytest-narrative-cap | 849 | 1 |
| .tmp-pytest-narrative-g1 | 849 | 1 |

## 操作与收尾

1. 复核上述边界；对每个通过的精确根，用 PowerShell `Remove-Item -LiteralPath` 顺序递归删除，不构造其他 shell 命令，不使用 takeown/icacls/reset/prune。
2. 产出 `harness_lanes/results/test_scratch_cleanup_2026-10-03.json` 和同名 `.md`，逐根记录扫描、删除/hold、实际新释放字节与复查不存在。失败独立保留；不能将不可读字节计为释放。
3. 核对当前主库size/mtime、Worker paused以及三资料根统计未变；不重新hash25GB原件，不启动Worker，不新增产品测试门。
4. root更新PWF和最终盘点，正常账号Git显式add/commit/push。此前12.152904GiB不包含本卡字节，独立列补批收益。

这是已授权一次性整理，无产品逻辑变更；没有新增小节点人工审查。历史24根不可读统计在执行收据确认后才可被覆盖。

## 执行补充：只读属性（同一范围）

首轮普通删除15根，实删259,795B；余9根14,283,258B完整可读且与清单一致，普通删除返回hidden/system/read-only提示。对首轮收据中这9个精确hold根，允许同一创建账号使用 `Remove-Item -LiteralPath -Recurse -Force` 清除测试只读/隐藏属性阻碍；这不修改ACL或扩大范围。仍须复核路径、reparse、bytes/files；若Force仍拒绝则保留，不进一步改ACL。首轮收据保留其原plan SHA，追加 `test_scratch_force_cleanup_2026-10-03.json` 记录本补充与每根真实结果，避免将首轮hold写成已经删除。

## 最终状态

24根全部已删除，实删14,543,053B，无剩余hold、无ACL改动；两阶段收据保留。最终完整stat0读取错误，三资料根和主库stat/control不变。见[最终收尾](harness_lanes/results/gd_storage_final_cleanup_2026-10-03.md)。
