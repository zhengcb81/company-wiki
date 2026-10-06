# 旧派生存储维护工具

本工具提供盘点、旧派生文件退休、显式范围切片删除和 SQLite 压缩。它不会改变原始资料、来源事实或新叙述摘要。生产执行顺序见 company-wiki 总 PWF 的 S5/S6；工具验收通过不表示生产清理已经完成。

## 使用

先设置 `PYTHONPATH=src`，收据和 manifest 保存到资料目录与 catalog 之外：

```text
python tools/legacy_storage_retirement.py inventory --config <catalog-config> --output <manifest.json>
python tools/legacy_storage_retirement.py retire-derived --config <catalog-config> --manifest <manifest.json> --receipt <report.json>
python tools/legacy_storage_retirement.py prune-spans --config <catalog-config> --selection <selection.json> --keep-refs <keep.jsonl> --receipt <report.json>
python tools/legacy_storage_retirement.py vacuum --config <catalog-config> --receipt <report.json>
```

后三项默认仅预览，加 `--apply` 才执行。一次明确操作即可，无人工签收文件。报告路径不能覆盖配置、catalog 或资料根。

`selection.json` 示例：

```json
{"schema_version":"cwp-span-selection/1","parser_name":"plain_text","parser_version":"1.0.0","source_ids":[],"document_ids":[]}
```

空 ID 列表表示选定 parser/version 的全部记录；缺省 version 表示该 parser 的全部版本。生产范围由真实旧消费者退出情况决定，不能把示例当作生产删除指令。无效类型/空 parser/schema 错误均拒绝。`keep.jsonl` 每行是实际存在的 `source_id` 与 `locator`。

## 恢复与计量

- manifest 只是选择和已有观察值。删除前读取当前 DB 身份、路径、hash；不递归扫删未知文件。
- 先退休旧 artifact 句柄，再删其已验证文件。中断后复用同一 manifest；已退休未删除的文件可续删，缺失仅计 `already_absent`。sections 恢复只保存小型路径/hash，正文不备份。
- 同一路径的已知旧parser别名一并在事务内退休，历史失配SHA保持原样，删除只用已验证候选的实际字节。未知/活跃/跨document或source共享引用阻止整个物理组删除；未选中sections的子文件不能单独删除。事务内再次复核共享行集合，新增或变化即拒绝，不会先删后发现。
- `candidate_bytes` 按规范化物理路径去重，sections成员与独立记录共享时仅算一次；`candidate_count`仍是记录数，`candidate_file_count`是唯一候选路径数。实际释放以删除记录与前后计量为准。空generator仅在绑定document SHA的旧`derived/{sha[:2]}/{sha}/summary.md`布局识别，其他未知对象保留。
- span 删除在既有 catalog 锁与单个 SQLite 事务内执行，保留 keep/范围外 parser。报告聚合数量，不输出百万 span 清单。保留行计 `kept_pairs`，不计 `already_absent`。
- 静态库预览不创建 WAL/SHM；活动 WAL 需要既有 SHM。预览不拿写锁或修改库。
- VACUUM 前后分别核 source、新 final、旧记录的确定性 digest、完整性和物理页数。额外空闲空间保守按当前库两倍检查；标准 VACUUM 会使用 SQLite 临时空间，不创建永久第二份完整库。磁盘 free-space 与 DB 文件释放量分列。
- busy、unlink、SQL、checkpoint 或读取失败返回非成功；不宣称失败后库未动。压缩后无法观测的字段为 `null`，`after_measurement_available=false`。根据当前状态与小收据接续。

## 节点验收

所有专属测试在 `tests/integration/test_p5_storage*.py`，共享真实 schema/parser 夹具在 `tests/support/p5_storage_catalog_fixture.py`。真实年度 PDF + 微软电话会 TXT E2E 为 `slow`，只在存储迁移节点运行；日常全 Unit CI 不新增这个长包。E2E 使用公开原文及叙述 reader/完整 locator replay，最终关闭连接并删除唯一测试根，小型空间计量通过 JUnit property 保存。

原交付收据在 `docs/implementation/handoffs/P5-STORAGE/`；最新主线验收以总 PWF 的 `harness_lanes/results/p5_storage_integration_review_2026-10-05.md` 为准。生产删除仍等待 RF 默认来源读取迁移与 CWP 旧正文/质量调用者退出。
