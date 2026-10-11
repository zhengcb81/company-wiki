# W06-CWP-PORTABILITY 交接（虚拟存储根迁移回归工具）

**status: COMPLETE** — 工具正确、报告准确、范围完成。未发现迁移缺陷；未改任何 src/scripts/config/现有tests/CI。
产品侧无需修复即全绿；ROOT 有 3 条低成本改进建议（见下）。

## 交付物

| 路径 | 内容 |
|------|------|
| `tools/source_root_portability/` | runner、fixture builder、oracle、consumer spy、报告、README |
| `tests/unit/test_w06_root_portability_oracle.py` | oracle 反例（虚假 PASS 形态逐类拒绝）+ 真实记录接受 |
| `tests/integration/test_w06_root_portability.py` | 真 SourceVersionReader+临时 catalog、跨进程 spy、sentinel 清理边界 |
| `docs/handoffs/w06-cwp-portability/logs/` | RED / GREEN / E2E 分立日志（不互相覆写） |
| `docs/handoffs/w06-cwp-portability/e2e/attempt-0003-report.json` | 最终 E2E 报告副本（schema cwp-root-portability/1，29KB） |
| `.planning/w06-cwp-portability/` | 本线 PWF 三文件 |

## 三个大节点证据

1. **RED**（logs/red-oracle.log）：oracle stub（全放行）下 22 反例/契约测试 19 failed —
   套件对漏 reopen、SHA 只核 metadata/假 receipt、消费者偷开 rawPath、移根造假日期/非周期假 FY、
   物理 dup 冒充逻辑来源、无 policy 观察、清理越界/丢 sentinel、改写 fixed expected、
   UNKNOWN 混入 same-ID 通过全部有拒绝断言；ImportError/未初始化不算 RED。
2. **GREEN**（logs/green-unit-integration-final.log）：33 passed。
   集成含真 `SourceVersionReader.open_version(ref, purpose="source_export")` 字节验真（不 mock）、
   跨进程 consumer spy（审计钩子记录直接文件访问，raw 直开归属非 reader 即违规）。
3. **E2E**（logs/e2e-runner-final.log + e2e/attempt-0003-report.json）：
   `python -B tools/source_root_portability/run.py --owned-root <fresh> --out-root <new-attempt>`；
   7 场景全 PASS、oracle overall PASS、exit 0、elapsed 7.4s ≤120s；
   source_read_calls 51（in-process 47 + 子进程 4）、HTTP 0、model 0、paid 0；
   owned root 清理恢复 absent 基线，sentinel 机制另有集成测试。
   attempt-0001（oracle 抓到 S4 记录缺字段→FAIL）/0002 保留不覆写。

## 关键实测（详见 .planning/w06-cwp-portability/findings.md F14-F18）

- **身份**：source_id/document_id 由内容 SHA 派生。移根/改 relative_path/跨根重登记 →
  `same_content_same_ids`（观察，非承诺）；旧 SourceRef 经当前根读同 bytes（S2/S3 PASS）。
- **policy**：移根使 policy_sha256 实测改变（path_refs），已记录 before/after，不作授权门。
- **去重**：同 bytes 双根 = 1 逻辑来源 / 2 物理副本（candidate_rank 按 root priority）；
  删 canonical 副本后 fallback 副本真实验真可读。
- **完整性**：同长度篡改→`content_sha256_mismatch` 真拒；同路径新内容重登记=新版本
  （旧 ref 拒 `no_indexed_location`，新 ref 读新 bytes）；恢复旧字节+重登记复原。
- **非周期**：sidecar 完整性契约（WU-701 N-02）要求 period 字段；fixture 用显式
  `nonperiodic` 标记，describe 层 fiscal_year=None（不获假 FY），移根后 facts 稳定。
- **无路径面**：SourceRef/export bundle 无路径字段；消费者只收 SourceRef/export；
  spy 证实 raw 只有正式 reader 打开；新进程 reopen（新 PID、fresh_read）。

## ROOT fix 建议（非阻塞）

1. sidecar schema 为非周期原件引入显式非周期约定（当前必须填任意真值 period 标记才能
   capture-ready，语义靠 describe 层过滤 4 位年份兜底）。
2. 文档化同路径重登记的 location 重绑语义（旧 ref → `no_indexed_location` 而非 SHA 类拒因），
   供消费者契约引用。
3. 无 routes 的 directory 根会把 `.source.json` 注册成独立文档（legacy quirk）；考虑与
   配对分支行为对齐（本工具 fixture 以 `routes: include ["*"]` 规避）。

## 复跑方式

```powershell
$env:PYTHONPATH="<worktree>\src"
python -B -m pytest -q tests/unit/test_w06_root_portability_oracle.py tests/integration/test_w06_root_portability.py
python -B tools/source_root_portability/run.py --owned-root C:\tmp\w06rp\owned --out-root C:\tmp\w06rp\out
```

默认 CI 只取快速 oracle 单元；跨仓/多根完整回放保留手动大节点入口（本卡 C）。
W05（OCR）不在本包；PNG/PPTX OCR 未测、未等待。
