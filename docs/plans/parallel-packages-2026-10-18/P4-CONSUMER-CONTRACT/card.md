# P4-CONSUMER-CONTRACT：FF/RF 只读契约验证

状态：READY，2026-10-18。范围是**集成测试 + 收据**：用已发布的 CWP 读/导出接口，核对消费端看到的 SourceRef、期间、单位与"未知可用性"是否与上游一致。0 下载、0 模型、跨仓只读。
PLAN_ID=parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT。

## 1. 真实问题

- CWP 已有 `company-wiki-source-read`（字节 + 收据 `2.1`/`2.2`）、`company-wiki-source-export-v2`（`2.0.0` bundle）、`company-wiki-source-query`。三者的字段语义由 `source_contract` 固定。
- 但消费端（filing-fetch、revenue-forecast）是独立仓库：它们各自读 manifest、各自拼期间、各自决定"日期未知时怎么办"。目前没有一份**在当前仓库内可复跑**的对照，能证明消费端没有丢 `source_availability_unknown`、没有把 `security_id` 宽度改掉、没有把"百万元"当"元"。
- 现有 `tests/integration/test_current_consumer_asof_contract.py` 与 `test_shared_scoped_rf_consumer.py` 已用 env 开关做类似事（`CWP_RF_PROJECT_ROOT`、`CWP_RF_E2E_REPO`），但覆盖的是发布口径/叙述链，不是本卡这组 identity/period/unit/availability 字段。

## 2. 目标

1. 新增 `tests/integration/test_p4_contract/`：默认 `skip`，显式 env 才运行；无 env 时输出明确的 `skip reason`，不静默通过。
2. 五类检查：**ref 往返**、**identity/period 一致**、**单位记号未被改写**、**未知可用性未被填成日期**、**零网络/零模型**。
3. 产出 `p4-contract-receipt/1` JSON（字段见 5.4），落在本卡目录，作为 ROOT 的验收输入。
4. 跨仓只读：只在 env 指定的 FF/RF 仓库里**运行**其已发布只读入口（若 ROOT 提供命令清单），并在运行前后核对 `git status --porcelain` 与 `HEAD` 不变。

## 3. 非目标（明确不做）

- 不采集、不下载、不重试任何原始文件；不调用供应商，不构造模型客户端。
- 不修改 FF/RF 仓库任何文件（含配置文件、`assurance/`、`output/`、`compatibility/`）。
- 不评估摘要质量、不判断预测正确性、不产出投资结论（那是 StockWiki/RF 的职责）。
- 不修 CWP 运行时；发现不一致只报告。
- 不新增 `conftest.py` 到 `tests/integration` 根目录，不给既有测试加依赖。

## 4. 独占写集

- `tests/integration/test_p4_contract/**`（新建：`conftest.py`、`test_p4_ref_roundtrip.py`、`test_p4_identity_period.py`、`test_p4_unit_grounding.py`、`test_p4_unknown_availability.py`、`test_p4_consumer_readonly.py`、`support/**`）
- `docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/**`（含 `fixtures/**`、`receipt.json`）

**禁写**：`src/**`（整目录）；`tools/**`；`tests/unit/**`；`tests/integration` 下其他任何文件（含 `__init__.py`、`conftest.py`）；`tests/support/**`；`pyproject.toml`；`.githooks/**`；`.github/**`；ROOT 独占清单（`narrative_reading.py`、`narrative_operating_relations.py`、`narrative_antecedent.py`、`operating_states/relations.py`、`operating_states/product_reference.py`、`tests/unit/du11_source_closure/**`、`docs/plans/du11-*/**`、`docs/plans/document-understanding-2026-10-13/**`）与其余三卡写集。

## 5. 冻结接口

### 5.1 环境开关（唯一开关方式）

| env | 含义 | 缺省行为 |
|---|---|---|
| `CWP_P4_CATALOG_CONFIG` | 只读 catalog 配置路径（**必须**指向测试专用 catalog） | 全部用例 `skip`，reason `"P4 requires CWP_P4_CATALOG_CONFIG"` |
| `CWP_P4_FF_ROOT` | filing-fetch 本地 checkout（只读） | FF 相关用例 `skip` |
| `CWP_P4_RF_ROOT` | revenue-forecast 本地 checkout（只读） | RF 相关用例 `skip` |
| `CWP_P4_CONSUMER_COMMANDS` | `p4-consumer-commands/1` JSON 路径 | 不执行任何消费端命令，`not_evaluated` |
| `CWP_P4_REQUIRE` | `"1"` 时把 skip 变成 fail | 默认不开启 |

