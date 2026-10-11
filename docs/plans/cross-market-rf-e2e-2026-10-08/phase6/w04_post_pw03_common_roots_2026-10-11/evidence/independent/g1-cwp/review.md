# W04 G1 CWP 独立审查

状态：**PASS_WITH_SCOPE_LIMITS_STOP**。未发现 material finding。范围为 WP01 CWP producer /3 与 ROOT 生成身份；未签 RF WP03 或真实经济质量。

独立执行 91 个断言（含源码/已有证据 SHA），全部通过。未重跑 110/98 套件或 9 次收费调用。

## 实际检查

- 公共 CLI reference/read/evidence 分页成功；ref 6 键、subject_ref 4 键，无 single raw SourceRef 锚。
- read 精确返回既有 59,247B bundle，SHA 970ce8774bbf7ab660a5562c7c299057b54648b2b412872c0480ad8aa4ff19ff。65 父 refs 和原 pointers 由字节等同确认；read/evidence 各打开每父一次。
- parent_count=65、locator_count=6；完整 subject lineage SHA 为 18290ca89092b7366bdee6d3d4ecdb6d2b99fd03a2ac14a04abeb759fd6a025d，与 projection/raw SHA 不同。
- reference stdin/stdout/receipt 为 424/579/667B，read stdin/receipt 为 725/931B，evidence receipt 为 981B。LF 纳入 16,384B cap；16,385B 请求被拒绝；bundle cap 保持 1,310,720B。
- issuer/as-of/generation/artifact 错配及第 65 父原件损坏均被拒绝、stdout 为空；自有损坏副本已恢复并删除。
- 两个真实 US 来源（PPTX IR、HTML research）保留 null fiscal_year/period/period_end；2027 FY 查询不借用发布时间。
- projected official_json unknown language 可解析；optional declared_language 保留，错误 metadata 类型被拒绝。
- 四 optional generation 字段 null/omitted 的实际 HTTP body 相同。真实 thinking/effort/temperature/reasoning_split/cap/output field/model/endpoint 改动失效；同 effective purpose label 可复用；旧 omitted 基线 manifest SHA 保持。

## 位置与根因

| 源码位置 | 已核对根因/结果 |
|---|---|
| src/company_wiki/automation/narrative_transport_contracts.py:202 | Full projected subject/65-parent embedding in /2 exceeds compact request budget. Explicit /3 carries neutral compact identity; full lineage stays in pinned body. |
| src/company_wiki/source_catalog/source_reader.py:585 | capture_ready previously required period_known for every kind. Nonperiodic kinds now retain genuine missing periods and qualify through capture metadata. |
| src/company_wiki/automation/narrative_generation.py:28 | Raw manifest copied thinking/temperature/reasoning_split null while HTTP omitted them. Shared optional seam follows emitted options and preserves historical omitted identity. |

其余行为具体源码定位在 review.json verified_current_behaviors；material_findings 为空。

## 来源及实际检查 SHA

- handoff：e5c71592eec4bcbee9cc26a08cc89e0483536a13133f9161ab3f09e650acaa66
- overlay：82b8596ddde2dc8a733c9a339284402407fb407bc971d2cb34aa04087732c509
- checks.json：02c20d19b9ecf7f237d405e165d12fba062b0b31df0a60e35ba855d09fa4b6d2
- checks.log：e466cfb4a08499766d09d12662aa91f1f331c5ffa43a1e09e667837f9ebe5c7e
- probe.py：b995d39d4a50327359b985364e784427b76c4e22c534e73ca128d8285eb14e77

审查前后相同的源码/测试 SHA：

| 文件 | SHA-256 |
|---|---|
| src/company_wiki/automation/narrative_contracts.py | 6a3b4a262dac4079d7ec6a21c1e09e7ec238d55db3253483f11a69365e76faf3 |
| src/company_wiki/automation/narrative_evidence_view.py | 840c6e22fc75297b0c28a8b82301add67d1796c0402d3511e45ee5f08162153d |
| src/company_wiki/automation/narrative_generation.py | b8621f835b0480fd79ab2f0a7ef33a2e3427e5b3d494f126612538be5411b1a8 |
| src/company_wiki/automation/narrative_http_model.py | 112bfe3e494c3eeb46f76f883ec31794f38de71af46924b9665f952c6c345028 |
| src/company_wiki/automation/narrative_official_json.py | 3dd559f183e065fbce68daa870b83c0249e34eaadff99a661a962e329693d7b3 |
| src/company_wiki/automation/narrative_transport.py | 3ed321a97bbf7bfef60dbb5719554924fbd84d3a3e917cd399c7e98e84451fc2 |
| src/company_wiki/automation/narrative_transport_contracts.py | 6fca7f092e3f4441e9a92b2f6ddcefbb08fc0553fd70bf36409ea1b51ae456b5 |
| src/company_wiki/narrative_subject.py | d87194b4f7a0b4d9eaccca7135133308fbd051dc7ef8c1a98d63d3b5473f60c0 |
| src/company_wiki/source_catalog/document_kinds.py | 699c09ab3846eb30905c1b7f3933271e8499d660274fef002eecc67c13764cdd |
| src/company_wiki/source_catalog/narrative_transport_cli.py | 8a2cbc088581496a8b48094cb53767f12b7a58448831f715c9cfb6397d41138e |
| src/company_wiki/source_catalog/official_json_projection.py | 3a0f7844f86eb07876812e5b8015c5179022762a3c25adc59b565a4f4f010adf |
| src/company_wiki/source_catalog/source_reader.py | be753a61cafd1b5d876f59c7e3f63f5f3724dc537d18e9cac58ff35795fab472 |
| tests/unit/test_w04_generation_identity.py | d81e14b9a6895d5f395a107bb8b72479de1eec3bd539942a1c1e06004e4d159b |
| tests/unit/test_w04_source_transport.py | bc4cccc1d327e89bcfdefd8b91ec0b0e51591c44148f186970a79d72e4f02fb6 |

## 兼容与未执行

旧 /1、/2 字符串、fields、默认 loader 及分支经只读 diff/source 复核。已有 110 GREEN 日志 SHA 6123410cd4b66390fc7304e53ed7d8ea488d34e1e5ffd72ec3944081a4df3718；ROOT 98 GREEN 日志 SHA 1a6348d47dadf17fc42a98bc83d2c938039d5abf34b235ea5d98775e107e99aa 均已独立核对，未重跑。

- Ordinary git status/diff in isolated checkout returned worktree/permission errors; review uses frozen diff, base generation git show, source/evidence SHA. Unrelated WIP cleanliness not attested.
- CodeGraph not initialized as supplied by ROOT; no init performed; specified files read directly.
- Owner 110 and ROOT 98 logs independently SHA-verified, not reexecuted; 9 paid model calls not repeated.
- ROOT RED JSON records 3 failed/7 passed with full_stdout_saved=false; no claim of a complete preserved RED stdout transcript.
- RF consumer integration, real paid-summary quality, new-company research and cross-repository final G1 remain outside this CWP review.

零网络/provider/HTTP/model，费用 0。只写本 g1-cwp 报告目录及自有短 TEMP；TEMP 已删除。67 原件+2 fixture 配置 SHA 不变，源码 SHA 前后不变。未改源码、生产配置、旧 run/ledger/artifact、canonical、Dayu 或其他 repo。

未执行：全套回归、收费摘要与质量、RF consumer integration、跨仓 final G1、G2/G4/G5、commit/push/install。

**STOP：报告封存后停止写入，等待 ROOT 汇总。**
