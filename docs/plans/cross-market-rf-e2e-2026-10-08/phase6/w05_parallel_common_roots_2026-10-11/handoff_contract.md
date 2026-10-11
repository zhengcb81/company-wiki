# W05 共用交接格式（记录接口，不是人工许可）

每张卡的工作树已存在。只在该树创建 `.planning/w05-<lane>/task_plan.md`、`findings.md`、`progress.md` 和 `docs/handoffs/w05-<lane>/`。不写CWP六份总PWF，不碰其他人的run或安装目录。

## handoff.json

```json
{
  "schema_version": "w05-lane-handoff/1",
  "lane": "W05-CWP-OCR",
  "status": "COMPLETE|PARTIAL|BLOCKED",
  "repository": "absolute repository path",
  "workdir": "absolute assigned worktree path",
  "base_commit": "full SHA",
  "head_commit": "full SHA or null if no commit",
  "branch": "codex/assigned-branch",
  "changed_files": [{"path": "repo-relative", "sha256": "actual file SHA", "purpose": "why"}],
  "input_evidence": [{"path": "absolute or handoff-relative", "sha256": "actual", "bytes": 1}],
  "interfaces": [{"name": "public seam", "before": "old meaning", "after": "new meaning", "compatibility": "tested boundary"}],
  "tests": [{"phase": "RED|GREEN|INTEGRATION|E2E", "command": "exact", "exit_code": 0, "counts": {}, "elapsed_seconds": 1, "log": "relative", "log_sha256": "actual", "scope": "what it proves"}],
  "findings": [{"id": "stable id", "root_cause": "mechanism", "disposition": "fixed|diagnostic|remaining", "test_ids": [], "evidence": []}],
  "cleanup": {"owned_root": "absolute", "baseline": "manifest path", "after": "manifest path", "restored": true, "raw_unchanged": true},
  "cost": {"provider_calls": 0, "model_calls": 0, "paid_usd": "0", "unknown_charge": null},
  "space": {"retained_bytes": 0, "scratch_peak_bytes": null, "measurement": "actual|not_measured"},
  "remaining": [],
  "root_next_action": "integration, not claimed already merged"
}
```

枚举字符串在真实JSON填写一个值，不能抄 `COMPLETE|PARTIAL|BLOCKED`。未执行/未知值如实用null/NOT_RUN，不能记作零/PASS；离线合成费用单列 synthetic，不进生产母账。manifest.json列所有交接证据的相对路径、实际字节和SHA，自身不递归哈希；不把原件二进制复制入Git。

`handoff.md` 是人可读摘要：根因、真正实现、接口、新旧行为、TDD失败与修复、集中测试、临时恢复、正常commit、剩余事项。完整日志有界，不能把关键失败的截断输出说成完整。

## 三个大节点

1. 先写行为/反例测试，保留现实现的真实RED。缺依赖、路径错误、导入失败不是业务反例已复现；先修测试环境再判定。
2. 完成责任层代码，运行相关快速单测+集成+独立目录端到端；正常hooks和lint。有真实数据的本地OCR属于显式一次性工程E2E，不塞进每次commit默认CI。
3. 一次最终交接。ROOT独立审接口并合并，跨仓公司研究另在原有G2/G4/G5做；不要每个小函数请协调员签收。

## 隔离与空间

测试前记录自己scratch根的初始清单/现有文件SHA，默认新根初始不存在；下载为0。只删本线生成且核对边界的临时文件，测试后恢复原样，保留小型失败/成功日志和定位。已有原件/其他owner文件/生产配置不能当scratch。不要完整恢复备份演练，不全湖扫/hash/copy。

推荐持久交接每线≤8MiB、scratch峰值≤64MiB；若真实必要证据超限，解释实际增长并优先去重，不把这个工程约定增加成新的人工许可。正常commit已验证代码和本线小型记录，保持对主线未合并的诚实表述；不force、不跳hooks、不自行安装或推主线。