`CWP_P4_CATALOG_CONFIG` **不得**指向生产 `config/source_catalog.yaml`：`conftest` 必须解析绝对路径并断言它位于 `tmp_path` 或 `docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/fixtures/` 之下，否则直接 `fail`（这是唯一允许的硬失败）。

### 5.2 消费端命令清单（`p4-consumer-commands/1`，由 ROOT 提供，本卡只读）

```json
{"schema_version":"p4-consumer-commands/1",
 "ff":{"argv":["python","-m","...","--config","{catalog}"],"cwd":"<repo root>","timeout_s":120},
 "rf":{"argv":["..."],"cwd":"<repo root>","timeout_s":120}}
```

- `argv` 中 `{catalog}`、`{document_id}`、`{source_id}`、`{content_sha256}` 由测试替换；其余原样。
- 命令必须是**只读**入口；测试不猜测命令、不探测子命令、不跑 `--help` 之外的探索性调用。
- 清单缺失 → 消费端用例 `not_evaluated`（记入收据），不失败。

### 5.3 消费端观测（`p4-consumer-observation/1`）

消费端命令的标准输出由测试解析为：

```json
{"schema_version":"p4-consumer-observation/1",
 "consumer":"ff|rf",
 "source_ref":{"document_id":"...","source_id":"...","content_sha256":"...",
               "byte_size":0,"mime_type":"...","schema_version":"2.0"},
 "facts":{"document_kind":null,"canonical_entity_id":null,"market":null,"security_id":null,
          "fiscal_year":null,"fiscal_period":null,"period_end":null,"published_date":null,
          "form_type":null,"language":null},
 "availability":{"status":"source_availability_unknown|observed","evidence":null},
 "quotes":[{"text":"...","unit_tokens":[{"text":"百万元"}]}],
 "downloads":{"count":0},"model_calls":{"count":0}}
```

若消费端输出的形状不是这个，测试**不得**顺手猜字段：记 `not_evaluated` + `reason="unmapped_consumer_output"`，并把原始 stdout 的 `sha256` 与截断前 2 KiB 存入收据（不落全文）。

### 5.4 收据（`p4-contract-receipt/1`）

```json
{"schema_version":"p4-contract-receipt/1","status":"ok|partial|fail|blocked",
 "generated_at":"...","inputs":{"catalog_sha256":"...","commands_sha256":null},
 "counts":{"checked":0,"passed":0,"failed":0,"skipped":0,"not_evaluated":0},
 "cases":[{"name":"p4_ref_roundtrip","status":"pass|fail|skip|not_evaluated","reason":null,
           "checks":[{"name":"manifest_vs_receipt","status":"pass","detail":{}}]}],
 "limitations":["..."]}
```

收据由测试在 `pytest_sessionfinish` 之后由本卡 `support/receipt.py` 汇总写出；路径固定为
`docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/receipt.json`。

### 5.5 五类判定（必须按此实现）

1. **ref 往返**：对每个 `SourceRef`，`company-wiki-source-export-v2` 的 manifest 与 `company-wiki-source-read` 收据的 `document_id/source_id/content_sha256/byte_size/mime_type` 全等；`sha256(bytes)` 等于 `content_sha256`；bundle 的 `bundle_sha256` 复算一致。不等 → `p4_consumer_field_missing` 或 `p3_*` 同义码（本卡用 `p4_*`）。
2. **identity/period**：消费端 `facts` 与 CWP manifest 逐字段比对；任一侧 `null` 且另一侧非 `null` → `fail`（未知不可被填）。`published_date` 为 `null` 时消费端必须是 `null`。
3. **单位**：消费端 `quotes[].unit_tokens` 必须是该 quote 文本的子串集合；若 CWP span 有单位记号而消费端 quote 对应位置没有 → `fail` + `p4_consumer_unit_rescaled`；若 quote 有换算后的数字（如 `1.2亿元` 对应原文 `120,000,000元`）→ 判 `fail`（本卡禁止自动换算）。
4. **未知可用性**：CWP `availability_evidence` 为 `null` → 消费端 `availability.status` 必须 `"source_availability_unknown"` 且 `evidence=null`；出现任何日期 → `p4_unknown_availability_lost`。
5. **零网络/零模型**：整个 session 内 `socket.socket.connect` 被 monkeypatch 为抛 `AssertionError`；任何捕获 → `p4_network_attempted`。模型：断言测试进程未 import `company_wiki.llm_client`，且消费端输出 `model_calls.count==0`；否则 `p4_model_attempted`。

