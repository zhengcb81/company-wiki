# S5首批缓存清理完成

- 代码基线：`349d331e64c84e721b45c4c43ac1c58ffa291815`。
- 机器收据：[s5_first_cache_cleanup_2026-10-04.json](s5_first_cache_cleanup_2026-10-04.json)，`s5-cache-cleanup/1`，status=success。
- 2026-10-04 22:21:38–22:26:27 UTC，在同一正常账号PowerShell内完成路径包含、reparse、当前进程、paused状态、前后保护快照和限定集合删除。耗时主要来自一次性原件清单/整库SHA保护检查，不加入commit/CI日常门。

| 已删除集合 | 文件数 | bytes |
|---|---:|---:|
| index | 8 | 45,052,670 |
| drills（旧演练库副本） | 3 | 77,283,328 |
| parser_tmp（旧孤儿结果） | 1 | 1,915,919 |
| qa（旧PNG） | 1 | 241,780 |
| wheel-test | 1 | 212,051 |
| worker_runs.jsonl | 1 | 12,310,654 |
| worker attempt stdout/stderr日志 | 908 | 1,631,621 |
| **合计** | **923** | **138,648,023** |

释放量为已删文件逻辑大小138.65MB（0.139GB）；未声称整个磁盘free-space净增或本轮全仓总量已重新实测。七类目标路径删除后全部不存在，恢复材料未再复制成一套大备份。

## 保留与端到端结果

- 公司原件33,133个、25,198,502,813 B，文件路径/size/mtime清单摘要前后相同。全量原件不重新hash；正式CLI实读四份代表资料的bytes SHA。
- 生产catalog.sqlite3为3,055,841,280 B，前后完整SHA相同：`fde7c8a2ea4d2dd15f1009d32423b4155e644be4f848c65fb2c00e9a441470e0`。来源事实没有写入或删除；当前DB比早期审计基线略大，不把差额算清理收益。
- derived、staging、security_master、新artifacts、旧N4C失败run清单前后相同；worker control/state、runtime policy、legacy periods、两份生产配置SHA前后相同。未知模型reservation保留，原件删除0，DB mutation0，network/model调用0。
- 用正式`company_wiki.source_catalog.source_reader_cli`在清理前后各读4份真实原件（年报、招股书、IR、季报），共8次。每轮12,343,802 B，SHA/size/来源ID/读取policy均匹配；stdout仅在内存校验，没有原件副本或付费HTTP。证据摘要合并保存在机器收据中。
- 一次性脚本及两份重复的临时读取结果退出删除；本报告和JSON为保留收据。没有代码变更，不跑全仓长测。

## 尚未完成

S5仍in_progress：2.826GB旧derived、8,191条artifact记录和占库主要部分的旧全量EvidenceSpan未删除。RF当前main仍有旧默认消费路径，CWP旧section入口仍有依赖；按[S5/S6实施细则](../../s5_s6_legacy_storage_implementation.md)先迁移/退出入口，再做主体降容。N4C模型/选材两卡集成、真实摘要及并行吞吐仍待完成。
