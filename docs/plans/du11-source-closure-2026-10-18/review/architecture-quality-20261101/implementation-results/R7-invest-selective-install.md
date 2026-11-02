# R7 invest 指定文件安装同步交接

状态：**IMPLEMENTED / FROZEN，待 ROOT 直接审查**。本轮没有实际全局部署、commit/push 或修改 ROOT17、RF/CWP 其他源码、CI/hooks/主 PWF。

只修改现有 canonical `invest-skills/tools/sync_installations.py`，新增一个 `invest-core/tests/test_targeted_install_sync.py`；没有另造安装器/报表框架或人工许可文件。

## 调用与行为

```powershell
python tools/sync_installations.py --canonical SOURCE --destination ROOT_A --destination ROOT_B --destination ROOT_C --file invest-core/scripts/invest_contracts.py --file tests_support/revenue_fixtures.py
# 核对后，在同一明确选中文件请求上增加 --apply 执行；无需另签授权文件。
python tools/sync_installations.py --canonical SOURCE --destination ROOT_A --destination ROOT_B --destination ROOT_C --file invest-core/scripts/invest_contracts.py --file tests_support/revenue_fixtures.py --apply
python tools/sync_installations.py --canonical SOURCE --file invest-core/scripts/invest_contracts.py --print-manifest
```

- `--file component/relative` 可重复；只读取/核对/写选中文件，不枚举或要求其它组件存在。无 apply 的核对不创建安装目录。
- 预先解析选中路径与 aliases；同一实际目标只处理一次，不同 canonical 内容争用同一物理文件在写入前拒绝。
- 每个文件在目标旁 stage、flush/fsync、原子 replace，再核真实落盘 SHA。已经同 SHA 则不建 stage、不 replace，mtime/inode 不变。
- 不改 junction/目录链接本体，合法组件别名可沿真实文件更新。嵌套引用不能越过 canonical/本次明确安装组件范围；canonical alias 本来相同则零写。
- 未选中的 unknown/config/output/code 不读不删；不替换整个组件。单文件失败报 ERROR/PARTIAL，已成功前项保留，不假称整体回滚；续跑只写未完成项。
- 不提供 `--file` 时现有显式全量 apply/check/manifest 模式保持兼容；Git hooks 不会隐式调用它。

## 实际验证与冻结

TDD **10F1P/0.77s → 11P/0.75s**；补实际 CLI/冲突别名与部分失败续跑后，最终 **13P/1.61s**。两个 Python 文件 Ruff 绿。全部为自有临时安装根、合成字节和真实 Windows junction，没有原件、key、网络或模型。

覆盖三安装根/别名去重、未知配置与输出保留、重复零写、原子替换中途失败及续跑、canonical alias、不安全 path、写前 alias 冲突、fresh CLI，以及旧 full/check 正控。JUnit 和控制台保存在同名 JSON。

| 文件 | SHA-256 |
|---|---|
| canonical tools/sync_installations.py | `14c443de2df4fbb40db067ab5841d2812144e91aede7a8cedcb272b3aab09996` |
| invest-core/tests/test_targeted_install_sync.py | `4bcb95632e5786c7630c55bb3f8236334608af7df7a54dbcef2da1072eaa4fb6` |

以上表格是原13P绑定的历史版本。ROOT 随后指出 canonical alias 的源更新竞态，已直接返修：

- snapshot 后 canonical 被正常 writer 更新时，旧版会把旧数据写回源，实际新反例 **1F/0.35s**。
- 当前先保同 SHA 零写；若不同 SHA 目标与 canonical 路径/physical file 相同，明确 `source_changed/PARTIAL`，不建 stage、不改新源或 junction。
- 只复验新反例＋原 canonical alias＋partial 续跑，**3P/0.36s**；Ruff两文件绿。保留原13P历史，不冒称14例全组重跑。

当前冻结 SHA：

- `C:\Users\郑曾波\Projects\invest-skills\tools\sync_installations.py`：`605beabfef388aba0336384c67e394eaa6a18ea83ecf7ddb97f0eb2adf949e2e`
- `C:\Users\郑曾波\Projects\invest-skills\invest-core\tests\test_targeted_install_sync.py`：`77281bd82eb2c5642132d204bfe7fe1ac1f8b7932b6dcdf4a85005b66d07413a`

两个源码再次停写，ROOT 可据此直接审查并使用同一个 canonical owner 做后续定点部署。本交接不声称全局副本已同步。

自有 `tmp/r7s-fb707c` 初始 absent，必要测试收据已保存；已完成精确绝对路径/无 reparse 检查，清理184文件、60,717逻辑字节并恢复 absent；源码两 SHA 清理后再核相同。STOP。
