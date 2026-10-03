# G-D B1：重复 active snapshot 退役实际收据

## 结果

- 工具提交 `9f986adcb97ebc166a34c2772d4c64e183cb902b`，已普通推送 origin/master；[Actions 37115171888](https://github.com/zhengcb81/company-wiki/actions/runs/37115171888) 成功，单 job 55 秒。
- TDD 节点 **34 passed / 15.73s**，覆盖小型真实 catalog/raw、精确 snapshot dry-run/apply/repeat/crash、正式叙述 CLI 前后读取和来源工具分类；Ruff/host guard 通过，独立测试根删除。
- 生产工具 `scripts/retire_catalog_snapshot.py --apply` 只删除 `.source_catalog/catalog.sqlite3.bak-r6-20260927-061319`；该精确文件已不存在。逻辑释放 **3,055,796,224 B / 2.846 GiB**。
- 同卷 free 前后 `131192340480 → 134248095744 B`，增加 **3,055,755,264 B**。与逻辑删除相差 40,960 B，不将其他进程或文件系统变化硬归因本工具。
- 当前 `catalog.sqlite3` 完整 SHA 前后一致：`30794a01e04a9e77ec13cd7b27a3f24bf9861bda9fc7c3c50a2b362830fbc823`；mtime_ns `1790490231504738600`，大小保持 3,055,800,320 B。
- 原文目录没有进入操作范围；没有全库 raw 重新 hash、完整备份恢复或 zstd/gzip 删除。B2/B3 仍待实施。

## 机器收据与保留依据

生产 receipt：`.source_catalog/snapshot-cleanup/b26c0c427a5fd31ef72d965c/receipt.json`，intent 同目录。结果 `removed` / `reconciled=false`，candidate SHA `63c359aa4b09545a540a05f8d32d66ac3c9dbd4ccf696470d55cb38a31f6dcfc`。

退休 basis run `20260926T170825Z-4a9c67e1`：

| 保留依据 | 完整 SHA-256 |
|---|---|
| prepared.json | `cebcc51daf0a13a5f583273a1f0c3218f265fbe845fd8656e38cd82a30805cd9` |
| retired.json | `6f7f1b88b36aa93f22056627143fa3dd1c4bdd8d4ce3032ab1a1d4a78008b8e9` |
| catalog.full.sqlite3.zst | `1bc09746b8ee18db91fbbd14c97410241ad9a54d3f45a6468886692e763edd9e` |

archive 的实际完整字节 SHA/size 已核，6,198,704,362 B，继续保留；不声称本批执行了完整恢复。prepared shadow SHA 与 retired production SHA 均等于已删除 snapshot SHA。

## 空间口径

本轮前三根实测 45,748,203,875 B / 42.606 GiB，减此精确文件得到 **42,692,407,651 B / 39.760 GiB**，未重新全遍历。历史净释放 37.630 GiB 单列，不重复累计到本批。companies 原件/sidecar/legacy wiki 整体保留 25,198,502,813 B；后续 derived/index/archives 依据[G-D 分批细则](../../gd_storage_batches_2026-10-03.md)分别处理。
