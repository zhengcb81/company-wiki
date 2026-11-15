# 验收证据索引 — OWNERPKG-CWP-CANDIDATES-01 / CWP-1

- 日期: 2026-11-15
- 分支: `codex/cwp1-identity-suffix-20261115`（worktree `company-wiki-cwp1-identity-20261115`）
- 基线对照: 未修复 master 源码树 `C:/Users/郑曾波/Projects/company-wiki/src`
- 全部探针零下载、零模型、零网络；每条 FF/RF 输出 `downloads=0` 如实记录。
- **夹具说明**: FF/RF 联动探针用 tmp 配置
  `C:/Users/郑曾波/AppData/Local/Temp/cwp1-probe/company_wiki_probe.json`
  把 CWP CLI 指向**修复后 lane 的 `src`**；catalog 数据用只读绝对路径配置
  `catalog_probe.yaml` 指向主仓 `.source_catalog`。**未改动任何生产配置**
  （`config/source_catalog.yaml`、`config/company_wiki.json` 保持原样），
  未写入、未登记、未删除任何原件或候选数据。复跑脚本不进 git。

## §5.1 三查询解析探针（真实 CLI，修复后）

命令模板:
```
PYTHONUTF8=1 PYTHONPATH=<lane>/src C:/Miniconda/python.exe -B \
  -m company_wiki.source_catalog.cli --config <lane>/config/source_catalog.yaml \
  identify --query "<Q>" [--market US|HK]
```

| 查询 | status | reason | resolved | 候选 | 证据 |
|---|---|---|---|---|---|
| `Alibaba Group Holding Limited` | `resolved` | `one_verified_exact_identity` | US BABA (`official_name_exact`) | 1 | `identify-Alibaba_Group_Holding_Limited.*` |
| `BABA` | `ambiguous` | `cross_market_dual_listing_requires_market_selection` | — | 2 (HK 09988 alias_exact + US BABA ticker_exact) | `identify-BABA.*` |
| `09988` | `resolved` | `one_verified_exact_identity` | HK 09988 (`ticker_exact`) | 1 | `identify-09988.*` |

具名消歧语义（`identify-*_market_*.command.txt` / `.stdout.json`）:

| 查询 + 显式市场 | status | resolved |
|---|---|---|
| `BABA --market US` | `resolved` | US BABA |
| `BABA --market HK` | `resolved` | HK 09988 |
| `Alibaba Group Holding Limited --market US` | `resolved` | US BABA |
| `09988 --market HK` | `resolved` | HK 09988 |

结论: 三查询均为具名、稳定、可复核响应：`single_match` 或**带消歧语义的具名
双上市响应**（候选各带 market/exchange/ticker/security_id，请求可显式选定），
不再是 `fuzzy_candidates_require_user_selection`。`BABA` 无 market 保持
`ambiguous` 是**有意保留的 fail-closed 语义**：不静默选边、不删候选，
但 reason 从无名 `multiple_verified_exact_identities` 变为具名可操作原因。

## §5.2 FF reuse_only 联动（阿里 20-F FY2025）

命令模板（见 `ff-*.command.txt`）:
```
C:/Miniconda/python.exe -B scripts/fetch_filing.py \
  --config <tmp>/company_wiki_probe.json \
  --request-file <tmp>/<tag>.json --timeout-seconds 120
```

| 探针 | exit | status | 说明 |
|---|---|---|---|
| `ff-alibaba-20f-reuse` (market=US) | 0 | `source_candidate` | `resolution_outcome=reused_existing`，命中 20-F 原件 sha256 `36daec0c…`，`download_events=0` |
| `ff-alibaba-20f-reuse-nomarket` | 0 | `source_candidate` | 同上，不依赖 market 参数 |
| `ff-baba-reuse-us` | 0 | `source_candidate` | 显式市场消歧后确定 resolve |
| `ff-baba-reuse-nomarket` | 2 | `identity_error` | **失败样本保留**：具名 `cross_market_dual_listing_requires_market_selection`，非 fuzzy |

基线对照（`baseline-master/master-ff-20f-reuse.stdout`）：未修复 master 对同一 20-F
请求返回 `exit=2 / identity_error / "ambiguous / fuzzy_candidates_require_user_selection"`，
完整复现施工包 §1 的 E12 FF 失败。**修复后该 identity_error 消失**。

