# W06 独立 major 审查（2026-10-09）

结论：暂不通过。源码实现和真实微软复验已改善原问题，但缓存可用快速路径仍会把实际公司或期次矛盾的原文返回 ready。先补下面的 RED，再由责任实现者修复；本审查未改源码、主 PWF 或安装副本。

## 审查对象和已验证部分

- Worktree：`C:/Users/郑曾波/.codex/worktrees/audit-provider-cause/company-wiki`。
- 源码 commit：`fc1c1c0c8bff1eb6a1a1c499a48dfadeef702a0f`；交接 PWF commit：`d44421fae8944c5b8e87c3ab4f824606d88e742f`。
- 复读 HANDOFF、task_plan 中冻结接口/实施细则、20 文件 commit diff 及 5 个新合同模块。此 PWF 没有独立 INTERFACES.md，接口定义实际在 task_plan.md 的 Design/共享预算各节。
- 独立集中执行新增责任集：38 PASS / 1 Windows symlink 权限 skip，6.53s。无 pytest 插件自动加载，所以 asyncio_mode 未知配置警告保留；不影响本同步责任集结果。
- 源码十四文件审查前后 SHA 一致，清单和确切测试 argv 见 `independent_review_receipt.json`。

## W06-R1 [P1] cached-ready 只核真实字节，未核实际请求相关性

责任位置：`local_reconcile.py` 的 `_prepare_local_source` 首个 `query.status == found` 分支。此分支直接 `reader.verify_version(... budget=budget)` 后返回 ready，跳过 `_proven_facts` 的实际 DEI issuer/year/period/form 判断。正确哈希只能证明正文没变，不能证明早先的 acquisition 描述正确。

两个独立正常 API 控验均复现；没有 mock query、修改数据库、改哈希或篡改原件：

| 控验 | 原文事实 | 导入/缓存描述 | 实际输出 | 期望 |
| --- | --- | --- | --- | --- |
| cached_same_period_wrong_actual_cik | CIK99999，FY2026，10-K/FY | Acme/CIK12345 对应身份；FY2026；已知真实日期；form/FY 事实与正文相符 | query found；ready/existing_active_source；blocks_download=false | issuer 冲突具名失败，不能 ready |
| cached_declared_FY2026_actual_FY2022 | CIK12345，FY2022，10-K/FY | acquisition fiscal_year2026；已知日期；form/FY 事实与正文相符 | query found；ready/existing_active_source；blocks_download=false | 实读证明不是请求 FY2026，不能返回 ready；可排除或报告真实事实冲突 |

两原件均 438 bytes；CIK 样本 SHA `27572046bae50fbeda71446d38af50d44832e5a4ad02f149858788e7bb692fdd`；期次样本 SHA `6301c771c1aa49c0a3d528cf587229d4fba77ceae6369cfa33a59ad156cd6498`。调用返回 download_events=0、空 diagnostics，原字节保留。精确 setup 和结果在 receipt 的 independent_control_setup / independent_controls。

### 可直接改成 RED 的最小 setup

```python
cat = lake(tmp_path)  # US Acme/ACME，身份库 CIK12345
ref, path = imported(cat, html(cik='99999'),
                     published='2026-07-30', declared_year=2026)
facts = {'form_type': '10-K', 'fiscal_period': 'FY'}
cat.record_source_facts(ref=ref, facts=facts, evidence=evidence(ref, facts))
assert SourceVersionReader(cat).query_local(request()).status == 'found'
result = prepare_local_source(cat, request())  # request FY2026/10-K exact
assert result['status'] in {'blocked', 'unavailable'}
assert result['blocks_download'] and result['reason'] != 'no_matching_local_period'
```

同根相邻 RED 用 `html(year=2022, end='2022-06-30')`，导入 declared_year2026，其余相同；不得把 FY2022 当请求 FY2026 来源。

### 为什么现有绿集遗漏

`test_genuine_target_gap_never_becomes_byte_absence` 的 wrong_cik 样本用 imported 默认 declared_year/published_date=None，query 缺元数据，必然走慢路径；`test_known_wrong_cache_year_is_not_an_exclusion_proof` 是实际 FY2026 配缓存 FY2025，仍走慢路径。两者没有覆盖“缓存已命中但原文冲突”的首个 ready 分支。缓存预算测试验证该分支传递预算，却不验证原文语义。

### 责任修复建议

从来源事实的统一 relevant/ready 决策修复两条路径，先以真实源字节与当前请求关系证明可用。既有已实读、hash-bound 的事实可复用；初次没有这种证明时在所属来源层建立，不能仅凭 acquisition 标签跳过。保持同一字节/截止时间预算，避免通过额外 verify + reopen 重复完整读取；不新增人工签收、身份许可、第二账本或消费者目录判断。测试覆盖 cached issuer、cached period、正常 cached-ready 与同一预算；不要只补一个 CIK 特例。

## 已独立通过的真实复验与相邻控制

- 用作者 replay 的相同业务逻辑独立运行；仅在内存重定向新 receipt 输出，不修改 replay 文件、旧日志或旧 receipt。SQLite 只从 mode=ro 备份到独占 TEMP，raw 不复制，根只读；socket connect/DNS 审计 hook 禁止外网。
- 真 MSFT：7 个物理原件读，52,643,200 bytes，32 groups / 40 entries；操作 8.32s。FY2026 not_found/no_matching_local_period、blocks_download=false；2021/2022 实际旧日期 transform 解析正常；3 个季度实际 title 10-Q 修复幂等，capture JSON 不改。
- protected 原件/metadata/DB/config SHA,size,mtime 均 unchanged=true；TEMP absent，下载/模型/HTTP 请求 0。记录在 `independent_actual_replay_receipt.json`，不是公司级 M3。
- 另 3 个独立控验通过：已登记错期原文的坏 date/cache 不阻断当前缺口；真正同期间坏 cache 仍 blocked/local_metadata_gap，诊断 local_metadata_unreadable；健康 Dayu primary 与 hash 读取失败 attachment 同组仍 ready，坏附件未挡主件。
- direct/raw 同内容统一 SourceRef、wiki/另一公司范围、共享 metadata/hash/ready budget、有限 groups/entries、unknown title、null title/form/schema稳定由新责任集验证。操作没有重置预算或将上述预算控制伪装成 not_found。

## 验收边界与清理

此次 5 个独立相邻控验中 3 PASS、2 RED，不能将总体写成通过。真实 MSFT 缺期绿不覆盖已缓存矛盾原文的两条 RED。实施者补 RED 并修统一责任后再做一次集中复审。

生产原件、目录、配置、数据库、密钥及外部项目均未改；所有新 TEMP 基线恢复/不存在；无网络/付费调用。本报告保留 root 既有诊断与所有旧执行证据，不增加小节点审查或许可。
