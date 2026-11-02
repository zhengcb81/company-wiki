# StockWiki 技术节点独立验收

**PASS_TECHNICAL_NODE。** 原stockwiki-independent-r1两项P2及FAIL证据保留不改；当前仅签StockWiki R2冻结13路径和两条合成资料跨仓技术链，不签公司研究或项目总完成。

## 独立结果

- 新增公开反例11P/1.15s：坏同协议duplicate/NaN/重复schema不能被好回执洗白；真实普通日志允许；formatted artifact必须先验原始SHA；partial/context_only/not_reviewed不假晋升；引用/partition/as-of/字节与真实finite预算反控仍有效。
- 两条真实public CWP→Stock合成E2E加3项既有资源/路径控制，共5P/20.47s：原文export/verified-open/Stock CLI，以及叙述handler/projector publication/reference/read/Stock CLI均实际执行。使用ReplayNarrativeModel固定合成响应，0付费POST。
- explicit stdout/receipt超额在读取期间停止并回收真实孙进程；file://原文路径拒绝。Ruff冻结13文件全部通过。
- 13路径在实际E2E前后与作者R2 manifest完全相同；没有重跑136/27或整仓。

## 层次和事实边界

- Runtime StockWiki imports only its owned wire/process/source modules, never CWP private implementation. CWP internals are imported by isolated test fixtures only; production integration uses source/narrative public CLIs and versioned DTO.
- Narrative exact artifact original byte size/SHA checked before noncanonical JSON parsing; identity/source/period/as-of and source/evidence output hashes remain.
- Support/context evidence membership, disjoint partition and citation closure still validated; no source/reference correctness removed with count caps.
- Optional malformed/foreign/unavailable review remains not_reviewed; trace absence and source_processing_complete=False are preserved, not promoted to research acceptance or completed source processing.
- One process lifetime owner enforces actual explicit output/receipt budgets, timeout and descendant cleanup; no replacement fixed16K/256K/1.31MiB representation allowance.
- Lenient duplicate-pair parse is schema classification only. Source data always comes from strict parser; bad claimed protocol cannot be laundered by good receipt.

## 最终冻结

作者报告SHA `fcd5eebc12f7c96ac50f113a6e9b1bad3e7e56cf4ba29b692a6ddd79182057e3`。
- `stockwiki/_narrative_process.py`：`54c8545a30cf76be644aca912abc8791694a315d3024c2d78484459e0443c6e2`
- `stockwiki/_source_reader_v2_transport.py`：`328c21435f774f1e9af3223501517303207e5b9d357c16c16bbff4956d947892`
- `stockwiki/_narrative_wire.py`：`f4c423b87fdae5f1ac982b07ea652ab32970b78051b92cf72b548f2eb9edc8c0`
- `stockwiki/narrative_source.py`：`bd5dea3518c134cce4c1ad518093484f9080a693d9f25677db9edb4ddc6d2ea3`
- `stockwiki/_narrative_bundle.py`：`edb43d55030da547f54d2d2ea5175b21b42ee75f1782d85c8cb8b32cb76faa3b`
- `stockwiki/services/narrative_source.py`：`812b39e5f5cda7653242926ed1664bfc0d705c68391b78961d129bbc021ca162`
- `stockwiki/_source_reader_v2_wire.py`：`9c34e6b58b683a5056654dbddade6cb6dc90a629e2f185ed62f3b2220ae86ca2`
- `tests/test_r8_source_observations.py`：`8c871956c52887284a033b9d73ca9b9afbdf1506a9346775c7ac514400606873`
- `tests/test_source_export_v2_bounded_transport.py`：`b458f22170b87045e8737a18c8b30492ba7cfcb8c9873545e2c5d110cca7008c`
- `tests/test_narrative_reading_support_use.py`：`9e57639c77e0a13c1f48d519b2906660c6ad79333a419c0c5e0639f8ba3e4991`
- `tests/test_source_export_v2_cli.py`：`370f7724e007bfbeeb2a31140f89fb798ca75fe54ae09d9e2f3c581403427fb2`
- `tests/test_narrative_source.py`：`b517663513eae0595680713849256e62c12832ccc2be9c4ecdc9cd9a487e4998`
- `tests/test_narrative_source_cli.py`：`5b9416f7c6bddbef448e39b2915adecb91095937cbc6af5d0cb070225fcf2fcf`

## 保留限制与清理

- PASS covers this technical gate/transport node only, not full company research/extraction quality or project completion.
- 0real originals,0downloads,0model/provider/API/network calls; synthetic publication uses the explicit ReplayNarrativeModel fixture.
- No author source/test/Git/index/config/global writes. Existing untracked production/dashboard/run paths were listed only and left untouched.
- Ruff shared cache metadata was not inventoried/restored; no cache/foreign worktree cleanup guessed. All pytest basetemp/cache/logs are isolated under owned root.

独立脚本、逐条命令、完整日志/JUnit和前后13SHA在同名JSON。自有tmp/si7初始不存在，先留证后精确清理；最终收据随后补此报告。

最终清理收据：绝对父目录/非reparse已核，自有27文件/110416 bytes全部删除，tmp/si7恢复初始不存在。真实两E2E各自目录快照恢复断言也已通过；原件/配置/未跟踪他人数据不动。
