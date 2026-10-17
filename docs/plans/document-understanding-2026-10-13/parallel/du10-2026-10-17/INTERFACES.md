# DU10 并行施工接口

## 母线接口

三个包独立产出自己的 PWF、提交历史和 handoff；它们不相互 cherry-pick、不依赖兄弟包的未提交文件。每个包只可触碰总表指定的一个仓库与卡内文件范围。ROOT 是唯一跨线接收人，负责将最终结果映射回母 PWF；作者不得修改母线其他包的进度。

## handoff.json 最少字段

```json
{
  "package_id": "DU10-...",
  "status": "COMPLETE|PARTIAL|BLOCKED",
  "repository": "absolute path",
  "branch": "branch name",
  "base_commit": "full sha",
  "head_commit": "full sha",
  "changed_files": [{"path": "repo-relative path", "sha256": "...", "purpose": "..."}],
  "tests": [{"command": "...", "exit_code": 0, "result": "...", "receipt": "..."}],
  "findings": [{"id": "...", "root_cause": "...", "fixed_in": "...", "test": "..."}],
  "independent_review": {"reviewer_id": "...", "reviewed_head": "full sha", "result": "PASS", "report": "...", "unresolved": []},
  "cleanup": {"owned_temp_restored": true, "raw_sha_unchanged": true},
  "provider_calls": 0,
  "remaining": []
}
```

`status=COMPLETE` 要求独审绑定 `head_commit` 且 `unresolved=[]`。其他状态保留准确剩余项，不能标 READY/COMPLETE。摘要报告不能代替命令退出码、哈希或原始证据。

## 独立审查流程

作者先完成实现、测试、清理并冻结提交，再单独委派另一 agent。审查 agent 使用独立上下文读取本卡、PWF、实际 diff 和 receipts；报告列出审查版本与文件 SHA。发现问题后作者逐项修复并重测，原报告保留；同一 reviewer 针对最终版本复核。完成前不能把工作交 ROOT，不能用自己的审查或另一个不同版本的旧报告替代。
