# N6-FOOTPRINT: 唯一施工入口

本线目标/写集/接口/测试/交接只取 docs/implementation/handoffs/N6-FOOTPRINT/INPUT_CARD.md。基线58b74d07dd4f8b589c134ef9060a689864a8c089，PLAN_ID=n6-footprint。MAIN拥有共享入口与总PWF。

| 阶段 | 状态 |
|---|---|
| 接口与TDD反例（口径/分类表 + Unit RED） | complete |
| 本线实现（只读扫描/聚合 → Unit GREEN） | complete |
| fixture联调 + 真实限额扫描/交接 | complete |

## Next Step

已推送 `origin/codex/n6-footprint`=`12f73db`（delivery `ba19571` + handoff `12f73db`，pre-push 门禁 GREEN），全部阶段完成，等待 MAIN 验收。验收后由 MAIN 决定是否将处置建议与现有存储层对接；done 仅指工具可信、真实限额扫描与小报告交付，不等于空间已释放。

启动先核HEAD/status，输入PWF/card是MAIN创建的新文档，可随本线提交；不执行旧N5/根总计划。无原件/配置/owner写入、0付费模型，临时根恢复原样。

## Decisions Made

- 报告 schema 固定 `cwp-storage-footprint/1`，上限 256KiB；`allocated_bytes` 恒为 null 并在 limitations 说明，不使用 GetCompressedFileSizeW/cluster 估算。
- 分类为互斥路径规则（首条命中生效），8 类：raw_originals / curated_final_summaries / databases / auto_recovery_materials / tmp_test_cache / plans_reports / git_code / unknown；分类只计已实测文件，reparse/云占位条目单列 skipped + skipped_samples(≤20)。
- AUTO store 标记目录内全部文件（含 automation.* 数据库）归 auto_recovery_materials，保留判断恒为 undetermined，绝不凭 mtime 判终态。
- 退出码：0=报告已写（complete 或 partial），2=refused（不写文件），1=内部失败（临时文件清理、目标不存在）。
- Windows 下 `DirEntry.stat(follow_symlinks=False)` 不带 inode，故已实测文件改用 `os.lstat` 取大小+身份；symlink 无权限时用 junction（`mklink /J`）做越界反例。
- 真实扫描输出先落本线 tmp、校验后移入 handoff 目录并删除 tmp（回原样）；保护证据 = 扫描前后 config sha256 + 生产库 stat/listing + 5 份原件 metadata，原件内容读 = 0。

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| 误在源仓创建 fixture 目录（bash 未钉 workdir） | 1 | 立即 `rm -rf` 删除，源仓 git status 复原；后续所有命令钉 worktree workdir |
| 单元 RED：`ImportError: cannot import name 'classify'` | 1 | 预期 RED（实现未写），随后实现转 GREEN |
| `logical_path_bytes` 差 2 字节 | 1 | `Path.write_text` 默认换行翻译 `\n`→`\r\n`，fixture 写入改 `newline=""` |
| 硬链接 `identity_available=false` | 1 | `DirEntry.stat(follow_symlinks=False)` 在 Windows 返回 `st_ino=0`，改用 `os.lstat(entry.path)` |
| 守卫测试命中 report.py 里的说明文字 `GetCompressedFileSize` | 1 | limitation 文案改为 OS 压缩尺寸 API 措辞，守卫保持零命中 |
| symlink 创建被拒（WinError 1314 权限） | 1 | `make_dir_link` 回退 `cmd /c mklink /J`（junction 无需管理员） |
| ruff F841：未使用变量 `root` | 1 | 删除该 fixture 行 |
| 保护收据 `originals_sampled=0` | 1 | `raw/` 下只有子目录，改 `rglob` 每家公司取 1 份、共 5 份原件 metadata |
| pre-push 门禁结构红：lane 工作树 basetemp 68>60 字符 | 1 | 不 `--no-verify`、不改共享门禁（写集外）；按 owner 选定改用短路径临时 worktree 完整过门禁后推送，随即删除临时 worktree |