## §5.3 RF source_preparation 六路线联动

- 入口: `revenue-forecast/scripts/source_preparation.py` → filing-fetch → CWP。
- 请求体: 直接复用 RF INPUT-PREP 的 `.planning/rf-input-prep-01/requests/route*.json`，未改动。
- 修复后证据 `rf-routes/`；未修复 master 归因对照 `rf-routes-master/`。
- 汇总: `rf-routes/alibaba-routes-after-fix.json`、`rf-routes-master/alibaba-routes-master.json`。

| 路线 | 修复后 | master 对照 | downloads |
|---|---|---|---|
| route1 HK FY2026 reuse | exit 3 `source_blocked` / `invalid_local_prepare_request` | 同 | 0 |
| route2 HK FY2026 fetch-if-missing | exit 3 `fatal` / `acquisition_validation_failed` | 同 | 0 |
| **route3 HK FY2025 reuse** | **exit 0 `found_capture_ready`** | **exit 0 `found_capture_ready`** | 0 |
| route4 US FY2026 fetch-if-missing | exit 3 `fatal` / `acquisition_validation_failed` | 同 | 0 |
| route5 HK latest_as_of reuse | exit 3 `fatal` / `acquisition_validation_failed` | 同 | 0 |
| route6 HK latest_as_of fetch-if-missing | exit 3 `fatal` / `acquisition_validation_failed` | 同 | 0 |

route3 产出完整来源记录: `source_id=urn:company-wiki:source:sha256:8ab12348…`、
`title=2025財務年度報告`、`published_date=2025-06-26`、
`capture_method=local_document`、`snapshot_sha256=8ab12348…`、verified_read host receipt。

**诚实归因（关键）**: route3 在未修复 master 下**同样成功**
（`baseline-master/master-rf-route3.stdout`、`rf-routes-master/route3-*`）。
因此 route3 的 `found+capture_ready` **不是本包身份修复的功劳**；该路线用
`company_query="阿里巴巴－Ｗ"`（HK 精确别名）与元数据完整的 FY2025 原件，
本来就未撞上身份歧义。六路线在两种源码树下逐条结果一致，证明：
(a) 本包没有引入任何 RF 回归；
(b) 剩余五条失败是**既有的下游契约/元数据缺口**，与身份库无关，也不是 fuzzy/ambiguous 复发。

### 剩余缺口的具名根因（§5.3 允许"具名新原因说明剩余缺口"）

- **route1**: 直接调用 CWP `prepare_local_source` 复现真实异常
  `SourceResolutionError('identity scope fields require source query request schema 1.1')`
  （`resolver.py:591`）。FF 的 `ff_local_source_prepare.py` 在 `source_request` 中同时传
  `identity_scope="listing"` / `issuer_link_id`，却把 `schema_version` 固定为 `"1.0"`；
  CWP CLI 归类为 `invalid_local_prepare_request`，FF 再映射成闭集外的 `unknown`。
  属 **FF↔CWP local_prepare 契约层缺口**，不在本包身份匹配范围（见 §8-3 交接）。
- **route2/4/5/6**: `company-wiki ensure exited 1`，
  `upstream_cause.code=acquisition_validation_failed`，`provider_started=false`、`downloads=0`。
  同属 ensure/采集校验层，非身份层。
- 六条路线均 `downloads=0`、未启动 provider，符合红线"浏览态 0 模型 / 0 下载"。

## §5.4 证据完整性与失败样本

- 每条探针落盘 `command`（`.command.txt` / `.command.json`）、`stdout`、`stderr`、`exit`。
- 失败样本全部保留未改写：4 个 `exit=2/3` 的 FF/RF stderr 与 `rf-six-routes-run.log`。
- 基线对照单独存于 `baseline-master/`、`rf-routes-master/`，可与修复后逐条比对。
- 证据目录 < 300KB，全量落盘，未做裁剪。

## 复现

tmp 夹具与复跑脚本位于 `C:/Users/郑曾波/AppData/Local/Temp/cwp1-probe/`
（`run_rf_routes.py`、`run_rf_master_routes.py`、`run_baseline_compare.py`），
仅用于本次验收，不进 git。生产配置零改动。