## 6. TDD 要求

**A：真实 RED（≥12 用例；先让断言在缺失实现/缺失收据时失败，再补 support）**

- `CWP_P4_CATALOG_CONFIG` 指向生产配置 → 硬失败（这是唯一允许的非 skip 硬失败）。
- env 全缺 → 所有用例 `skip`，且 `skip reason` 可读；`CWP_P4_REQUIRE=1` 时变 `fail`。
- bundle 与 receipt 的 `byte_size` 差 1 → `fail`。
- 同长度篡改字节 → `fail`。
- `security_id` 宽度不一致 → `fail`。
- `published_date` 被消费端填了日期而 CWP 为 `null` → `fail`。
- quote 丢单位记号 → `fail`；quote 做换算 → `fail`。
- availability `null` 而消费端写 `observed` → `fail`。
- 触发一次 `socket.connect` → `p4_network_attempted` 且用例失败。
- 消费端命令清单缺失 → `not_evaluated` 且 `status="partial"`（不是 `pass`）。
- 收据 schema 字段与 5.4 完全一致（多/少字段都算失败）。
- 跨仓只读：`git status --porcelain` 与 `HEAD` 运行前后相同（env 提供仓库时）。

**B：实现 support 与收据**；**C：在真实测试 catalog 上跑一遍，保存日志与收据**。

夹具：`fixtures/` 内的最小 catalog（1–2 个合成 source，`text/plain` 与一个 `application/pdf` 无 span 的 source），配置与 request 均带 `sha256`。

禁止：删用例、`skip` 无 reason、把 `not_evaluated` 写成 `pass`、改断言阈值、跳过 `git` 只读核对。

## 7. 验收命令与完成定义

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m pytest tests/integration/test_p4_contract -q -p no:cacheprovider          # 无 env：全 skip
$env:CWP_P4_CATALOG_CONFIG = "<fixture>/catalog.yaml"
python -m pytest tests/integration/test_p4_contract -q -p no:cacheprovider          # 有 env：核心用例真跑
python -m ruff check tests/integration/test_p4_contract
```

**完成定义**

1. 无 env 时全部 `skip` 且 reason 明确；有 env 时核心用例真跑并通过或如实 `not_evaluated`。
2. `receipt.json` 生成，字段与 `p4-contract-receipt/1` 完全一致，`counts` 与 pytest 汇总一致。
3. `tests/integration` 下除本卡目录外 0 改动。
4. `git status --porcelain` 在本仓与被测消费端仓库均无新增改动。
5. 独立审查 PASS 且绑定最终 SHA。
6. 写明"未跑真实生产 catalog；消费端是否真实只读取决于 ROOT 提供的命令清单"。

## 8. 资源与安全边界

- 0 下载、0 上传、0 模型；`socket` monkeypatch 全程生效。
- 不读密钥；不把任何 `env` 值写进收据（只写 `sha256` 与布尔）。
- 不写生产 config/DB/`output/`/gold；不 `pip install`；不改 `sys.path` 之外的导入路径。
- 跨仓只读：只执行清单里 `argv`，不写对方目录；运行前后核对 `HEAD`/`git status`。
- 超时：单命令 ≤ 清单 `timeout_s`（≤300s）；pytest 单用例 ≤ 300s，超时记 `fail` 并保留 `$TEMP` 证据。
- 收据 ≤ 16 MiB；消费端输出只存 `sha256` 与前 2 KiB。

## 9. 交接格式

`handoff.md` ≤80 行四段式。`handoff.json` 在外壳上补充：

```json
{
  "lane": "P4-CONSUMER-CONTRACT",
  "interface_versions": {"observation": "p4-consumer-observation/1", "receipt": "p4-contract-receipt/1",
                          "commands": "p4-consumer-commands/1"},
  "known_limits": ["消费端映射取决于 ROOT 提供的命令清单", "未跑生产 catalog"],
  "root_integration_steps": [
    "提供 consumer-commands.json 与只读 catalog 后复跑一次",
    "把 receipt.cases 的 fail/not_evaluated 纳入发布前对照",
    "P4 不进入 pre-push；由 ROOT 在大节点显式运行"
  ]
}
```

## 10. 独立审查要求

- 审查者 ≠ 作者、≠ ROOT。
- 重点：skip 是否被当成通过；收据 `counts` 是否与真实运行一致；是否真的 0 网络 0 模型（要求审查者手工开一次 `socket` 验证会失败）；是否写入被测仓库；生产配置守卫是否可被绕过。
- 修完对最终 SHA 复审；报告写 `review/independent.md`。
