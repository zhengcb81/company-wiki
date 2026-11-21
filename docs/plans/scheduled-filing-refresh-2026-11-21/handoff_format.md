# 施工包交接格式

每张卡在所属仓提交同名 Markdown 与 JSON。Markdown 给复现者记录最小命令、输入范围、观察结果和剩余项。JSON 给总控校对候选与测试版本。缺少真实环境的测试明示待组合，已经跑过的测试列实际退出码和可核证据。

```json
{
  "package_id": "SR-CWP 或 SR-DASH",
  "owner_repo": "所属仓",
  "base_commit": "完整 SHA",
  "delivery_commit": "被验证的源码提交 SHA",
  "release_state": "candidate",
  "interface": {
    "protocols": [],
    "entry_points": [],
    "deployment_config_keys": []
  },
  "verification": [
    {"case": "A1 等", "scope": "unit/integration/e2e", "command": "可重放命令",
     "tested_commit": "完整 SHA", "exit_code": 0, "evidence_ref": "回执相对路径"}
  ],
  "independent_review": {
    "tested_commit": "完整 SHA",
    "result": "pass",
    "findings_and_repairs": [],
    "evidence_ref": "审查记录相对路径"
  },
  "cleanup": {"temporary_root_restored": true, "production_write_count": 0},
  "remaining_for_integration": []
}
```

测试和审查记录应绑定最终实现提交。只补交接文档可另作提交。总控核对提交范围、依赖、实际接口、失败恢复和所有具名余项后，安排各 owner 并线和组合验收。
